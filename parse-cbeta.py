#!/usr/bin/env python3

import re
import sys
import json
import argparse
import logging
from pathlib import Path
from lxml import etree
from bisect import bisect_left

from dataclasses import asdict

from cbeta_seg import Mulu, Byline, RelativeToByline
from cbeta_seg import JuanNumber, JuanRange, JuanHead, Juan
from cbeta_seg import Segment
from cbeta_seg import remove_underscore_keys_in_obj
from tick_spinner import TickSpinner
from superscript import fromStringASCII as to_sup

def parse_args():
  parser = argparse.ArgumentParser(
    description="Extract mappings between lb@n and juan[fun=open]@n from CBETA XML files."
  )
  parser.add_argument("files", nargs="*",
    help="Target XML file(s)"
  )
  parser.add_argument("--dir", "-d", action="append",
    help="Target directory containing XML files (can be specified multiple times)"
  )
  parser.add_argument("--output", "-o",
    help="Output JSON file path (prints to stdout if omitted)"
  )
  parser.add_argument("--summary", action="store_true",
    help="Print summary"
  )
  parser.add_argument("--log", type=str,
    help="Log file (progress & spinner is not logged)"
  )
  parser.add_argument("--debug", action="store_true",
    help="Debug"
  )

  args = parser.parse_args()

  if not args.files and not args.dir:
    parser.error("Please specify target XML file(s) or directory with -d/--dir.")

  if args.debug:
    log_level = logging.DEBUG
  else:
    log_level = logging.CRITICAL

  if args.log:
    logging.basicConfig(level=log_level, filename=args.log, filemode="w")
  else:
    logging.basicConfig(level=log_level, stream=sys.stderr)

  args.logger = logging.getLogger(__name__)

  return args


def get_local_tag(tag: str) -> str:
  """Extract local tag name by removing XML namespace."""
  if "}" in tag:
    return tag.split("}")[-1]
  elif ":" in tag:
    return tag.split(":")[-1]
  else:
    return tag


def generate_key_from_filename(file_path: Path) -> str:
  """
  Generate a dictionary key from the filename.
  Example: T01n0002.xml -> T0002 (ignores 2nd, 3rd, and 4th characters).
  """
  stem = file_path.stem  # Filename without extension
  if len(stem) >= 5:
    # 1st character (index 0) + 5th character onwards (index 4~)
    return stem[0] + stem[4:]
  return stem


def get_attr_by_local(elem, nm):
  nsnm = "}" + nm
  for k, v in elem.attrib.items():
    if k.endswith(nsnm) or k == nm:
      return v
  return None


def collect_texts_from_node(nd, strip = False):
  if hasattr(nd, "tag"):
    texts = [ t for t in nd.itertext() ]
  else:
    texts = [ str(nd) ]
  return [ t.strip() if strip else t for t in texts ]


def get_localname(nd):
  return etree.QName(nd).localname


def written_tag(nd):
  if not hasattr(nd, "tag"):
    return "(none)"

  localname = get_localname(nd)
  if nd.prefix is None:
    return localname

  return f"{nd.prefix}:{localname}"


def try_key_value_attr(nd, attr_k):
  if (attr_v := nd.get(attr_k)) is None:
    return ""
  return f" {attr_k}=\"{attr_v}\""


def parse_xml_file(file_path: Path, args) -> dict:
  stem = file_path.stem
  tick_spinner = TickSpinner(tick_interval = 10)
  tick_spinner.set_label(f"{stem} parsing XML")
  tick_spinner.progress()
  xml_tree = etree.parse(file_path)
  xml_root = xml_tree.getroot()

  tick_spinner.set_label(f"{stem} collect element ordering")
  xml_order = {}
  xml_elems = []
  for i, elem in enumerate(xml_root.iter()):
    tick_spinner.progress()
    xml_order[elem] = i
    xml_elems.append(elem)

  tick_spinner.set_label(f"{stem} collect <milestone>")
  milestones = xml_root.xpath("//*[local-name()='milestone']")
  segments = []
  for m in milestones:
    tick_spinner.progress()
    segments.append(Segment(n=m.get("n"), unit=m.get("unit")))

  milestone_indexes = [ xml_order[m] for m in milestones ]

  tick_spinner.set_label(f"{stem} collect <lb>")
  for elem_lb in xml_root.xpath("//*[local-name()='lb']"):
    tick_spinner.progress()
    lb_index = xml_order[elem_lb]
    try:
      lb_n = elem_lb.get("n")
      i = bisect_left(milestone_indexes, lb_index)
      if i > 0:
        seg = segments[i-1]
        if seg.lb_n_first is None:
          seg.lb_n_first = lb_n
        seg.lb_n_last = lb_n

    except:
      print(f"No segment would include <lb n='{lb_n}'>", file=sys.stderr)

  tick_spinner.set_label(f"{stem} collect <byline>")
  bylines = [ bl for bl in xml_root.xpath("//*[local-name()='byline']") ]
  byline_indexes = [ xml_order[bl] for bl in bylines ]
  for i, bl in zip(byline_indexes, bylines):
    lb_n = next(
      xml_elems[j].get("n")
      for j in range(i - 1, -1, -1)
      if get_localname(xml_elems[j]) == "lb"
    )
    bl_dic = {
      "text":    "".join(collect_texts_from_node(bl, strip = True)),
      "cb_type": get_attr_by_local(bl, "type"),
      "lb_n":    lb_n,
    }
    j = bisect_left(milestone_indexes, i)
    if j > 0:
      seg = segments[j-1]
      seg.bylines.append(Byline.from_dict(bl_dic))
    else:
      print(f"No segment would include {bl_dic}", file=sys.stderr)


  tick_spinner.set_label(f"{stem} collect <cb:juan>")
  for elem_juan in xml_root.xpath("//*[local-name()='body']//*[local-name()='juan']"):
    tick_spinner.progress()
    # print("=", end="", file=sys.stderr, flush=True)
    j = xml_order[elem_juan]
    i = bisect_left(milestone_indexes, j)

    if i == 0:
      continue

    if len(byline_indexes) == 0:
      r2bl = RelativeToByline.NO_BYLINE
    elif j < byline_indexes[0]:
      r2bl = RelativeToByline.BEFORE
    else:
      r2bl = RelativeToByline.AFTER


    seg = segments[i-1]
    juan = Juan(
      fun = elem_juan.get("fun"),
      n = elem_juan.get("n"),
      relative_to_byline = r2bl,
    )
    seg.juans.append(juan)


    tick_spinner.set_label(f"{stem} jhead <cb:jhead>")
    for elem_jhead in elem_juan.xpath(".//*[local-name()='jhead']"):
      str_jhead = written_tag(elem_jhead)
      str_jhead += try_key_value_attr(elem_jhead, "n")
      str_jhead += try_key_value_attr(elem_jhead, "place")
      str_jhead += try_key_value_attr(elem_jhead, "type")
      str_jhead += try_key_value_attr(elem_jhead, "level")
      tick_spinner.progress()

      seen_title = False
      jh_prefixes = []
      jh_title = []
      jh_postfixes = []
      for nd in elem_jhead.xpath("./node()"):
        dest_strings = jh_postfixes if seen_title else jh_prefixes
        if not hasattr(nd, "tag"):
          dest_strings += collect_texts_from_node(nd, strip = True)
        else:
          localname = etree.QName(nd).localname
          if localname in ("title"):
            seen_title = True
            jh_title += collect_texts_from_node(nd, strip = True)
            continue

          str_elem = written_tag(nd)
          str_elem += try_key_value_attr(nd, "n")
          str_elem += try_key_value_attr(nd, "place")
          str_elem += try_key_value_attr(nd, "type")
          str_elem += try_key_value_attr(nd, "level")
          str_elem += try_key_value_attr(nd, "ref")
          str_text = "".join(collect_texts_from_node(nd, strip = True))

          if localname == "g":
            g_strings = "".join(collect_texts_from_node(nd, strip = True))
            g_ref = to_sup(
              re.sub(r"CB0+", "CB", nd.get("ref").split("#", 1).pop()).lower()
            )
            logging.debug(
              f"{file_path}: picked <{str_elem}> under <{str_jhead}>"
              f" has string \"{''.join(g_strings) + g_ref}\""
            )
            dest_strings += g_strings
            dest_strings += [ g_ref ]
            continue

          if len(str_text):
            logging.debug(
              f"{file_path}: ignored <{str_elem}> under <{str_jhead}>"
              f" has string \"{''.join(collect_texts_from_node(nd, strip = True))}\""
            )
          else:
            logging.debug(
              f"{file_path}: ignored <{str_elem}> under <{str_jhead}>"
            )

      jhead = JuanHead(
        head  = "".join(jh_prefixes),
        title = "".join(jh_title),
        tail  = "".join(jh_postfixes)
      )
      juan.heads.append(jhead)


    tick_spinner.set_label(f"{stem} jhead <mulu>")
    for elem_mulu in elem_juan.xpath(".//*[local-name()='mulu']"):
      # print("-", end="", file=sys.stderr, flush=True)
      mulu = Mulu(
        n = elem_mulu.get("n"),
        type = elem_mulu.get("type"),
        level = elem_mulu.get("level"),
      )
      juan.mulus.append(mulu)

    # print("", file=sys.stderr, flush=True)

  tick_spinner.finish()
  return segments


def collect_xml_files(files: list[str], directories: list[str]) -> list[Path]:
  """Collect XML file paths from specified files and directories."""
  target_paths = []

  # Process individually specified files
  if files:
    for f in files:
      p = Path(f)
      if p.is_file():
        target_paths.append(p)
      else:
        sys.stderr.write(f"Warning: File not found: {f}\n")

  # Collect *.xml files recursively from specified directories
  if directories:
    for d in directories:
      dir_path = Path(d)
      if dir_path.is_dir():
        target_paths.extend(dir_path.rglob("*.xml"))
      else:
        sys.stderr.write(f"Warning: Directory not found: {d}\n")

  # Deduplicate and sort file paths
  return sorted(list(set(target_paths)))


def print_progress(current: int, total: int, bar_length: int = 30):
  """Render a progress bar to sys.stderr."""
  if total == 0:
    return
  fraction = current / total
  filled = int(bar_length * fraction)
  bar = "=" * filled + "-" * (bar_length - filled)
  percent = fraction * 100
  sys.stderr.write(f"\rProcessing: [{bar}] {current}/{total} ({percent:.1f}%)")
  sys.stderr.flush()
  if current == total:
    sys.stderr.write("\n")


def main():
  args = parse_args()

  target_files = collect_xml_files(args.files, args.dir)
  meta_dict = {}

  for i, xml_file in enumerate(target_files, start=1):
    print_progress(i, len(target_files))
    dict_key = generate_key_from_filename(xml_file)
    segments = parse_xml_file(xml_file, args = args)
    meta_dict[dict_key] = {
      "xml_file": Path(xml_file).name,
      "segments": segments,
    }

  # Format JSON output with 2-space indentation
  json_data = json.dumps({
                  k: {
                    "xml_file": d["xml_file"],
                    "segments": [
                      remove_underscore_keys_in_obj(asdict(seg))
                      for seg in d["segments"]
                    ]
                  } for k, d in meta_dict.items()
                },
                ensure_ascii=False, indent=2)

  if args.output:
    Path(args.output).write_text(json_data, encoding="utf-8")
  else:
    print(json_data)

if __name__ == "__main__":
    main()

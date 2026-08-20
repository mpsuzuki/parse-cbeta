#!/usr/bin/env python3

import sys
import csv
import argparse
from pathlib import Path
from contextlib import nullcontext
from collections import Counter
from difflib import SequenceMatcher

teiHeader_title_m = "teiHeader/title[level='m']"


def parse_args():
  parser = argparse.ArgumentParser(
    description="Analyze Title-like Data in debug log"
  )
  parser.add_argument("files", nargs="*",
    help="Target XML file(s)"
  )
  parser.add_argument("--input", "-i", type=str,
    help="Input debug file (use stdin if omitted)"
  )
  parser.add_argument("--csv", type=str,
    help="Output CSV file path (prints to stdout if omitted)"
  )
  parser.add_argument("--summary", type=str,
    help="Output Summary file path (prints to stdout if omitted)"
  )
  parser.add_argument("--no-bom", action="store_true",
    help="Do not emit BOM at the header of CSV"
  )
  parser.add_argument("--list-include", "--include", "--incl", type=str,
    help="File listing XMLs to be included (all files would be included by default)"
  )
  parser.add_argument("--list-exclude", "--exclude", "--excl", type=str,
    help="File listing XMLs to be excluded (no file would be excluded by default)"
  )

  args = parser.parse_args()

  if args.input:
    args.ctx_input = open(args.input, "w", encoding="utf-8-sig")
  else:
    args.ctx_input = nullcontext(sys.stdin)

  if args.csv:
    if args.no_bom:
      args.ctx_csv = open(args.csv, "w", encoding="utf-8")
    else:
      args.ctx_csv = open(args.csv, "w", encoding="utf-8-sig")
  else:
    args.ctx_csv = nullcontext(sys.stdout)

  if args.summary:
    args.ctx_summary = open(args.summary, "w", encoding="utf-8")
  else:
    args.ctx_summary = nullcontext(sys.stdout)

  args.set_include = None
  if args.list_include:
    args.set_include = set()
    with open(args.list_include, "r", encoding="utf-8") as fh:
      for line in fh:
        if line.startswith("#"):
          continue
        line = line.split("#", 1)[0].strip()
        if len(line) > 0:
          args.set_include.add(line)

  args.set_exclude = None
  if args.list_exclude:
    args.set_exclude = set()
    with open(args.list_exclude, "r", encoding="utf-8") as fh:
      for line in fh:
        if line.startswith("#"):
          continue
        line = line.split("#", 1)[0].strip()
        if len(line) > 0:
          args.set_exclude.add(line)

  return args


def order_policies_by_contrib(dict_sets):
  ordered_pols = []
  covered_xmls = set()
  rest_pols = set(dict_sets.keys())
  while rest_pols:
    next_pol = max(rest_pols, key=lambda pol: len(dict_sets[pol] - covered_xmls))

    ordered_pols.append(next_pol)
    covered_xmls |= dict_sets[next_pol]

    rest_pols.remove(next_pol)
  return ordered_pols


def make_xml2dic_from_debug_log(fh):
  xml2dic = {}
  keys = set()
  for line in sys.stdin:
    toks = line.split(" ", 4)
    if not toks[0].startswith("INFO:root:"):
      continue

    xml_path = toks[0].split(":", 2).pop()
    xml = Path(xml_path).name
    if xml in xml2dic:
      d = xml2dic[xml]
    else:
      d = {}
      xml2dic[xml] = d

    lb_n = toks[1]
    xpath = toks[3]
    tagname = xpath.split("/").pop()
    scan_type = toks[2]
    text = toks[4].strip()

    key = f"{scan_type}/{tagname}"
    keys.add(key)

    d[key] = text.replace("|", "")
  return (keys, xml2dic)


def write_summary1(fh, fieldnames, xml2dic, rows):
  policies = fieldnames[2:]
  ## summarize "differ" case
  diff2xmls = {}
  for d in rows:
    for pol in policies:
      if pol not in d:
        continue
      d_pol = d[pol]
      if d_pol == "==" or "\u2026" in d_pol:
        continue
      if d_pol not in diff2xmls:
        diff2xmls[d_pol] = set()
      diff2xmls[d_pol].add(d["file"])

  for d_txt in sorted(diff2xmls.keys(), key=lambda k: -len(diff2xmls[k])):
    rows = [ xml2dic[xml] for xml in sorted(diff2xmls[d_txt]) ]
    if len(rows) > 1:
      print(f"differ: \"{d_txt}\" in {len(diff2xmls[d_txt])} XMLs", file=fh)
      continue

    xml = rows[0]["file"]
    title_m = rows[0][teiHeader_title_m]
    sm = None
    if title_m.startswith(d_txt):
      kind = "lost_suffix"
    elif title_m.endswith(d_txt):
      kind = "lost_prefix"
    elif d_txt in title_m:
      kind = "lost_both"
    else:
      kind = "differ"
      sm = SequenceMatcher(None, title_m, d_txt,)
    if sm:
      print(f"{kind}: "
            f"ratio={sm.ratio():.01f} "
            f"candidate=\"{d_txt}\" vs expected=\"{title_m}\" in {xml}, "
            , file=fh)
    else:
      print(f"{kind}: candidate=\"{d_txt}\" vs expected=\"{title_m}\" in {xml}"
            , file=fh)


    print("  " + ",".join(fieldnames), file=fh)
    for row in rows[:10]:
      print("  " + ",".join([
        row[f] if f in row else ""
        for f in fieldnames
      ]), file=fh)
    if len(rows) > 10:
      print("  ...", file=fh)
    print(file=fh)


def write_summary2(fh, policies, xml2dic, rows):
  ## summarize
  sets_tested  = { pol: set() for pol in policies }
  sets_equal   = { pol: set() for pol in policies }
  sets_prefix  = { pol: set() for pol in policies }
  sets_suffix  = { pol: set() for pol in policies }
  sets_both    = { pol: set() for pol in policies }
  sets_differ  = { pol: set() for pol in policies }
  for pol in policies:
    for d in rows:
      if pol not in d or d[pol] is None or len(d[pol]) == 0:
        continue
      fn = d["file"]
      sets_tested[pol].add(fn)
      if d[pol] == "==":
        sets_equal[pol].add(fn)
      elif d[pol].startswith("\u2026"):
        sets_suffix[pol].add(fn)
      elif d[pol].endswith("\u2026"):
        sets_prefix[pol].add(fn)
      elif "\u2026" in d[pol]:
        sets_both[pol].add(fn)
      else:
        sets_differ[pol].add(fn)

  policies_equal   = order_policies_by_contrib(sets_equal)
  policies_prefix  = order_policies_by_contrib(sets_prefix)
  policies_suffix  = order_policies_by_contrib(sets_suffix)
  policies_both    = order_policies_by_contrib(sets_both)

  covered_xmls_any = set()
  covered_xmls_equal = set()
  covered_xmls_prefix = set()
  covered_xmls_suffix = set()
  covered_xmls_both = set()
  for pol in policies_equal:
    toks = [ f"{pol} brings" ]
    toks.append(f"equal={len(sets_equal[pol] - covered_xmls_equal)}")
    toks.append(f"with_prefix={len(sets_prefix[pol] - covered_xmls_any)}")
    toks.append(f"with_suffix={len(sets_suffix[pol] - covered_xmls_any)}")
    toks.append(f"with_both={len(sets_both[pol] - covered_xmls_any)}")

    covered_xmls_any     |= (sets_equal[pol] |
                             sets_prefix[pol] |
                             sets_suffix[pol] |
                             sets_both[pol])
    covered_xmls_equal   |= sets_equal[pol]
    covered_xmls_prefix  |= sets_prefix[pol]
    covered_xmls_suffix  |= sets_suffix[pol]
    covered_xmls_both    |= sets_both[pol]

    print("\t".join(toks), file=fh)

  toks = ["covered XML"]
  toks.append(f"equal={len(covered_xmls_equal)}")
  toks.append(f"with_prefix={len(covered_xmls_prefix)}")
  toks.append(f"with_suffix={len(covered_xmls_suffix)}")
  toks.append(f"with_both={len(covered_xmls_both)}")
  print("\t".join(toks), file=fh)


def main():
  args = parse_args()

  with args.ctx_input as fh:
    keys, xml2dic, = make_xml2dic_from_debug_log(fh)

  xml2dic = {
    k: v
    for k, v in xml2dic.items()
    if (
      (args.set_include is None or k in args.set_include) and
      (args.set_exclude is None or k not in args.set_exclude)
    )
  }
  for xml in xml2dic.keys():
    if args.set_include and xml not in args.set_include:
      xml2dic.pop(xml)
    if args.set_exclude and xml in args.set_exclude:
      xml2dic.pop(xml)

  rows = []
  for xml in sorted(xml2dic.keys()):
    d = xml2dic[xml]
    d["file"] = xml
    rows.append(d)

  policies = [
    k
    for k in sorted(keys)
    if k.startswith("after") or k.startswith("before")
  ]
  fieldnames = ["file", teiHeader_title_m] + policies

  # compress the string including 'correct' text
  policies = fieldnames[2:]
  for xml, dic in xml2dic.items():
    tm = dic[teiHeader_title_m]
    for k, v in dic.items():
      if k not in policies:
        continue
      if v == tm:
        dic[k] = "=="
      elif tm in v:
        dic[k] = v.replace(tm, "\u2026")


  with args.ctx_summary as fh:
    write_summary1(fh, fieldnames, xml2dic, rows)
    write_summary2(fh, policies, xml2dic, rows)

  with args.ctx_csv as fh:
    if args.csv is None and not args.no_bom:
      fh.write("\ufeff")
    writer = csv.DictWriter(fh, fieldnames = fieldnames)
    writer.writeheader()
    writer.writerows(rows)

if __name__ == "__main__":
    main()

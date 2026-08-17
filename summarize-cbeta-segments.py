#!/usr/bin/env python3

import sys
import argparse
import json
from fnmatch import fnmatch
from contextlib import nullcontext, contextmanager
from cbeta_seg import JuanNumber, JuanRange, JuanHead, Mulu, Juan, OpenCloseMatch, Segment


def parse_args():
  parser = argparse.ArgumentParser(
    formatter_class=argparse.RawTextHelpFormatter,
    description="Parse CBETA Analysis JSON and Summarize it"
  )
  parser.add_argument("--ignore-complete-sutra", action="store_true",
    help="Do not print about XML whose segments are all properly opened & closed"
  )
  parser.add_argument("--no-comment-statistics", action="store_true",
    help="Do not print comment for statistic of single XML file"
  )
  parser.add_argument("--show-events", "--show-event", action="store_true",
    help="Print events in stacking juan elements"
  )
  parser.add_argument("--verbose", "-v", action="count", default=0,
    help="verbose mode"
  )
  parser.add_argument("--json", type=str,
    help="Load input data from a file specified by JSON"
  )
  available_tag = "\n".join(OpenCloseMatch.names())
  parser.add_argument("--filter", type=str, default="*",
    help=f"Limit openclose status to print (default: *)\n(available:\n{available_tag}\n)"
  )

  args = parser.parse_args()

  if args.filter:
    args.filter = args.filter.split(",")

  if args.json:
    args.ctx_json = open(args.json, "r", encoding="utf-8-sig")
  else:
    args.ctx_json = nullcontext(sys.stdin)

  return args

def append_stack_info(seg, lines):
  lines.append(seg.get_log_openclose())
  lines.append(seg.get_summary_openclose())

def main():
  args = parse_args()
  with args.ctx_json as fh_json:
    t2vs = {
      tnum: {
        "xml_file": d["xml_file"],
        "segments": [
          Segment.from_dict(seg) for seg in d["segments"]
        ],
      }
      for tnum, d in json.load(fh_json).items()
    }

  # print(f"t2vs: {len(t2vs)} sutra")
  print_something = False
  for tnum, dic in t2vs.items():
    xml_file = dic["xml_file"]
    segments = dic["segments"]
    num_segs = len(segments)
    num_segs1 = max(0, num_segs - 1)
    is_multi = (num_segs > 1)
    for i, seg in enumerate(segments):
      is_first = (i == 0)
      is_last = (i == num_segs1)
      inspect_result = seg.inspect_juans()

      oc = seg._cache.openclose
      jns = seg._cache.juan_ns

      oc.status_suffix = "MULTI" if is_multi else "SINGLE"
      if oc.status == OpenCloseMatch.INCOMPLETE:
        if is_first or is_last:
          oc.status = OpenCloseMatch.EDGE_INCOMPLETE
        else:
          oc.status = OpenCloseMatch.INNER_INCOMPLETE

        if is_first and jns.open == "(none)":
          oc.status = OpenCloseMatch.HEAD_UNOPENED
        elif is_first and jns.close == "(none)":
          oc.status = OpenCloseMatch.HEAD_UNCLOSED
        elif is_last and jns.open == "(none)":
          oc.status = OpenCloseMatch.TAIL_UNOPENED
        elif is_last and jns.close == "(none)":
          oc.status = OpenCloseMatch.TAIL_UNCLOSED

    num_segments = len(segments)
    num_complete = len([seg for vol in segments if (vol.is_complete() == True)])
    num_incomplete = len([seg for vol in segments if (vol.is_incomplete() == True)])
    num_inconsistent = len([seg for vol in segments if (vol.is_inconsistent() == True)])
    if args.ignore_complete_sutra and num_incomplete == 0 and num_inconsistent == 0:
      continue

    lines = []
    for i, seg in enumerate(segments):
      oc = seg._cache.openclose
      try:
        tag = f"{oc.status}:{oc.status_suffix}"
      except:
        tag = oc.status

      for pat in args.filter:
        if fnmatch(tag, pat):
          if args.show_events:
            append_stack_info(seg, lines)
          elif len(seg._stack.events) == 1:
            pass
          elif len(seg._stack.events) == 2 and seg.is_complete():
            pass
          else:
            append_stack_info(seg, lines)
          lines.append(f"{xml_file}\tseg:{i+1:03d}/{num_segs:03d}\t{seg.get_str_inspect_juans()}")
          break

    if len(lines) == 0:
      continue

    if not args.no_comment_statistics:
      per_incomplete = float(100 * num_incomplete) / num_segments
      per_inconsistent = float(100 * num_inconsistent) / num_segments
      # print(f"# {xml_file} incomplete={num_incomplete} inconsistent={num_inconsistent}")
      if print_something:
        print("")
      print(f"# {xml_file} incomplete={per_incomplete:.1f}% inconsistent={per_inconsistent:.1f}%")
      print_something = True

    for l in lines:
      print(l)
      print_something = True

if __name__ == "__main__":
    main()

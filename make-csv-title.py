#!/usr/bin/env python3

import sys
import csv
from pathlib import Path
from collections import Counter

teiHeader_title_m = "teiHeader/title[level='m']"

xml2dic = {}

keys = set()
for line in sys.stdin:
  toks = line.split(" ", 4)
  if not toks[0].startswith("INFO:root:"):
    continue

  xml_path = toks[0].split(":", 2).pop()
  if xml_path in xml2dic:
    d = xml2dic[xml_path]
  else:
    d = {}
    xml2dic[xml_path] = d

  lb_n = toks[1]
  xpath = toks[3]
  tagname = xpath.split("/").pop()
  scan_type = toks[2]
  text = toks[4].strip()

  key = f"{scan_type}/{tagname}"
  keys.add(key)

  d[key] = text.replace("|", "")

# -----------------
# compress
#
policies = [
  k
  for k in keys
  if k.startswith("after") or k.startswith("before")
]
for xml_path, dic in xml2dic.items():
  tm = dic[teiHeader_title_m]
  for k, v in dic.items():
    if k not in policies:
      continue
    if v == tm:
      dic[k] = "=="
    elif tm in v:
      dic[k] = v.replace(tm, "\u2026")

rows = []
for xml_path in sorted(xml2dic.keys()):
  d = xml2dic[xml_path]
  d["file"] = Path(xml_path).name
  rows.append(d)

fieldnames = ["file", teiHeader_title_m] + policies

## summarize
sets_tested  = { pol: set() for pol in policies }
sets_equal   = { pol: set() for pol in policies }
sets_prefix  = { pol: set() for pol in policies }
sets_suffix  = { pol: set() for pol in policies }
sets_affixes = { pol: set() for pol in policies }
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
      sets_affixes[pol].add(fn)
    elif "\u2026" in d[pol]:
      sets_affixes[pol].add(fn)


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

policies = order_policies_by_contrib(sets_equal)
covered_xmls = set()
for pol in policies:
  print(f"{pol} saves {len(sets_equal[pol] - covered_xmls)} XMLs")  
  covered_xmls |= sets_equal[pol]
print(f"sets_equal has {len(covered_xmls)} XMLs in total")

#total = Counter()
#summary = {
#  k: Counter()
#  for k in fieldnames
#  if k.startswith("after") or k.startswith("before")
#}
#for d in rows:
#  for k, v in d.items():
#    k_prefix = k.split("-", 1)[0]
#    if k_prefix not in ("after", "before"):
#      continue
#
#    total[k] += 1
#    if v == "==":
#      summary[k]["equal"] += 1
#    elif v.startswith("\u2026"):
#      summary[k]["has_suffix"] += 1
#    elif v.endswith("\u2026"):
#      summary[k]["has_prefix"] += 1
#    elif "\u2026" in v:
#      summary[k]["has_affixes"] += 1
#    else:
#      summary[k]["differ"] += 1
#  
#for k in summary.keys():
#  toks = [ k ]
#  for k2 in ("equal", "has_prefix", "has_suffix", "has_affixes", "differ"):
#    toks.append(f"{k2}={summary[k][k2]}/{total[k]}")
#  print("\t".join(toks))


writer = csv.DictWriter(sys.stdout, fieldnames = fieldnames)

sys.stdout.write("\ufeff")
writer.writeheader()
writer.writerows(rows)

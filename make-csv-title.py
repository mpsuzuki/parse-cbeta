#!/usr/bin/env python3

import sys
import csv
from pathlib import Path
from collections import Counter
from difflib import SequenceMatcher

teiHeader_title_m = "teiHeader/title[level='m']"

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

# -----------------
# compress
#
policies = [
  k
  for k in keys
  if k.startswith("after") or k.startswith("before")
]
for xml, dic in xml2dic.items():
  tm = dic[teiHeader_title_m]
  for k, v in dic.items():
    if k not in policies:
      continue
    if v == tm:
      dic[k] = "=="
    elif tm in v:
      dic[k] = v.replace(tm, "\u2026")

rows = []
for xml in sorted(xml2dic.keys()):
  d = xml2dic[xml]
  d["file"] = xml
  rows.append(d)

fieldnames = ["file", teiHeader_title_m] + policies

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
    print(f"\"{d_txt}\" in {len(diff2xmls[d_txt])} XMLs")
  else:
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
      print(f"{kind}: candidate=\"{d_txt}\" vs expected=\"{title_m}\" in {xml}, ratio={sm.ratio():.01f}")
    else:
      print(f"{kind}: candidate=\"{d_txt}\" vs expected=\"{title_m}\" in {xml}")


  print("  " + ",".join(fieldnames))
  for row in rows[:10]:
    print("  " + ",".join([
      row[f] if f in row else ""
      for f in fieldnames
    ]))
  if len(rows) > 10:
    print("  ...")
  print()




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

  print("\t".join(toks))

toks = ["covered XML"]
toks.append(f"equal={len(covered_xmls_equal)}")
toks.append(f"with_prefix={len(covered_xmls_prefix)}")
toks.append(f"with_suffix={len(covered_xmls_suffix)}")
toks.append(f"with_both={len(covered_xmls_both)}")
print("\t".join(toks))

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
#      summary[k]["with_suffix"] += 1
#    elif v.endswith("\u2026"):
#      summary[k]["with_prefix"] += 1
#    elif "\u2026" in v:
#      summary[k]["with_both"] += 1
#    else:
#      summary[k]["differ"] += 1
#  
#for k in summary.keys():
#  toks = [ k ]
#  for k2 in ("equal", "with_prefix", "with_suffix", "with_both", "differ"):
#    toks.append(f"{k2}={summary[k][k2]}/{total[k]}")
#  print("\t".join(toks))


writer = csv.DictWriter(sys.stdout, fieldnames = fieldnames)

sys.stdout.write("\ufeff")
writer.writeheader()
writer.writerows(rows)

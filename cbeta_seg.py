import re
from collections import Counter
from dataclasses import dataclass, field
from enum import IntEnum
from attrdict import AttrDict

#
# use remove_underscore_keys_in_obj(asdict(obj))
# to exclude internal items, like Segment._cache
#
def remove_underscore_keys_in_obj(obj, jsonable=True):
  if isinstance(obj, dict):
    return {
      k: remove_underscore_keys_in_obj(v)
      for k, v in obj.items()
      if not k.startswith("_")
    }

  if isinstance(obj, list) or ( jsonable and isinstance(obj, (tuple, set)) ):
    return [
      remove_underscore_keys_in_obj(o)
      for o in obj
    ]

  if isinstance(obj, tuple):
    return tuple(
      remove_underscore_keys_in_obj(o)
      for o in obj
    )

  if isinstance(obj, set):
    return {
      remove_underscore_keys_in_obj(o)
      for o in obj
    }
  else:
    return obj


@dataclass
class JuanNumber:
  UNKNOWN = -1
  DIGITS = 0
  DIGITS_ALPHA = 1
  DIGITS_ALPHA_HYPHEN_DIGIT = 2

  value: str
  format: int = UNKNOWN
  page: int | None = None
  subpage: str | None = None
  subsubpage: int | None = None

  @classmethod
  def get_format(cls, value: str) -> int:
    if re.match(r"^\d+$", value):
      return JuanNumber.DIGITS
    elif re.match(r"^\d+[a-z]$", value):
      return JuanNumber.DIGITS_ALPHA
    elif re.match(r"^\d+[a-z]-[0-9]$", value):
      return JuanNumber.DIGITS_ALPHA_HYPHEN_DIGIT
    else:
      return JuanNumber.UNKNOWN

  def isDigits(self):
    return (self.format == JuanNumber.DIGITS)

  def isDigitsAlpha(self):
    return (self.format == JuanNumber.DIGITS_ALPHA)

  def isDigitsAlphaHyphenDigit(self):
    return (self.format == JuanNumber.DIGITS_ALPHA_HYPHEN_DIGIT)

  def isUnknown(self):
    return self.format not in (
      JuanNumber.DIGITS,
      JuanNumber.DIGITS_ALPHA,
      JuanNumber.DIGITS_ALPHA_HYPHEN_DIGIT,
    )

  def __post_init__(self):
    self.format = JuanNumber.get_format(self.value)
    if self.isUnknown():
      return

    m = re.match(r"^(\d+)([a-z]?)(?:-(\d+))?", self.value)
    if m is None:
      pass
    else:
      self.page = int(m.group(1)) if m.group(1) else None
      self.subpage = m.group(2) or None
      self.subsubpage = int(m.group(3)) if m.group(3) else None

  def __eq__(self, other):
    if self.format != other.format:
      return False
    elif self.page != other.page:
      return False
    elif self.subpage != other.subpage:
      return False
    elif self.subsubpage != other.subsubpage:
      return False

    return True


  def is_consecutive(self, other):
    if self.format != other.format:
      return False
    elif self.isDigits():
      return (
        ((self.page + 1) == other.page)
      )
    elif self.isDigitsAlpha():
      return (
        (self.page == other.page) and
        ((ord(self.subpage) + 1) == ord(other.subpage))
      )
    elif self.isDigitsAlphaHyphenDigit():
      return (
        (self.page == other.page) and
        (self.subpage == other.subpage) and
        ((self.subsubpage + 1) == other.subsubpage)
      )
    else: # comparison of unknown
      return False


@dataclass
class JuanRange:
  first: JuanNumber
  last: JuanNumber

  def appendable(self, value: JuanNumber) -> bool:
    if self.last.is_consecutive(value):
      return True
    else:
      return False

  def __str__(self):
    if self.first.value == self.last.value:
      return self.first.value
    elif self.first.format == self.last.format and not self.first.isUnknown():
      if self.first.isDigits():
        return f"{self.first.value}..{self.last.value}"
      elif self.first.isDigitsAlpha():
        return f"{self.first.value}..{self.last.subpage}"
      elif self.first.isDigitsAlphaHyphenDigit():
        return f"{self.first.value}..{self.last.subsubpage}"
    else:
      return f"{self.first.value}..{self.last.value}"

  def __repr__(self):
    return f"JuanRange({self})"


@dataclass
class JuanHead:
  head: str | None = None
  title: str | None = None
  tail: str | None = None

  @classmethod
  def from_dict(cls, dic):
    head = dic["head"]
    title = dic["title"]
    tail = dic["tail"]
    return JuanHead(head=head, title=title, tail=tail)

  def __str__(self):
    return f"{self.head}|{self.title}|{self.tail}"

  def __repr__(self):
    return f"JuanHead(\'{self.head}\',\'{self.title}\',\'{self.tail}\')"


@dataclass
class Mulu:
  n: str | None = None
  type: str | None = None
  level: str | None = None

  @classmethod
  def from_dict(cls, dic):
    n = dic["n"] or None
    type = dic["type"] or None
    level = dic["level"] or None
    return Mulu(n=n, type=type, level=level)


@dataclass
class Juan:
  fun: str | None = None
  n: str | None = None
  heads: list[JuanHead] = field(default_factory = list)
  mulus: list[Mulu] = field(default_factory = list)

  @classmethod
  def from_dict(cls, dic, check_heads=False, check_mulus=False):
    fun = dic["fun"] or None
    n = dic["n"] or None
    heads = [ JuanHead.from_dict(h) for h in dic["heads"] ]
    mulus = [ Mulu.from_dict(h) for h in dic["mulus"] ]
    return Juan(fun=fun, n=n, heads=heads, mulus=mulus)

  def is_open(self):
    return (self.fun == "open")

  def is_close(self):
    return (self.fun == "close")

  def n_parsed(self):
    return JuanNumber(self.n)

  def get_heads_texts(self):
    return ",".join([str(jh) for jh in self.heads])

  def pair_with(self, other, compare_as_str=False, check_heads=False, check_mulus=False):
    if self.is_open() and other.is_close():
      pass
    elif self.is_close() and other.is_open():
      pass
    else:
      return False

    if compare_as_str:
      if self.n != other.n:
        return False
    else:
      if self.n_parsed() != other.n_parsed():
        return False

    if check_heads:
      if self.heads != other.heads:
        return False

    if check_mulus:
      if self.mulus != other.mulus:
        return False

    return True

class OpenCloseMatch(IntEnum):
  NULL = 0
  COMPLETE = 1
  INCONSISTENT = 2
  INCOMPLETE = 3
  INNER_INCOMPLETE = 4
  EDGE_INCOMPLETE = 5
  HEAD_UNOPENED = 6
  HEAD_UNCLOSED = 7
  TAIL_UNOPENED = 8
  TAIL_UNCLOSED = 9

  @classmethod
  def names(cls):
    return [ entry.name for entry in OpenCloseMatch ]

  @classmethod
  def name2int(cls, i):
    return OpenCloseMatch(i).name

  def __str__(self):
    return self.name


@dataclass
class JuanStackEvent:
  EMPTY = "empty"
  SUCCESS_OPEN = "success_open"
  SUCCESS_CLOSE = "success_close"
  # FAIL_OPEN = "fail_open"
  FAIL_CLOSE = "fail_close"

  event: str
  n_expected: JuanNumber | None = None
  n_actual: JuanNumber | None = None

  @classmethod
  def empty(cls):
    return JuanStackEvent(JuanStackEvent.EMPTY)

  @classmethod
  def good(cls, obj, obj_top_stack = None):
    n = obj.n_parsed()
    if obj.is_open():
      return JuanStackEvent(JuanStackEvent.SUCCESS_OPEN,
                            n_expected=None, n_actual=n)
    elif obj.is_close():
      return JuanStackEvent(JuanStackEvent.SUCCESS_CLOSE,
                            n_expected=obj_top_stack.n_parsed(),
                            n_actual=n)
    else:
      return JuanStackEvent(JuanStackEvent.EMPTY)

  @classmethod
  def bad(cls, obj, obj_top_stack):
    return JuanStackEvent(JuanStackEvent.FAIL_CLOSE,
                          n_expected=(None if obj_top_stack is None else obj_top_stack.n_parsed()),
                          n_actual=obj.n_parsed())

  def is_good(self):
    return self.event.startswith("success_")

  def is_bad(self):
    return self.event.startswith("fail_")

  def __str__(self):
    return f"{self.event}({
      '' if self.n_expected is None else self.n_expected.value
    }←{
      '' if self.n_actual is None else self.n_actual.value
    })"

  def __repr__(self):
    return f"JuanStackEvent({self.event}, {self.n_expected or None}, {self.n_actual or None})"

class JuanStackAppendResult(IntEnum):
  FAIL_CLOSE_CROSSED = -2
  FAIL_CLOSE_UNOPENED = -1
  UNKNOWN_OBJECT = 0
  SUCCESS_OPENED = 1
  SUCCESS_CLOSED = 2

@dataclass
class JuanStack:
  stack: list[Juan] = field(default_factory = list)
  events: list[JuanStackEvent] = field(default_factory = list)
  counts: Counter = field(default_factory = Counter)

  def depth(self):
    return len(self.stack)

  def count_result(self, result):
    self.counts[result] += 1
    return result

  def index_to_open_this(self, obj):
    if not obj.is_close():
      return None

    for i1 in range(len(self.stack), 0, -1):
      i = i1 - 1
      oi = self.stack[i]
      if oi.n_parsed() != obj.n_parsed():
        continue
      if oi.is_open():
        return i

    return -1


  def get_top(self, confirm=True):
    obj_top = self.stack[-1] if self.depth() > 0 else None

    if (not confirm) or (confirm and isinstance(obj_top, Juan)):
      return obj_top
    else:
      return None

  def get_top_check_closable_by(self, obj):
    obj_top = self.get_top()

    if obj_top is None:
      return (False, None)

    if obj_top.n_parsed() == obj.n_parsed():
      return (True, obj_top)

    return (False, obj_top)

  def append(self, obj):
    if obj.is_open():
      self.events.append(JuanStackEvent.good(obj))
      self.stack.append(obj)
      return self.count_result( JuanStackAppendResult.SUCCESS_OPENED )

    elif obj.fun == "close":
      is_closable, obj_top = self.get_top_check_closable_by(obj)

      if is_closable:
        self.events.append(JuanStackEvent.good(obj, obj_top))
        self.stack.pop()
        return self.count_result( JuanStackAppendResult.SUCCESS_CLOSED )

      i_open = self.index_to_open_this(obj)
      if i_open is None:
        # should not happen, obj is already confirmed to be a closer.
        self.events.append(JuanStackEvent.empty())
        return self.count_result( JuanStackAppendResult.UNKNOWN_OBJECT )
      elif i_open < 0:
        self.events.append(JuanStackEvent.bad(obj, obj_top))
        return self.count_result( JuanStackAppendResult.FAIL_CLOSE_UNOPENED )
      else:
        # self.stack.pop(i_open)
        return self.count_result( JuanStackAppendResult.FAIL_CLOSE_CROSSED )

    else:
      return self.count_result( JuanStackAppendResult.UNKNOWN_OBJECT )

  def has_crossed(self):
    return (self.counts[JuanStackAppendResult.FAIL_CLOSE_CROSSED] > 0)

  def has_unopened(self):
    return (self.counts[JuanStackAppendResult.FAIL_CLOSE_UNOPENED] > 0)

  def has_unclosed(self):
    return (self.depth() > 0)

  def count_success_opened(self):
    return self.counts[JuanStackAppendResult.SUCCESS_OPENED]

  def count_success_closed(self):
    return self.counts[JuanStackAppendResult.SUCCESS_CLOSED]

  def count_fail_unopened(self):
    return self.counts[JuanStackAppendResult.FAIL_CLOSE_UNOPENED]

  def count_fail_crossed(self):
    return self.counts[JuanStackAppendResult.FAIL_CLOSE_CROSSED]

  def is_balanced(self):
    if self.has_unclosed():
      return False

    if self.count_fail_unopened():
      return False

    if self.count_fail_crossed():
      return False

    return True

  def get_event_log(self):
    return [ str(ev) for ev in self.events ]

  def count_bad_events(self):
    return sum(ev.is_bad() for ev in self.events)

@dataclass
class Segment:
  n: str | None		# <milestone n="..."/>
  unit: str | None	# <milestone unit="..."/>

  # belows are determined by the <lb /> elements
  #   after current milestone and before next milestione
  #
  lb_n_first: str | None = None
  lb_n_last: str | None = None

  # belows are determined by the <cb:juan>...</cb:juan> elements
  #   after current milestone and before next milestione
  juans: list[Juan] = field(default_factory = list)

  _cache: AttrDict = field(default_factory = AttrDict)
  _stack: JuanStack = field(default_factory = JuanStack)


  @classmethod
  def from_dict(cls, dic):
    n = dic["n"] or None
    unit = dic["unit"] or None
    lb_n_first = dic["lb_n_first"] or None
    lb_n_last = dic["lb_n_last"] or None
    juans = [ Juan.from_dict(jd) for jd in dic["juans"] ]
    return Segment(n=n, unit=unit,
                  lb_n_first=lb_n_first,
                  lb_n_last=lb_n_last,
                  juans=juans)


  def get_juans_open(self):
    return [ j for j in self.juans if j.is_open() ]


  def get_juans_close(self):
    return [ j for j in self.juans if j.is_close() ]


  def get_str_inspect_juans(self):
    oc_stat = self._cache.openclose.status or None
    try:
      oc_suffix = f":{self._cache.openclose.status_suffix}"
    except:
      oc_suffix = ""
    rel = self._cache.openclose.relation or None
    juan_ns_open = self._cache.juan_ns.open or None
    juan_ns_close = self._cache.juan_ns.close or None
    heads_texts_open = self._cache.heads.open.texts or None
    heads_texts_close = self._cache.heads.close.texts or None
    return (
      f"{juan_ns_open} {rel} {juan_ns_close}\t{oc_stat}{oc_suffix}\t"
      f"{heads_texts_open}\t{heads_texts_close}"
    )

  def is_complete(self):
    return (self._cache.openclose.status == OpenCloseMatch.COMPLETE)

  def is_inconsistent(self):
    return (self._cache.openclose.status == OpenCloseMatch.INCONSISTENT)

  def is_incomplete(self):
    return (self._cache.openclose.status in (
        OpenCloseMatch.INCOMPLETE,
        OpenCloseMatch.EDGE_INCOMPLETE,
        OpenCloseMatch.INNER_INCOMPLETE,
        OpenCloseMatch.HEAD_UNOPENED,
        OpenCloseMatch.HEAD_UNCLOSED,
        OpenCloseMatch.TAIL_UNOPENED,
        OpenCloseMatch.TAIL_UNCLOSED,
    ))

  def inspect_juans_openclose(self):
    stack = self._stack
    for j in self.juans:
      stack.append(j)

  def inspect_juans(self):
    self.inspect_juans_openclose()

    juans_open  = self.get_juans_open()
    juans_close = self.get_juans_close()

    self._cache.juan_ns = AttrDict()
    self._cache.juan_ns.open = ",".join(str(j.n) for j in juans_open) or "(none)"
    self._cache.juan_ns.close = ",".join(str(j.n) for j in juans_close) or "(none)"

    unmatched = AttrDict.from_dict({"open": 0, "close": 0})

    # all open has counter close
    for jo in juans_open:
      if all((not jo.pair_with(jc) for jc in juans_close)):
        unmatched.open += 1

    # all close has counter open
    for jc in juans_close:
      if all((not jc.pair_with(jo) for jo in juans_open)):
        unmatched.close += 1

    self._cache.heads = AttrDict.from_dict({"open": AttrDict(), "close": AttrDict()})
    self._cache.heads.open.texts  = [ jo.get_heads_texts() for jo in juans_open ]
    self._cache.heads.close.texts = [ jc.get_heads_texts() for jc in juans_close ]

    if unmatched.open > 0 and unmatched.close > 0:
      self._cache.openclose = AttrDict.from_dict({
        "status": OpenCloseMatch.INCONSISTENT,
        "relation": "!="
      })
    elif unmatched.open > unmatched.close:
      self._cache.openclose = AttrDict.from_dict({
        "status": OpenCloseMatch.INCOMPLETE,
        "relation": ">"
      })
    elif unmatched.open < unmatched.close:
      self._cache.openclose = AttrDict.from_dict({
        "status": OpenCloseMatch.INCOMPLETE,
        "relation": "<"
      })
    else:
      self._cache.openclose = AttrDict.from_dict({
        "status": OpenCloseMatch.COMPLETE,
        "relation": "=="
      })

    return self.get_str_inspect_juans()

  def get_summary_openclose(self):
    stack = self._stack
    return ("## "
            + f" open_success:{stack.count_success_opened()}"
            + f" close_success:{stack.count_success_closed()}"
            + (f" close_crossed:{stack.count_fail_crossed()}" if stack.has_crossed() else "")
            + (f" close_unopened:{stack.count_fail_unopened()}" if stack.has_unopened() else "")
    )

  def get_log_openclose(self):
    stack = self._stack
    return ("### " + ", ".join(stack.get_event_log()))

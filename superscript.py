a2s = {
    "0": "\u2070",  # ⁰
    "1": "\u00B9",  # ¹
    "2": "\u00B2",  # ²
    "3": "\u00B3",  # ³
    "4": "\u2074",  # ⁴
    "5": "\u2075",  # ⁵
    "6": "\u2076",  # ⁶
    "7": "\u2077",  # ⁷
    "8": "\u2078",  # ⁸
    "9": "\u2079",  # ⁹

    "a": "\u1D43",  # ᵃ
    "b": "\u1D47",  # ᵇ
    "c": "\u1D9C",  # ᶜ
    "d": "\u1D48",  # ᵈ
    "e": "\u1D49",  # ᵉ
    "f": "\u1DA0",  # ᶠ
    "g": "\u1D4D",  # ᵍ
    "h": "\u02B0",  # ʰ
    "i": "\u2071",  # ⁱ
    "j": "\u02B2",  # ʲ
    "k": "\u1D4F",  # ᵏ
    "l": "\u02E1",  # ˡ
    "m": "\u1D50",  # ᵐ
    "n": "\u207F",  # ⁿ
    "o": "\u1D52",  # ᵒ
    "p": "\u1D56",  # ᵖ
    # "q": None,      # Unicodeに標準的なものなし
    "r": "\u02B3",  # ʳ
    "s": "\u02E2",  # ˢ
    "t": "\u1D57",  # ᵗ
    "u": "\u1D58",  # ᵘ
    "v": "\u1D5B",  # ᵛ
    "w": "\u02B7",  # ʷ
    "x": "\u02E3",  # ˣ
    "y": "\u02B8",  # ʸ
    "z": "\u1DBB",  # ᶻ

    "+": "\u207A",  # ⁺
    "-": "\u207B",  # ⁻
    "=": "\u207C",  #
}

s2a = {
  s: a
  for a, s in a2s.items()
}

def fromASCII(a, fallback = None):
  return a2s[a] if a in a2s else fallback

def fromStringASCII(str, fallback = ""):
  return "".join(fromASCII(a, fallback) for a in str)

def fromSuper(s, fallback = None):
  return s2a[s] if s in s2a else fallback

def fromStringSuper(str, fallback = ""):
  return "".join(fromSuper(s, fallback) for s in str)

def dropSuper(s):
  return "".join(c for c in s if c not in s2a)

from dataclasses import dataclass

@dataclass
class AttrDict:
  @classmethod
  def from_dict(cls, dic):
    ad = AttrDict()
    for k, v in dic.items():
      setattr(ad, k, v)
    return ad

  def assign_attrdicts_to_keys(self, keys):
    for k in keys:
      setattr(self, k, AttrDict())
    return self

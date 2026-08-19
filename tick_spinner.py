from dataclasses import dataclass, field
import sys
from typing import TextIO


@dataclass
class TickSpinner:
  file: TextIO = sys.stderr
  tick_interval: int = 500
  count: int = 0
  spinner: tuple[str, ...] = ("/", "-", "\\", "|")
  label: str = ""


  def progress(self):
    if self.tick_interval < 1:
      return

    self.count += 1

    if self.count % self.tick_interval != 0:
      return

    idx = (self.count // self.tick_interval) % len(self.spinner)

    print(
      f"\r{self.label} {self.spinner[idx]}",
      end="",
      flush=True,
      file=self.file,
    )

  def finish(self):
    if self.tick_interval < 1:
      return
    print("\r ", file=self.file)

  def set_spinner(self, *chars: str):
    if chars:
      self.spinner = chars

  def set_label(self, label: str):
    self.label = label

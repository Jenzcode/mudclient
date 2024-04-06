import re

class ansi:
  pat_escape = re.compile(b'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


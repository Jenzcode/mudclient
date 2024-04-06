import re

pat_escape = re.compile(b'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


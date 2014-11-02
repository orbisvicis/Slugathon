__copyright__ = "Copyright (c) 2014 Yclept Nemo"
__license__ = "GNU GPL v3"


import enum


class StrValueEnum(enum.Enum):
    def __str__(self):
        return str(self.value)

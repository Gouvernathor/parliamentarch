from collections.abc import Sequence
from typing import NamedTuple

class FactoryDict(dict):
    def __init__(self, default_factory, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_factory = default_factory

    def __missing__(self, key):
        self[key] = value = self.default_factory(key)
        return value

class UnPicklable:
    def __reduce__(self):
        raise TypeError(f"{self.__class__.__name__} is not picklable")

class Color(NamedTuple):
    r: int
    g: int
    b: int
    a: int = 255
    @property
    def hexcode(self) -> str:
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}{self.a:02x}"
    @classmethod
    def from_any(cls, o):
        if isinstance(o, cls):
            return o
        if isinstance(o, str):
            oo = o
            if oo.startswith("#"):
                oo = oo[1:]
            if len(oo) in (3, 4):
                oo = "".join(2*c for c in oo)
            if len(oo) in (6, 8):
                return cls(*(int(oo[i:i+2], 16) for i in range(0, len(oo), 2)))
        elif isinstance(o, Sequence) and len(o) in (3, 4):
            return cls(*o)
        raise ValueError(f"Cannot convert {o!r} to a {cls.__name__}")

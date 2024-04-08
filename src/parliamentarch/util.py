from collections.abc import Container, Sequence
from io import StringIO
from typing import Any, NamedTuple

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
    def from_any(cls, o, /):
        if isinstance(o, cls):
            return o
        if isinstance(o, str):
            oo = o
            if oo.startswith("#"):
                oo = oo[1:]
            if set(oo).issubset("0123456789abcdefABCDEF"):
                if len(oo) in (3, 4):
                    oo = "".join(2*c for c in oo)
                if len(oo) in (6, 8):
                    return cls(*(int(oo[i:i+2], 16) for i in range(0, len(oo), 2)))
        elif isinstance(o, Sequence) and len(o) in (3, 4):
            return cls(*o)
        raise ValueError(f"Cannot convert {o!r} to a {cls.__name__}")

def get_from_write(write_func):
    def get(*args, **kwargs) -> str:
        sio = StringIO()
        write_func(sio, *args, **kwargs)
        return sio.getvalue()
    return get

def filter_kwargs(
        *sets: Container[str],
        **kwargs: Any,
        ) -> list[dict[str, Any]]:
    """
    The length of the list is one more than the number of sets passed.
    The sets may actually be any container.
    """

    rvdicts = []
    for s in sets:
        rvdict = {}
        # no set operations in order to keep the ordering
        for k in tuple(kwargs):
            if k in s:
                rvdict[k] = kwargs.pop(k)
        if not kwargs:
            break

    rvdicts.append(kwargs)
    return rvdicts

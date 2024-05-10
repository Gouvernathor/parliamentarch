from collections.abc import Callable, Container, Sequence
from inspect import Parameter, signature
from io import TextIOBase
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
    def from_any(cls, o, /):
        if isinstance(o, cls):
            return o
        if isinstance(o, str):
            oo = o.removeprefix("#")
            if set(oo).issubset("0123456789abcdefABCDEF"):
                if len(oo) in (3, 4):
                    oo = "".join(2*c for c in oo)
                if len(oo) in (6, 8):
                    return cls(*(int(oo[i:i+2], 16) for i in range(0, len(oo), 2)))
        elif isinstance(o, Sequence) and len(o) in (3, 4):
            return cls(*o)
        raise ValueError(f"Cannot convert {o!r} to a {cls.__name__}")

_file_parameter = Parameter("file",
    Parameter.POSITIONAL_ONLY,
    annotation=str | TextIOBase)

def write_from_get(get_func: Callable[..., str]) -> Callable[..., None]:
    def write_func(file, /, *args, **kwargs):
        if isinstance(file, str):
            with open(file, "w") as f:
                return write_func(f, *args, **kwargs)
        print(get_func(*args, **kwargs), file=file)

    get_sig = signature(get_func)
    write_sig = get_sig.replace(
        parameters=[_file_parameter] + list(get_sig.parameters.values()))
    write_func.__signature__ = write_sig
    write_func.__name__ = get_func.__name__.replace("get_", "write_")
    return write_func

def filter_kwargs[V](
        *sets: Container[str],
        **kwargs: V,
        ) -> list[dict[str, V]]:
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
        rvdicts.append(rvdict)

    rvdicts.append(kwargs)
    return rvdicts

import dataclasses
from functools import partial
import json
from typing import Any
import xml.etree.ElementTree as ET

from .organize import _Organized
from .scrape import _Path, _Scraped, Color


def json_serializer(o: object) -> Any:
    """
    To be passed as the `default` parameter to `json.dump` or `json.dumps`.
    """
    if isinstance(o, Color):
        return str(o)
    if dataclasses.is_dataclass(o) and not isinstance(o, type):
        # return dataclasses.asdict(o) # recursive, bad
        return dict(__typename__=type(o).__name__) | {f.name: value for f in dataclasses.fields(o) if (value := getattr(o, f.name)) is not None}
    if isinstance(o, ET.Element) and (o.tag.rpartition("}")[2] == "title") and (not o.attrib) and (not o[:]) and o.text:
        return o.text
    raise TypeError(f"Cannot serialize {o!r}.")

def json_object_hook(d: dict[str, Any]) -> Any:
    """
    To be passed as the `object_hook` parameter to `json.load` or `json.loads`.
    """
    typname = d.pop("__typename__", None)
    if typname:
        for typ in (_Organized, _Path, _Scraped, Color):
            if typ.__name__ == typname:
                return typ(**d)
    return d

# parse_float=str, parse_int=str
json_loads = partial(json.loads, object_hook=json_object_hook)
json_load = partial(json.load, object_hook=json_object_hook)
json_dumps = partial(json.dumps, default=json_serializer)
json_dump = partial(json.dump, default=json_serializer)

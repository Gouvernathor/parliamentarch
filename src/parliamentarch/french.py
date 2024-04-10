from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from io import TextIOBase
import re
from typing import NamedTuple, Self
import warnings
import xml.etree.ElementTree as ET

class Color(NamedTuple):
    r: int
    g: int
    b: int
    a: int = 255

    @classmethod
    def from_hex(cls, hex: str) -> Self:
        hex = hex.removeprefix("#")
        a = 255
        match len(hex):
            case 6:
                r = int(hex[:2], 16)
                g = int(hex[2:4], 16)
                b = int(hex[4:], 16)
            case 8:
                r = int(hex[:2], 16)
                g = int(hex[2:4], 16)
                b = int(hex[4:6], 16)
                a = int(hex[6:], 16)
            case 3:
                r = int(hex[0], 16) * 0x11
                g = int(hex[1], 16) * 0x11
                b = int(hex[2], 16) * 0x11
            case 4:
                r = int(hex[0], 16) * 0x11
                g = int(hex[1], 16) * 0x11
                b = int(hex[2], 16) * 0x11
                a = int(hex[3], 16) * 0x11
        return cls(r, g, b, a)

    def __str__(self):
        s = f"#{self.r:2x}{self.g:2x}{self.b:2x}"
        if self.a != 255:
            s += f"{self.a:2x}"
        return s

    __repr__ = __str__

@dataclass
class _Path:
    d: str
    transform: str|None = None
    clazz: str|None = None
    id: str|None = None
    style: str|dict[str, str|Color]|None = None
    stroke: str|Color|None = None
    fill: str|Color|None = None
    tabindex: str|None = None
    title: str|ET.Element|None = None
    stroke_linejoin: str|None = None
    stroke_width: str|None = None

class DictList[T](list[T|None]):
    __slots__ = ()
    def __getitem__(self, idx: int|slice, /) -> T|None|list[T|None]:
        # enable slice support
        if isinstance(idx, int):
            if idx > len(self):
                return None
        return super().__getitem__(idx)
    def __setitem__(self, idx: int|slice, value: T|None, /) -> None:
        # enable slice setting to work even if the start of the slice is higher than current length
        if isinstance(idx, int):
            diff = idx - len(self)
            if diff >= 0:
                self.extend([None]*(diff+1))
        return super().__setitem__(idx, value) # type: ignore

@dataclass
class _Scrapped:
    paths: dict[str, _Path]
    seats: Sequence[_Path|None]

    def get_seats_by_color(self) -> dict[Color, list[int]]:
        """
        Renverra une clé de None pour les sièges existants mais non-attribués
        (dont potentiellement le siège en hémicycle de la présidence)
        """
        rv = defaultdict(list)
        for i, seat in enumerate(self.seats):
            if seat is not None:
                rv[seat.fill].append(i)
        rv.default_factory = None
        return rv

def scrape_svg(file: TextIOBase|str) -> _Scrapped:
    if not isinstance(file, str):
        with file as f:
            return scrape_svg(f.read())

    tree = ET.fromstring(file)

    for a in tuple(tree.findall(".//{*}a")):
        if not a.attrib.get("href", "www"):
            del a.attrib["href"]

        # retirer ? le tabindex à -1 désactive l'accès par tab,
        # mais c'est sans objet pour des éléments qui ne sont pas focusables par défaut
        # comme par ex les path, ou les a sans href
        if tabindex := a.attrib.pop("tabindex", None):
            for child in a:
                if child.tag.rpartition("}")[2] != "title":
                    child.attrib["tabindex"] = tabindex

        if a.attrib:
            warnings.warn(f"There are <a> attribs remaining : {', '.join(a.attrib)}")

        if (title := a.find("{*}title")) is not None:
            a.remove(title)
            for child in a:
                child.append(title)

    paths = {}
    seats = DictList()

    for path in tree.findall(".//{*}path"):
        pattrib = path.attrib.copy()

        transform = pattrib.pop("transform", None)
        if isinstance(transform, str) and (m := re.fullmatch(r"matrix *\( *([\d\.]+), *([\d\.]+), *([\d\.]+), *([\d\.]+), *([\d\.]+), *([\d\.]+), *\) *", transform)):
            a, b, c, d, e, f = map(float, m.groups())
            if a == d and not any((b, c, e, f)):
                transform = f"scale({a})"

        clazz = pattrib.pop("class", None)

        style_str = pattrib.pop("style", "")
        style_dict: dict[str, str|Color] = {(part := entry.partition(":"))[0].strip() : part[2].strip() for entry in style_str.split(";") if entry}

        for d in (pattrib, style_dict):
            for k, v in d.items():
                if isinstance(v, str):
                    if m := re.fullmatch(r"rgb *\( *([^\s,]+) *(?:\s|,) *([^\s,]+) *(?:\s|,) *([^\s,]+) *(?:\s|,|/)? *([^\s,]*) *\)", v.strip()):
                        r, g, b, a = m.groups()
                        if not a:
                            a = "255"
                        *rgba, = r, g, b, a
                        def convert_value(c):
                            if m := re.fullmatch(r"([\d\.]+)%", c):
                                c = round(float(m.group(1).lstrip("0")) / 100 * 255)
                            elif m := re.fullmatch(r"[\d\.]+", c):
                                c = round(float(c.lstrip("0")))
                            else:
                                raise ValueError(f"Value not recognized: {c!r}")
                            return c
                        d[k] = Color(*map(convert_value, rgba)) # type: ignore
                    elif m := re.fullmatch(r"#([\da-fA-F]{3,8})", v.strip()):
                        c = m.group()
                        if len(c) in (4, 5, 7, 9):
                            d[k] = Color.from_hex(c) # type: ignore

        for k in tuple(pattrib):
            if "-" in k:
                pattrib[k.replace("-", "_")] = pattrib.pop(k)

        id_ = pattrib.pop("id", None)

        if (title := path.find("{*}title")) is not None:
            path.remove(title)

        tabindex = pattrib.pop("tabindex", None)

        fill = pattrib.pop("fill", None)
        if not fill:
            fill = style_dict.pop("fill", None)

        path_kwargs = {k: pattrib.pop(k, None) for k in ("stroke", "stroke_linejoin", "stroke_width")}
        path_object = _Path(
            d=pattrib.pop("d"),
            transform=transform,
            clazz=clazz,
            id=id_,
            style=(style_dict or None),
            tabindex=tabindex,
            title=title,
            fill=fill,
            **path_kwargs
        )

        if id_ and (m := re.fullmatch(r"p(\d+)", id_)):
            seats[int(m.group(1))] = path_object

        identifier: str
        if id_:
            identifier = id_
        elif clazz:
            identifier = clazz
        elif (title is not None) and ((titext := title.text) is not None):
            identifier = titext
        # hardcodé
        elif tabindex:
            identifier = "architecture interne"
        else:
            identifier = "perchoir"

        if identifier in paths:
            warnings.warn(f"Identifier {identifier!r} misidentified or duplicated : {path_object, paths[identifier]}")
        paths[identifier] = path_object

        if pattrib:
            warnings.warn(f"There are <path> attribs remaining : {', '.join(pattrib)}")
        if path[:]:
            warnings.warn(f"There are <path> children remaining : {', '.join(map(str, path))}")

    return _Scrapped(paths=paths, seats=seats)

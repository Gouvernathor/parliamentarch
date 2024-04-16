from collections import defaultdict
from collections.abc import Iterable, Mapping
import dataclasses
from io import TextIOBase
import re
from typing import Self
import warnings
import xml.etree.ElementTree as ET


@dataclasses.dataclass(frozen=True)
class Color:
# class Color(NamedTuple):
    # namedtuple cannot be json-serialized other than as a json array
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

@dataclasses.dataclass
class Scraped_Path:
    d: str
    transform: str|None = None
    clazz: str|None = None
    id: str|None = None
    style: str|Mapping[str, str|Color]|None = None
    stroke: str|Color|None = None
    fill: str|Color|None = None
    tabindex: str|None = None
    title: str|ET.Element|None = None
    stroke_linejoin: str|None = None
    stroke_width: str|None = None

@dataclasses.dataclass
class Scraped:
    svg_attribs: dict[str, str]
    paths: Mapping[str, Scraped_Path]

    @staticmethod
    def pop_seats(paths: dict[str, Scraped_Path], pop: bool, yield_nones: bool):
        """
        Pops the seats off from the path dict *passed* to it,
        not the paths dict of the instance it's called on (since this is a static method)
        """
        mx = max(int(m.group(1)) for key in paths if (m := re.fullmatch(r"p(\d+)", key))) + 1
        if pop:
            method = paths.pop
        else:
            method = paths.get
        nones = 0
        for i in range(mx):
            key = f"p{i}"
            val = method(key, None)
            if val is None:
                nones += 1
            else:
                if yield_nones:
                    yield from iter((None,)*nones)
                nones = 0
                yield val

    # seats: Sequence[Scraped_Path|None]
    @property
    def seats(self) -> Iterable[Scraped_Path|None]:
        # turn into cachedproperty if made frozen
        return self.pop_seats(dict(self.paths), pop=False, yield_nones=True)

    def get_seats_by_color(self) -> Mapping[Color, list[int]]:
        """
        Renverra une clé de None pour les sièges existants mais non-attribués
        (dont potentiellement le siège en hémicycle de la présidence)
        Maybe deprecated.
        """
        rv = defaultdict(list)
        for i, seat in enumerate(self.seats):
            if seat is not None:
                rv[seat.fill].append(i)
        rv.default_factory = None
        return rv

def scrape_svg(file: TextIOBase|str) -> Scraped:
    # there is one circle in the svg, which is intentionally not scraped
    # TODO: store the circle's coordinates (discard the radius), maybe store its color
    # store the SVG params (class size params...)
    # recalculate the viewBox's x (maybe not here) from the circle's x
    if not isinstance(file, str):
        with file as f:
            return scrape_svg(f.read())

    tree = ET.fromstring(file)

    svg_attribs = tree.attrib.copy()

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

    for path in tree.findall(".//{*}path"):
        pattrib = path.attrib.copy()

        transform = pattrib.pop("transform", None)
        if isinstance(transform, str) and (m := re.fullmatch(r"matrix *\( *([\d\.]+), *([\d\.]+) *, *([\d\.]+) *, *([\d\.]+) *, *([\d\.]+) *, *([\d\.]+) *\) *", transform)):
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
            if title.text and (not title.attrib) and (not title[:]):
                title = title.text
            else:
                warnings.warn("A title element has attribs or doesn't contain text")

        tabindex = pattrib.pop("tabindex", None)

        fill = pattrib.pop("fill", None)
        if not fill:
            fill = style_dict.pop("fill", None)

        path_kwargs = {k: pattrib.pop(k, None) for k in ("stroke", "stroke_linejoin", "stroke_width")}
        path_object = Scraped_Path(
            d=pattrib.pop("d"),
            transform=transform,
            clazz=clazz,
            id=id_,
            style=(style_dict or None),
            fill=fill,
            tabindex=tabindex,
            title=title,
            **path_kwargs
        )

        identifier: str
        if id_:
            identifier = id_
        elif clazz:
            identifier = clazz
        elif isinstance(title, str):
            identifier = title
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

    rv = Scraped(svg_attribs=svg_attribs, paths=paths)
    return rv

# TODO: save the permanent data, excluding the seat colors, to a committed json file

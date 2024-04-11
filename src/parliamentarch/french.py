from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
import dataclasses
from functools import partial
from io import TextIOBase
import json
import re
from typing import Any, Self
import warnings
import xml.etree.ElementTree as ET

# class Color(NamedTuple):
@dataclasses.dataclass(frozen=True)
class Color:
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
class _Path:
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
class _Scraped:
    paths: Mapping[str, _Path]

    # seats: Sequence[_Path|None]
    @property
    def seats(self) -> Iterable[_Path|None]:
        # turn into cachedproperty if made frozen
        mx = max(int(m.group(1)) for key in self.paths if (m := re.fullmatch(r"p(\d+)", key))) + 1
        nones = 0
        for i in range(mx):
            key = f"p{i}"
            val = self.paths.get(key, None)
            if val is None:
                nones += 1
            else:
                yield from iter((None,)*nones)
                nones = 0
                yield val

    def get_seats_by_color(self) -> Mapping[Color, list[int]]:
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

@dataclasses.dataclass
class _Organized[G]:
    structural_paths: dict[str, _Path]
    grouped_seats: dict[G, list[_Path]]
    group_colors: dict[G, Color|str]

def scrape_svg(file: TextIOBase|str) -> _Scraped:
    # there is one circle in the svg, which is intentionally not scraped
    # TODO: store the circle's coordinates (discard the radius), maybe store its color
    # store the SVG params (class size params...)
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
        path_object = _Path(
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

    rv = _Scraped(paths=paths)
    return rv


def json_serializer(o: object) -> Any:
    """
    To be passed as the `default` parameter to `json.dump` or `json.dumps`.
    """
    if isinstance(o, Color):
        return str(o)
    if dataclasses.is_dataclass(o) and not isinstance(o, type):
        # return dataclasses.asdict(o) # recursive, bad
        return {f.name: getattr(o, f.name) for f in dataclasses.fields(o)}
    if isinstance(o, ET.Element) and (o.tag.rpartition("}")[2] == "title") and (not o.attrib) and (not o[:]) and o.text:
        return o.text
    raise TypeError(f"Cannot serialize {o!r}.")

def json_object_hook(d: dict[str, Any]) -> Any:
    """
    To be passed as the `object_hook` parameter to `json.load` or `json.loads`.
    """
    for typ in (_Organized, _Path, _Scraped, Color):
        if d.keys() == {f.name for f in dataclasses.fields(typ)}:
            return typ(**d)
    return d

# parse_float=str, parse_int=str
json_loads = partial(json.loads, object_hook=json_object_hook)
json_load = partial(json.load, object_hook=json_object_hook)
json_dumps = partial(json.dumps, default=json_serializer)
json_dump = partial(json.dump, default=json_serializer)


def get_svg_tree(organized_data: _Organized, *,
        seats_blacklist: Sequence[int] = (),
        seats_whitelist: Sequence[int] = (),
        **toggles: bool) -> ET.ElementTree:

    @dataclasses.dataclass
    class G:
        attrib: dict[str, str]
        children: Sequence["G|_Path"]
        @property
        def tag(self) -> str:
            if "href" in self.attrib:
                return "a"
            return "g"

    def to_ET(c: G|_Path) -> ET.Element:
        if isinstance(c, _Path):
            attrib = {k.replace("_", "-"): v for k, v in dataclasses.asdict(c).items() if v is not None}

            title = attrib.pop("title", None)
            if title:
                if isinstance(title, ET.Element):
                    children = (title,)
                elif isinstance(title, str):
                    title_elem = ET.Element("title")
                    title_elem.text = title
                    children = (title_elem,)
            else:
                children = ()

            tag = "path"

        else:
            attrib = c.attrib

            raw_children = list(c.children)
            for child in c.children:
                if isinstance(child, G) and not child.attrib:
                    raw_children.remove(child)
                    raw_children.extend(child.children)

            children = map(to_ET, raw_children)

            tag = c.tag
            if tag == "g" and attrib.get("tabindex", "0") == "-1":
                del attrib["tabindex"]

        e = ET.Element(tag, attrib)
        e.extend(children)
        return e

    svg_direct_content: list[G|_Path] = []

    for name, path in organized_data.structural_paths.items():
        if toggles.pop(name, True):
            svg_direct_content.append(path)

    # TODO: check if the clazz attribute should be censored as well
    PATH_FIELDS_TO_GROUP = frozenset(f.name for f in dataclasses.fields(_Path)) - {"d", "id"}
    remaining: dict[tuple[int, ...], frozenset[str]] = {}
    # make a g for each color (with at least a fill attribute), and put the seats inside
    for i, (gid, pathlist) in enumerate(organized_data.grouped_seats.items(), start=len(svg_direct_content)):
        # TODO: filter the seats here
        g = G(dict(fill=str(organized_data.group_colors[gid])), pathlist.copy())
        remaining[(i,)] = PATH_FIELDS_TO_GROUP
        svg_direct_content.append(g)

    def get_index(i, *idx:int) -> G:
        e = svg_direct_content[i]
        for i in idx:
            e = e.children[i]
        return e

    while remaining:
        indices, fields = next(iter(remaining.items()))
        if not fields:
            del remaining[indices]
            continue

        g = get_index(*indices)
        per_field_value: dict[str, dict[str, list[_Path]]] = {}
        for field in fields:
            this_fields_values = per_field_value[field] = defaultdict(list)
            for child in g.children:
                this_fields_values[getattr(child, field)].append(child) # type: ignore

            if len(this_fields_values) == 1:
                field_value = next(iter(this_fields_values))
                if field_value is not None:
                    g.attrib[field] = field_value
                    for child in g.children:
                        setattr(child, field, None)
                del per_field_value[field]
                fields -= {field}

        if not per_field_value:
            del remaining[indices]
            continue

        # field with minimal number of different values
        minfield = min(per_field_value, key=lambda f:len(per_field_value[f]))
        # TODO: maybe take all the fields with that exact list
        # not necessary but may be quicker

        new_gs = []
        for value, pathlist in per_field_value[minfield].items():
            if value is None:
                new_gs.extend(pathlist)
            elif (minfield != "href") and (len(pathlist) == 1):
                new_gs.append(pathlist[0])
            else:
                new_gs.append(G({minfield: value}, pathlist))
        g.children = new_gs

        del remaining[indices]
        fields -= {minfield}
        if fields:
            for i, sub_g in enumerate(new_gs):
                if isinstance(sub_g, G):
                    remaining[indices+(i,)] = fields

    # a final pass for the all-encompassing gs, putting those with common attribs in encompassing gs
    # just once for attribs common to all
    # (meant for the transform field)
    for g in svg_direct_content:
        if isinstance(g, G):
            main_g_attribs: dict[str, str] = g.attrib.copy()
            break
    for elem in svg_direct_content:
        if isinstance(elem, G):
            for k, v in main_g_attribs.items():
                if elem.attrib.get(k, not v) != v:
                    del main_g_attribs[k]
        else:
            for k, v in main_g_attribs.items():
                if getattr(elem, k, not v) != v:
                    del main_g_attribs[k]
    if main_g_attribs:
        for g in tuple(svg_direct_content):
            if isinstance(g, G):
                for k in main_g_attribs:
                    del g.attrib[k]
                if not g.attrib:
                    i = svg_direct_content.index(g)
                    svg_direct_content[i:i+1] = g.children
            else:
                for k in main_g_attribs:
                    setattr(g, k, None)
        svg_direct_content = [G(main_g_attribs, svg_direct_content)]

    svg = ET.Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "xmlns:xlink": "http://www.w3.org/1999/xlink",
        "version": "1.1",
    })
    # manage size and other properties

    svg.extend(map(to_ET, svg_direct_content))

    return ET.ElementTree(svg)

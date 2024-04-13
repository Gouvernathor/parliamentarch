from collections import defaultdict
from collections.abc import Collection, Iterable, Mapping, Sequence
import dataclasses
from functools import partial
from io import TextIOBase
import json
import re
from typing import Any, ClassVar, Self
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

    @staticmethod
    def pop_seats(paths: dict[str, _Path], pop: bool, yield_nones: bool):
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

    # seats: Sequence[_Path|None]
    @property
    def seats(self) -> Iterable[_Path|None]:
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


@dataclasses.dataclass
class _Organized[G]:
    structural_paths: dict[str, _Path]
    seats: Mapping[int, _Path]
    # only the following two should be mutated, generally, and only by values
    grouped_seats: dict[G, list[int]]
    # TODO: turn into group_data and allow more than just color (href too)
    group_colors: dict[G, Color|str|None]

    @staticmethod
    def from_scraped(scraped: _Scraped, group_ids: Iterable[G]|None = None) -> "_Organized[G]":
        if group_ids is None:
            group_ids = range(len(scraped.paths)) # type: ignore

        group_ids_it = iter(group_ids) # type: ignore

        paths = dict(scraped.paths)
        seats_it: Iterable[_Path] = _Scraped.pop_seats(paths, pop=True, yield_nones=True) # type: ignore
        seats_dict = {}

        grouped_seats: dict[G, list[int]] = defaultdict(list)
        color_groups: dict[Color|str|None, G] = {}
        for i, seat in enumerate(seats_it):
            if seat is None:
                continue

            color = seat.fill
            if color is not None:
                color = str(color)

            seat = dataclasses.replace(seat, fill=None)
            seats_dict[i] = seat

            group = color_groups.get(color, None)
            if group is None:
                group = next(group_ids_it)
                color_groups[color] = group

            grouped_seats[group].append(i)

        grouped_seats.default_factory = None
        return _Organized(paths, seats_dict, grouped_seats, {g: c for c, g in color_groups.items()})

# pseudo-svg nodes
@dataclasses.dataclass
class Path: # TODO: rename this shit
    attrib: dict[str, str]
    tag: ClassVar[str] = "path"

def Path_from_other_Path(p: _Path) -> Path:
    return Path({field.name: getattr(p, field.name) for field in dataclasses.fields(p)})

@dataclasses.dataclass
class G(Path):
    children: list[Path] = dataclasses.field(default_factory=list)
    @property
    def tag(self) -> str:
        if "href" in self.attrib:
            return "a"
        return "g"

@dataclasses.dataclass
class SVG(G):
    attrib: dict[str, str] = dataclasses.field(default_factory={
        "xmlns": "http://www.w3.org/2000/svg",
        "xmlns:xlink": "http://www.w3.org/1999/xlink",
        "version": "1.1",
    }.copy) # TODO: get this from the scrape
    tag: ClassVar[str] = "svg"

def get_svg_pseudo_xml(organized_data: _Organized, *,
        seats_blacklist: Collection[int] = (),
        seats_whitelist: Collection[int] = (),
        include_none_seats: bool = False,
        error_on_extra_toggles: bool = True,
        **toggles: bool) -> SVG:
    """
    include_none_seats being False (the default) means not writing
    the seats whose color is None.
    That parameter overrides such a seat being present in the whitelist
    or being absent from the blacklist.
    toggles only applies to structural paths, not to seats.
    """

    seats_blacklist = frozenset(seats_blacklist)
    seats_whitelist = frozenset(seats_whitelist)
    if seats_whitelist:
        if seats_blacklist:
            raise TypeError("Cannot pass whitelist and blacklist at the same time")
    else:
        seats_whitelist = organized_data.seats.keys() - seats_blacklist

    svg = SVG()
    svg_direct_content = svg.children # TODO: rename to svg_children or sth

    for name, path in organized_data.structural_paths.items():
        if toggles.pop(name, True):
            svg_direct_content.append(Path_from_other_Path(path))
    if error_on_extra_toggles and toggles:
        raise ValueError("The following toggles were not found among the structural paths : " + ", ".join(toggles))

    # make a g for each color (with at least a fill attribute), and put the seats inside
    for gid, seat_nb_list in organized_data.grouped_seats.items():
        g = G({}, [Path_from_other_Path(organized_data.seats[i]) for i in seat_nb_list if i in seats_whitelist])

        color = organized_data.group_colors[gid]
        if color is not None:
            g.attrib["fill"] = str(color)
        elif not include_none_seats:
            continue

        svg_direct_content.append(g)

    return svg

def get_svg_tree(
        svg,
        indent: str|None = "    ",
        ) -> ET.ElementTree:

    # TODO: check if the clazz attribute should be censored as well
    PATH_FIELDS_TO_GROUP = frozenset(f.name for f in dataclasses.fields(_Path)) - {"d", "id", "fill"}
    remaining: dict[tuple[int, ...], frozenset[str]] = {(): PATH_FIELDS_TO_GROUP}

    def get_at_index(*idx:int) -> G:
        e: G = svg
        for i in idx:
            e = e.children[i] # type: ignore
        return e

    # TODO: check this for None values (should be fine but check again)
    while remaining:
        indices, fields = remaining.popitem()
        if not fields:
            continue

        g = get_at_index(*indices)

        for child in g.children:
            if isinstance(child, G) and not child.attrib:
                i = g.children.index(child)
                g.children[i:i+1] = child.children

        per_field_value: dict[str, dict[str, list[_Path]]] = {}
        for field in fields:
            this_fields_values = per_field_value[field] = defaultdict(list)
            for child in g.children:
                this_fields_values[child.attrib.get(field, None)].append(child) # type: ignore

            if len(this_fields_values) == 1:
                field_value = next(iter(this_fields_values))
                if field_value is not None:
                    g.attrib[field] = field_value
                    for child in g.children:
                        child.attrib.pop(field, None)
                del per_field_value[field]
                fields -= {field}

        if not per_field_value:
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
                new_gs.append(G({minfield: value}, pathlist)) # type: ignore
        g.children = new_gs

        fields -= {minfield}
        if fields:
            remaining[indices] = fields
            for i, sub_g in enumerate(new_gs):
                if isinstance(sub_g, G):
                    remaining[indices+(i,)] = fields

    def to_ET(c: Path) -> ET.Element:
        def replace_fname(n):
            if n == "clazz":
                return "class"
            return n.replace("_", "-")

        def replace_color(o):
            if isinstance(o, Color):
                return str(o)
            return o

        attrib = {replace_fname(k): replace_color(v) for k, v in c.attrib.items() if v is not None}
        if None in attrib.values():
            warnings.warn(f"None value in attrib: {attrib}, build not done properly")

        if isinstance(c, G):
            raw_children = list(c.children)
            for child in c.children:
                if isinstance(child, G) and not child.attrib:
                    raw_children.remove(child)
                    raw_children.extend(child.children)

            children = map(to_ET, raw_children)
        else:
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

        tag = c.tag
        if tag == "g" and attrib.get("tabindex", "0") == "-1":
            del attrib["tabindex"]

        e = ET.Element(tag, attrib)
        e.extend(children)
        return e

    et = ET.ElementTree(to_ET(svg))
    if indent is not None:
        ET.indent(et, indent)
    return et

def main(in_fn, out_fn=None):
    with open(in_fn) as f:
        scraped = scrape_svg(f.read())
    organized = _Organized.from_scraped(scraped)
    pseudo_xml_svg = get_svg_pseudo_xml(organized, include_none_seats=True)
    tree = get_svg_tree(pseudo_xml_svg)

    if out_fn is not None:
        with open(out_fn, "w+") as f:
            tree.write(f, encoding="unicode", xml_declaration=False)

    return scraped, organized, pseudo_xml_svg, tree

if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 2:
        out_fn = None
        if len(sys.argv) >= 3:
            out_fn = sys.argv[2]
        scraped, organized, pseudo_xml_svg, tree = main(sys.argv[1], out_fn)

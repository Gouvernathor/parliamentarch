from collections import defaultdict
from collections.abc import Collection
import dataclasses
from typing import ClassVar

from .organize import Organized
from .scrape import Scraped_Path


# pseudo-svg nodes
@dataclasses.dataclass
class Path:
    attrib: dict[str, str]
    tag: ClassVar[str] = "path"

def Path_from_other_Path(p: Scraped_Path) -> Path:
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
    attrib: dict[str, str] = dataclasses.field(default_factory=dict)
    tag: ClassVar[str] = "svg"

    NAMESPACE_ATTRIB: ClassVar[dict[str, str]] = {
        "xmlns": "http://www.w3.org/2000/svg",
        "xmlns:xlink": "http://www.w3.org/1999/xlink",
    }

def get_svg_pseudo_xml(organized_data: Organized, *,
        seats_blacklist: Collection[int] = (),
        seats_whitelist: Collection[int] = (),
        include_none_seats: bool = False,
        error_on_extra_toggles: bool = True,
        reduce: bool = False,
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

    svg = SVG(organized_data.svg_attribs)
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

    if reduce:
        reduce_pseudo_xml_svg(svg)

    return svg

# TODO: check if the clazz attribute should be censored as well
PATH_FIELDS_TO_GROUP = frozenset(f.name for f in dataclasses.fields(Scraped_Path)) - {"d", "id"}

def reduce_pseudo_xml_svg(svg: SVG,) -> None:
    remaining: dict[tuple[int, ...], frozenset[str]] = {(): PATH_FIELDS_TO_GROUP}

    def get_at_index(*idx:int) -> G:
        e: G = svg
        for i in idx:
            e = e.children[i] # type: ignore
        return e

    while remaining:
        indices, fields = remaining.popitem()
        if not fields:
            continue

        g = get_at_index(*indices)

        for child in g.children:
            if isinstance(child, G) and not child.attrib:
                i = g.children.index(child)
                g.children[i:i+1] = child.children

        per_field_value: dict[str, dict[str|None, list[Path]]] = {}
        for field in fields:
            this_fields_values = per_field_value[field] = defaultdict(list)
            for child in g.children:
                this_fields_values[child.attrib.get(field, None)].append(child)

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

        # field with minimal number of different values (and first alphabetical for consistency)
        minfield = min(per_field_value, key=lambda f:(len(per_field_value[f]), f))

        new_children = []
        for value, childlist in per_field_value[minfield].items():
            if value is None:
                new_children.extend(childlist)
            elif (minfield != "href") and (len(childlist) == 1):
                new_children.append(childlist[0])
            else:
                for path in childlist:
                    path.attrib.pop(minfield, None)
                new_children.append(G({minfield: value}, childlist))
        g.children = new_children

        fields -= {minfield}
        if fields:
            remaining[indices] = fields
            for i, child in enumerate(new_children):
                if isinstance(child, G):
                    remaining[indices+(i,)] = fields

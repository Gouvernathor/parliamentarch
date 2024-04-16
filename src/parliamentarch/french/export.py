import re
import warnings
import xml.etree.ElementTree as ET

from .pseudo_xml import G, SVG, Path
from .scrape import Color


def get_svg_tree(svg: SVG, *,
        indent: str|None = "    ",
        pop_main_transform: bool = True,
        ) -> ET.ElementTree:

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
        if isinstance(c, SVG):
            attrib = SVG.NAMESPACE_ATTRIB | attrib

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

    svg_element = to_ET(svg)
    if pop_main_transform:
        transform = svg_element.attrib.get("transform", None)
        if transform is not None:
            if m := re.fullmatch(r"scale\(([\d\.]+)\)", transform):
                scale = float(m.group(1))
                del svg_element.attrib["transform"]

                viewBox = svg_element.attrib.get("viewBox", None)
                if viewBox is not None:
                    x, y, w, h = map(float, viewBox.split())
                    svg_element.attrib["viewBox"] = f"{x/scale} {y/scale} {w/scale} {h/scale}"

                #TODO: do the same for height and width, but not if they're percentages
    et = ET.ElementTree(svg_element)
    if indent is not None:
        ET.indent(et, indent)
    return et

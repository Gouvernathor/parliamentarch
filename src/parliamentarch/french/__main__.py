from .scrape import scrape_svg
from .organize import _Organized
from .pseudo_xml import get_svg_pseudo_xml
from .export import get_svg_tree


def main(in_fn, out_fn=None):
    with open(in_fn) as f:
        scraped = scrape_svg(f.read())
    organized = _Organized.from_scraped(scraped)
    pseudo_xml_svg = get_svg_pseudo_xml(organized, include_none_seats=True, reduce=True)
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

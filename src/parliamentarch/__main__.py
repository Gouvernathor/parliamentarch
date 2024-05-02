import argparse
import json
import sys

from . import get_svg_from_attribution, SeatData

def main():
    # return None (or nothing) is good
    # return a non-zero integer or an error message for an error

    parser = argparse.ArgumentParser(
        prog="ParliamentArch",
        description="Generate arch-like parliament diagrams.",
    )

    # input filename (json)
    parser.add_argument("input",
        type=argparse.FileType("rb"),
        help="""A readable JSON file containing the named parameters to use when
        creating the diagram. The parameters are as the get_svg_from_attribution
        function takes them, except that the "attrib" parameter should be a
        sequence of dicts (JSON objects) with key/value pairs being parameters
        to SeatData, and the optional nseats (defaulting to 1) being the number
        of seats of that party.""",
    )
    # each possible parameter separately ?
    # TODO do this programmatically using inspect
    # only require input if not all required are passed specifically

    # output filename
    parser.add_argument("--output",
        type=argparse.FileType("w+"), # TODO check : write mode, clobber if exists, create if not
        help="""The file in which to write the SVG diagram. If not passed, the
        SVG code will be printed in the standard output.""",
        # TODO: make sure that this argument is optional and defaults to None
    )
    # whether to print the resulting file's content (when the output file is not given)
    parser.add_argument("-p", "--print",
        action="store_true",
        help="""Pass this to print the SVG code in the standard output even when
        an output file is passed.""",
    )
    # if both are given, do both
    # if none are given, only print


    args = parser.parse_args()

    with args.input as f:
        kwparams = json.load(f)
    kwparams["attrib"] = {SeatData(**d): n for d in kwparams["attrib"] if (n := d.pop("nseats", 1))}

    result = get_svg_from_attribution(**kwparams)

    file_output = args.output is not None
    if file_output:
        with args.output as f:
            f.write(result)
    if args.print or not file_output:
        print(result)


if __name__ == "__main__":
    sys.exit(main())

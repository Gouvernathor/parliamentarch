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
        help="""A readable JSON file containing one object whose members are the
        named parameters to use when creating the diagram. The parameters are as
        the get_svg_from_attribution function takes them, except for the
        "attrib" parameter. It should instead be a sequence of JSON objects with
        members being parameters to SeatData, and an optional "nseats" member
        (defaulting to 1) being the number of seats for that party.""",
    )
    # each possible parameter separately ?
    # TODO do this programmatically using inspect
    # only require input if not all required are passed specifically

    # output filename
    parser.add_argument("-o", "--output",
        type=argparse.FileType("w+"), # TODO check : write mode, clobber if exists, create if not
        help="""The file in which to write the SVG diagram. If not passed, the
        SVG code will be printed in the standard output.""",
        # TODO: make sure that this argument is optional and defaults to None
    )
    # whether to print the resulting file's content (regardless of the output file being given)
    parser.add_argument("-p", "--print",
        action="store_true",
        help="""Pass this to print the SVG code in the standard output even when
        an output file is passed.""",
    )
    # if both are given, do both
    # if none are given, raise


    args = parser.parse_args()

    if not (args.output or args.print):
        parser.error("At least one of --output or --print must be passed.")

    with args.input as f:
        kwparams = json.load(f)
    kwparams["attrib"] = {SeatData(**d): n for d in kwparams["attrib"] if (n := d.pop("nseats", 1))}

    result = get_svg_from_attribution(**kwparams)

    if args.output is not None:
        with args.output as f:
            f.write(result)
    if args.print:
        print(result)


if __name__ == "__main__":
    sys.exit(main())

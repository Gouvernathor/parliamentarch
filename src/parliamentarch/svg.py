from collections.abc import Iterable
from functools import cached_property
from io import TextIOBase
import re

from ._util import Color, UnPicklable, get_from_write

__all__ = ("SeatData", "dispatch_seats", "write_svg", "write_grouped_svg", "get_svg", "get_grouped_svg")

class SeatData(UnPicklable):
    """Put this somewhere else"""
    id: int|None = None
    data: str
    @cached_property
    def sanitized_data(self) -> str:
        return re.sub(r"[^a-zA-Z0-9_-]", "-", self.data)
    color: Color|str
    border_size: float
    border_color: Color|str

    def __init__(self,
            data: str,
            color,
            border_size: float = 0,
            border_color="#000",
            ) -> None:

        def accepted_color(c):
            try:
                return Color.from_any(c)
            except ValueError:
                if not isinstance(c, str):
                    raise
                return c

        self.data = data
        self.color = accepted_color(color)
        self.border_size = border_size
        self.border_color = accepted_color(border_color)

def dispatch_seats[S](
        group_seats: dict[SeatData, int],
        seats: Iterable[S],
        ) -> dict[SeatData, list[S]]:
    """
    From a dict of groups associating the groups in a given order
    to the number of seats each group has,
    and an iterable of seats in a given order,
    returns a dict associating each group to a list of seats.
    (Typically S is a tuple of x/y coordinates.)
    The length of the iterable should be the sum of the values in the dict.
    Typically the groups are ordered from the left to the right,
    and the seats are ordered from the left to the right.
    """
    its = iter(seats)
    rv = {}
    for group, nseats in group_seats.items():
        rv[group] = [next(its) for _ in range(nseats)]
    return rv


def write_svg(
        file: TextIOBase,
        seat_centers: dict[tuple[float, float], SeatData],
        *args, **kwargs,
        ) -> None:
    seat_centers_by_group = {}
    for seat, group in seat_centers.items():
        seat_centers_by_group.setdefault(group, []).append(seat)
    write_grouped_svg(file, seat_centers_by_group, *args, **kwargs)

def write_grouped_svg(
        file: TextIOBase,
        seat_centers_by_group: dict[SeatData, list[tuple[float, float]]],
        seat_actual_radius: float, *,
        canvas_size: float = 175,
        margins: float|tuple[float, float]|tuple[float, float, float, float] = 5.,
        write_number_of_seats: bool = True,
        font_size_factor: float = 36/175,
        ) -> None:
    """
    The margins is either a single value for all four sides,
    or a (horizontal, vertical) tuple,
    or a (left, top, right, bottom) tuple.

    canvas_size is the height and half of the width
    of the canvas 2:1 rectangle to which to add the margins.
    """

    if isinstance(margins, (int, float)):
        margins = (margins, margins, margins, margins)
    elif len(margins) == 2:
        margins = margins + margins
    left_margin, top_margin, right_margin, bottom_margin = margins

    _write_svg_header(file,
        width=left_margin+2*canvas_size+right_margin,
        height=top_margin+canvas_size+bottom_margin)
    if write_number_of_seats:
        font_size = round(font_size_factor * canvas_size)
        _write_svg_number_of_seats(file, sum(map(len, seat_centers_by_group.values())),
            x=left_margin+canvas_size, y=top_margin+canvas_size, font_size=font_size)
    _write_grouped_svg_seats(file, seat_centers_by_group, seat_actual_radius,
        canvas_size=canvas_size, left_margin=left_margin, top_margin=top_margin)
    _write_svg_footer(file)

def _write_svg_header(file: TextIOBase, width: float, height: float) -> None:
    file.write(f"""\
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns:svg="http://www.w3.org/2000/svg"
     xmlns="http://www.w3.org/2000/svg" version="1.1"
     width="{width}" height="{height}">
    <!-- Created with parliamentarch (https://github.com/Gouvernathor/parliamentarch/) -->""")

def _write_svg_number_of_seats(
        file: TextIOBase,
        nseats: int,
        x: float, y: float,
        font_size: int,
        ) -> None:
    file.write(f"""
    <text x="{x}" y="{y}"
          style="font-size:{font_size}px;font-weight:bold;text-align:center;text-anchor:middle;font-family:sans-serif">{nseats}</text>""")

def _write_grouped_svg_seats(
        file: TextIOBase,
        seat_centers_by_group: dict[SeatData, list[tuple[float, float]]],
        seat_actual_radius: float,
        canvas_size: float,
        left_margin: float,
        top_margin: float,
        ) -> None:

    group_number_fallback = 0
    for group, seat_centers in seat_centers_by_group.items():
        group_number = group.id
        if group_number is None:
            group_number = group_number_fallback
            group_number_fallback += 1

        block_id = f"{group_number}-{group.sanitized_data}"

        group_border_width = group.border_size * seat_actual_radius * canvas_size

        group_color = group.color
        if isinstance(group_color, Color):
            group_color = group_color.hexcode
        group_border_color = group.border_color
        if isinstance(group_border_color, Color):
            group_border_color = group_border_color.hexcode

        file.write(f"""
    <g style="fill:{group_color}; stroke-width:{group_border_width:.2f}; stroke:{group_border_color}"
       id="{block_id}">
        <title>{group.data}</title>""")

        for x, y in seat_centers:
            actual_x = left_margin + canvas_size * x
            actual_y = top_margin + canvas_size * (1 - y)
            actual_radius = seat_actual_radius * canvas_size - group_border_width/2
            file.write(f"""
        <circle cx="{actual_x:.2f}" cy="{actual_y:.2f}" r="{actual_radius:.2f}"/>""")

        file.write("""
    </g>""")

def _write_svg_footer(file: TextIOBase) -> None:
    file.write("""
</svg>
""")


get_svg = get_from_write(write_svg)
get_grouped_svg = get_from_write(write_grouped_svg)

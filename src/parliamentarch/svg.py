from collections.abc import Iterable
from functools import cached_property
from io import TextIOBase
import re
import warnings

from ._util import Color, UnPicklable, write_from_get

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
    If too few seats are passed, an exception is raised.
    If too many seats are passed, a warning is emitted.
    """
    its = iter(seats)
    rv = {}
    for group, nseats in group_seats.items():
        rv[group] = [next(its) for _ in range(nseats)]
    if tuple(its):
        warnings.warn("Too many seats were passed to dispatch_seats.")
    return rv


def get_svg(
        seat_centers: dict[tuple[float, float], SeatData],
        *args, **kwargs,
        ) -> str:
    seat_centers_by_group = {}
    for seat, group in seat_centers.items():
        seat_centers_by_group.setdefault(group, []).append(seat)
    return get_grouped_svg(seat_centers_by_group, *args, **kwargs)

def get_grouped_svg(
        seat_centers_by_group: dict[SeatData, list[tuple[float, float]]],
        seat_actual_radius: float, *,
        canvas_size: float = 175,
        margins: float|tuple[float, float]|tuple[float, float, float, float] = 5.,
        write_number_of_seats: bool = True,
        font_size_factor: float = 36/175,
        ) -> str:
    """
    The margins is either a single value for all four sides,
    or a (horizontal, vertical) tuple,
    or a (left, top, right, bottom) tuple.

    canvas_size is the height and half of the width
    of the canvas 2:1 rectangle to which to add the margins.
    """
    buffer = []

    if isinstance(margins, (int, float)):
        margins = (margins, margins, margins, margins)
    elif len(margins) == 2:
        margins = margins + margins
    left_margin, top_margin, right_margin, bottom_margin = margins

    _append_svg_header(buffer,
        width=left_margin+2*canvas_size+right_margin,
        height=top_margin+canvas_size+bottom_margin)
    if write_number_of_seats:
        font_size = round(font_size_factor * canvas_size)
        _append_svg_number_of_seats(buffer, sum(map(len, seat_centers_by_group.values())),
            x=left_margin+canvas_size, y=top_margin+(canvas_size*170/175), font_size=font_size)
    _append_grouped_svg_seats(buffer, seat_centers_by_group, seat_actual_radius,
        canvas_size=canvas_size, left_margin=left_margin, top_margin=top_margin)
    _append_svg_footer(buffer)

    return "".join(buffer)

def _append_svg_header(buffer: list[str], width: float, height: float) -> None:
    buffer.append(f"""\
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg xmlns:svg="http://www.w3.org/2000/svg"
     xmlns="http://www.w3.org/2000/svg" version="1.1"
     width="{width}" height="{height}">
    <!-- Created with parliamentarch (https://github.com/Gouvernathor/parliamentarch/) -->""")

def _append_svg_number_of_seats(
        buffer: list[str],
        nseats: int,
        x: float, y: float,
        font_size: int,
        ) -> None:
    buffer.append(f"""
    <text x="{x}" y="{y}"
          style="font-size:{font_size}px;font-weight:bold;text-align:center;text-anchor:middle;font-family:sans-serif">{nseats}</text>""")

def _append_grouped_svg_seats(
        buffer: list[str],
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

        buffer.append(f"""
    <g style="fill:{group_color}; stroke-width:{group_border_width:.2f}; stroke:{group_border_color}"
       id="{block_id}">
        <title>{group.data}</title>""")

        for x, y in seat_centers:
            actual_x = left_margin + canvas_size * x
            actual_y = top_margin + canvas_size * (1 - y)
            actual_radius = seat_actual_radius * canvas_size - group_border_width/2
            buffer.append(f"""
        <circle cx="{actual_x:.2f}" cy="{actual_y:.2f}" r="{actual_radius:.2f}"/>""")

        buffer.append("""
    </g>""")

def _append_svg_footer(buffer: list[str]) -> None:
    buffer.append("""
</svg>
""")


write_svg = write_from_get(get_svg)
write_grouped_svg = write_from_get(get_grouped_svg)

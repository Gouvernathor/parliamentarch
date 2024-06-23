from collections import Counter
from collections.abc import Iterable
from functools import cached_property
import math
import re
from typing import TypeVar
import warnings

from ._util import Color, UnPicklable, write_from_get

__all__ = ("SeatData", "dispatch_seats", "better_dispatch_seats", "write_svg", "write_grouped_svg", "get_svg", "get_grouped_svg")

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

S = TypeVar("S") # PY3.11 compat
def dispatch_seats(
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
    If too many seats are passed, the output will be incorrect and a warning is emitted.
    """
    its = iter(seats)
    rv = {}
    for group, nseats in group_seats.items():
        rv[group] = [next(its) for _ in range(nseats)]
    if tuple(its):
        warnings.warn("Too many seats were passed to dispatch_seats.")
    return rv

def bruteforce_better_dispatch_seats(
        group_seats: dict[SeatData, int],
        seats: dict[tuple[float, float], float],
        ) -> dict[SeatData, list[tuple[float, float]]]:
    """
    From a dict of groups associating the groups in a given order
    to the number of seats each group has,
    and an dict of x/y seat coordinates
    to the angle of each seat wrt the center of the half-annulus,
    returns a dict associating each group to a list of seats.
    The grouping minimizes the maximum distance between the seats in each group.
    The length of the iterable should be the sum of the values in the dict.
    Typically the groups are ordered from the left to the right,
    and the seats are ordered from the left to the right.
    If too few seats are passed, an exception is raised.
    If too many seats are passed...?
    """
    # put the seats (tuple[float, float]) in subgroups
    # such that the max distance (math.hypot(x1-x2, y1-y2)) between the seats of each subgroup is minimized
    # the number of seats in each subgroup is as group_seats indicates
    # when computing for each group the mean of the value of the seats in the seats dict, the values should be increasing

    # generate all possible SeatData sequences
    # such that the sequence length is len(seats)
    # and the number of times each number appears is the value of the corresponding group in group_seats
    nseats = len(seats)
    group_seats = Counter(group_seats)
    def generate_sequences(sequence: tuple[SeatData, ...] = ()):
        if len(sequence) >= nseats:
            yield sequence
            return
        localcounter = group_seats - Counter(sequence)
        for p in localcounter:
            yield from generate_sequences(sequence+(p,))

    def get_weight(attrib) -> float:
        return sum(max(math.hypot(seat1[0]-seat2[0], seat1[1]-seat2[1]) for seat1 in seatlist for seat2 in seatlist) for seatlist in attrib.values())

    def get_mean_angle(seat_list) -> float:
        return sum(seats[s] for s in seat_list) / len(seat_list)

    seats_sequence = tuple(seats)
    def get_attribution_from_sequence(sequence) -> dict[SeatData, list[tuple[float, float]]]:
        attribution = {sd: [] for sd in group_seats}
        for i, sd in enumerate(sequence):
            attribution[sd].append(seats_sequence[i])
        return attribution

    lstgs = list(group_seats)
    weight_per_sequence: dict[tuple[SeatData, ...]|None, float] = {None: math.inf}
    best_sequence = None
    for i, sequence in enumerate(generate_sequences()):
        assert Counter(sequence) == Counter(group_seats)

        attribution = get_attribution_from_sequence(sequence)

        # test if the order is correct
        if sorted(group_seats, key=lambda g: get_mean_angle(attribution[g])) == lstgs:
            if sequence in weight_per_sequence:
                raise ValueError("Duplicate sequence")
            weight = get_weight(attribution)
            weight_per_sequence[sequence] = weight
            if weight < weight_per_sequence[best_sequence]:
                best_sequence = sequence

        print(f"{len(weight_per_sequence)} good / {i} tested {hash(best_sequence)}", end="\r")
    print()

    return get_attribution_from_sequence(best_sequence)

better_dispatch_seats = bruteforce_better_dispatch_seats


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
    <g style="fill:{group_color}""")
        if group_border_width:
            buffer.append(f"; stroke-width:{group_border_width:.2f}; stroke:{group_border_color}")
        # the fourth quote on the next line is intentional
        buffer.append(f""""
       id="{block_id}">""")
        if group.data:
            buffer.append(f"""
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

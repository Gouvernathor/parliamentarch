from inspect import signature
from io import TextIOBase

from .geometry import get_seats_centers
from .svg import SeatData, dispatch_seats, write_grouped_svg
from ._util import filter_kwargs, get_from_write

__all__ = ("get_svg_from_attribution", "write_svg_from_attribution", "SeatData")

_GET_SEATS_CENTERS_PARAM_NAMES = {k for k, p in signature(get_seats_centers).parameters.items() if p.kind==p.KEYWORD_ONLY}
_WRITE_GROUPED_SVG_PARAM_NAMES = {k for k, p in signature(write_grouped_svg).parameters.items() if p.kind==p.KEYWORD_ONLY}

def write_svg_from_attribution(file: TextIOBase, attrib: dict[SeatData, int], **kwargs) -> None:
    nseats = sum(attrib.values())
    get_seats_centers_kwargs, write_grouped_svg_kwargs, kwargs = filter_kwargs(_GET_SEATS_CENTERS_PARAM_NAMES, _WRITE_GROUPED_SVG_PARAM_NAMES, **kwargs)

    if kwargs:
        raise TypeError("Unknown parameters : " + ", ".join(kwargs))

    results = get_seats_centers(nseats, **get_seats_centers_kwargs)
    seat_centers_by_group = dispatch_seats(attrib, sorted(results, key=results.__getitem__, reverse=True))
    write_grouped_svg(file, seat_centers_by_group, results.seat_actual_radius, **write_grouped_svg_kwargs)

get_svg_from_attribution = get_from_write(write_svg_from_attribution)

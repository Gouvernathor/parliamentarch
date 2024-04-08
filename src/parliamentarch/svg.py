from collections.abc import Container
from inspect import signature as _signature
from typing import Any

from . import get_seats_centers as _get_seats_centers
from .svg_base import *
from .util import filter_kwargs as _filter_kwargs, get_from_write as _get_from_write

_GET_SEATS_CENTERS_PARAMS = {k for k, p in _signature(_get_seats_centers).parameters.items() if p.kind==p.KEYWORD_ONLY}
_WRITE_GROUPED_SVG_PARAMS = {k for k, p in _signature(write_grouped_svg).parameters.items() if p.kind==p.KEYWORD_ONLY}

def write_svg_from_attribution(file: TextIOBase, attrib: dict[SeatData, int], **kwargs) -> None:
    nseats = sum(attrib.values())
    get_seats_centers_kwargs, write_grouped_svg_kwargs, kwargs = _filter_kwargs(_GET_SEATS_CENTERS_PARAMS, _WRITE_GROUPED_SVG_PARAMS, **kwargs)

    if kwargs:
        raise TypeError("Unknown parameters : " + ", ".join(kwargs))

    results = _get_seats_centers(nseats, **get_seats_centers_kwargs)
    seat_centers_by_group = dispatch_seats(attrib, sorted(results, key=results.get, reverse=True))
    write_grouped_svg(file, seat_centers_by_group, results.seat_actual_radius, **write_grouped_svg_kwargs)

get_svg_from_attribution = _get_from_write(write_svg_from_attribution)

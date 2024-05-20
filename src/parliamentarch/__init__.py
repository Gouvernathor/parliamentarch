from inspect import signature

from .geometry import get_seats_centers
from .svg import SeatData, dispatch_seats, get_grouped_svg
from ._util import filter_kwargs, write_from_get

__all__ = ("get_svg_from_attribution", "write_svg_from_attribution", "SeatData")

_GET_SEATS_CENTERS_PARAM_NAMES = {k: p for k, p in signature(get_seats_centers).parameters.items() if p.kind==p.KEYWORD_ONLY}
_WRITE_GROUPED_SVG_PARAM_NAMES = {k: p for k, p in signature(get_grouped_svg).parameters.items() if p.kind==p.KEYWORD_ONLY}

def get_svg_from_attribution(attrib: dict[SeatData, int], **kwargs) -> str:
    nseats = sum(attrib.values())
    get_seats_centers_kwargs, write_grouped_svg_kwargs, kwargs = filter_kwargs(_GET_SEATS_CENTERS_PARAM_NAMES, _WRITE_GROUPED_SVG_PARAM_NAMES, **kwargs)

    if kwargs:
        raise TypeError("Unknown parameters : " + ", ".join(kwargs))

    results = get_seats_centers(nseats, **get_seats_centers_kwargs)
    seat_centers_by_group = dispatch_seats(attrib, sorted(results, key=results.__getitem__, reverse=True))
    return get_grouped_svg(seat_centers_by_group, results.seat_actual_radius, **write_grouped_svg_kwargs)

_sig = signature(get_svg_from_attribution)
_attrib_param = _sig.parameters["attrib"]
get_svg_from_attribution.__signature__ = _sig.replace(parameters=(
    _attrib_param,
    *_GET_SEATS_CENTERS_PARAM_NAMES.values(),
    *_WRITE_GROUPED_SVG_PARAM_NAMES.values()
))
del _sig, _attrib_param

write_svg_from_attribution = write_from_get(get_svg_from_attribution)

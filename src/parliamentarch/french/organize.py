from collections import defaultdict
from collections.abc import Iterable, Mapping
import dataclasses

from .scrape import Scraped_Path, Scraped, Color


@dataclasses.dataclass
class Organized[G]:
    svg_attribs: dict[str, str]
    structural_paths: dict[str, Scraped_Path]
    seats: Mapping[int, Scraped_Path]
    # only the following two should be mutated, generally, and only by values
    grouped_seats: dict[G, list[int]]
    # TODO: turn into group_data and allow more than just color (href too)
    group_colors: dict[G, Color|str|None]

    @staticmethod
    def from_scraped(scraped: Scraped, group_ids: Iterable[G]|None = None) -> "Organized[G]":
        if group_ids is None:
            group_ids = range(len(scraped.paths)) # type: ignore

        group_ids_it = iter(group_ids) # type: ignore

        paths = dict(scraped.paths)
        seats_it: Iterable[Scraped_Path] = Scraped.pop_seats(paths, pop=True, yield_nones=True) # type: ignore
        seats_dict = {}

        grouped_seats: dict[G, list[int]] = defaultdict(list)
        color_groups: dict[Color|str|None, G] = {}
        for i, seat in enumerate(seats_it):
            if seat is None:
                continue

            color = seat.fill
            if color is not None:
                color = str(color)

            seat = dataclasses.replace(seat, fill=None)
            seats_dict[i] = seat

            group = color_groups.get(color, None)
            if group is None:
                group = next(group_ids_it)
                color_groups[color] = group

            grouped_seats[group].append(i)

        grouped_seats.default_factory = None
        return Organized(scraped.svg_attribs, paths, seats_dict, grouped_seats, {g: c for c, g in color_groups.items()})

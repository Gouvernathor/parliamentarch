import enum
import functools
import math

__all__ = ("get_row_thickness", "get_rows_from_nrows", "get_nrows_from_nseats", "FillingStrategy", "get_uniform_plus_three_rows", "get_seats_centers")

# default angle, in degrees, coming from the rightmost seats through the center to the leftmost seats
_DEFAULT_SPAN_ANGLE = 180

def get_row_thickness(nrows: int) -> float:
    """
    Returns the thickness of a row in the same unit as the coordinates.
    """
    return 1 / (4*nrows - 2)

def get_rows_from_nrows(nrows: int, span_angle: float = _DEFAULT_SPAN_ANGLE) -> list[int]:
    """
    This indicates the maximal number of seats for each row for a given number of rows.
    Returns a list of number of seats per row, from inner to outer.
    The length of the list is nrows.
    span_angle, if provided, is the angle in degrees that the hemicycle, as an annulus arc, covers.
    """
    rv = []

    # thickness of a row (as an annulus) compared to the outer diameter of the hemicycle
    # this is equal to the diameter of a single seat
    rad = get_row_thickness(nrows)
    # if you divide the half-disk of the hemicycle
    # into one half-disk of half the radius
    # and one half-annulus outside it,
    # the innermost row lies on the border between the two,
    # and the outermost row lies entirely inside the half-annulus.
    # So, looking at the line cutting the circle and the annulus in half
    # (which is the bottom border of the diagram),
    # all rows minus one half of the innermost are on the left, same on the right,
    # and the radius of the void at the center is equal to that value again.
    # So, total = 4 * (nrows-.5) = 4*nrows - 2

    radian_span_angle = math.pi*span_angle/180

    for r in range(nrows):
        # row radius : the radius of the circle crossing the center of each seat in the row
        row_arc_radius = .5 + 2*r*rad

        rv.append(int(radian_span_angle*row_arc_radius/(2*rad)))

    return rv

@functools.cache
def _cached_get_rows_from_nrows(nrows: int, span_angle: float = _DEFAULT_SPAN_ANGLE) -> tuple[int, ...]:
    """
    Returns tuples to avoid cache mutation issues.
    """
    return tuple(get_rows_from_nrows(nrows, span_angle))

def get_nrows_from_nseats(nseats: int, span_angle: float = _DEFAULT_SPAN_ANGLE) -> int:
    """
    Returns the minimal number of rows necessary to contain nseats seats.
    """
    i = 1
    while sum(_cached_get_rows_from_nrows(i, span_angle)) < nseats:
        i += 1
    return i

_cached_get_nrows_from_nseats = functools.cache(get_nrows_from_nseats)


class FillingStrategy(enum.StrEnum):
    def __new__(cls, value, doc):
        self = str.__new__(cls, value)
        self._value_ = value
        self.__doc__ = doc
        return self

    DEFAULT = enum.auto(), """
    The seats are distributed among all the rows,
    proportionally to the maximum number of seats each row may contain.
    """

    EMPTY_INNER = enum.auto(), """
    Selects as few outermost rows as necessary, then distributes the seats among them,
    proportionally to the maximum number of seats each row may contain.
    """

    OUTER_PRIORITY = enum.auto(), """
    Fills up the rows as much as possible, starting with the outermost ones.
    """

    UNIFORM_PLUS_THREE = enum.auto(), """
    Gives each row 3 more seats than the row inside it,
    and places the rows so that neighboring seats are equally spaced in every row.
    Only supports a span_angle of 180°.
    """


# For these numbers of seats, the general rule below gives a single row.
# 9 seats use 2 rows of the uniform layout (3 + 6). 8 and 10 seats use rows
# that are not 3 apart, placed like the rows of the other strategies.
_UNIFORM_PLUS_THREE_NROWS = {9: 2}
_UNIFORM_PLUS_THREE_SPLITS = {8: (3, 5), 10: (4, 6)}

def get_uniform_plus_three_rows(nseats: int, *,
                                min_nrows: int = 0,
                                ) -> tuple[list[int], list[float], float]:
    """
    Returns the layout used by FillingStrategy.UNIFORM_PLUS_THREE, as a tuple of
    the number of seats in each row, the radius of each row (both from inner to outer),
    and the row thickness, in the same unit as the coordinates.

    Row i holds n0 + 3*i seats. When the seats of a row are about as far apart as
    the rows are, a 180° row holds about π more seats than the row inside it,
    and 3 is the nearest whole number.
    The rows are placed so that the distance between neighboring seats is the same
    in every row.

    The number of rows is chosen by the open radius at the center: the radius of the
    innermost row minus the seat radius at the default seat_radius_factor of .8,
    with the outer edge at 1.
    Among the numbers of rows (at least min_nrows) that hold nseats with no remainder
    and give an open radius between .4 and .6, the one closest to .5 is used.
    If there is none, the number of rows whose open radius is closest to .5 is used,
    and the remainder, which is less than the number of rows,
    adds one seat to each of the outermost rows.

    8, 9 and 10 seats use rows of 3 + 5, 3 + 6 and 4 + 6 seats.
    """
    step = 3

    split = _UNIFORM_PLUS_THREE_SPLITS.get(nseats)
    if split is not None and min_nrows <= len(split):
        row_thicc = get_row_thickness(len(split))
        return list(split), [.5 + 2*r*row_thicc for r in range(len(split))], row_thicc

    # Seats in a row of radius R span an arc of about π*R - 2*thickness,
    # with n-1 gaps between them. For the gap to be the same in every row,
    # and the rows to be one row spacing apart, R = spacing * ((n-1)/3 + 1/π).
    # The outermost row's outer edge is at radius 1.
    def row_spacing_for(n0, nrows):
        outer_base = n0 + step*(nrows-1)
        return 1 / ((outer_base-1)/step + 1/math.pi + .5)

    def open_radius(n0, nrows):
        spacing = row_spacing_for(n0, nrows)
        return spacing * ((n0-1)/step + 1/math.pi) - .8*spacing/2

    # (nrows, seats on the innermost row, remainder, open radius)
    candidates = []
    nrows = max(1, min_nrows)
    while True:
        n0, remainder = divmod(nseats - step*nrows*(nrows-1)//2, nrows)
        if n0 < 2:
            break
        candidates.append((nrows, n0, remainder, open_radius(n0, nrows)))
        nrows += 1

    if not candidates:
        if nseats == 1 and min_nrows <= 1:
            candidates.append((1, 1, 0, open_radius(1, 1)))
        else:
            raise ValueError(f"Cannot place {nseats} seats in at least {min_nrows} rows with a constant step")

    forced = [c for c in candidates if c[0] == _UNIFORM_PLUS_THREE_NROWS.get(nseats)]
    exact = [c for c in candidates if c[2] == 0 and .4 <= c[3] <= .6]
    nrows, n0, remainder, _open = forced[0] if forced else min(exact or candidates, key=lambda c: abs(c[3] - .5))
    row_spacing = row_spacing_for(n0, nrows)

    seats = [n0 + step*r + (r >= nrows-remainder) for r in range(nrows)]
    radii = [row_spacing * ((n0 + step*r - 1)/step + 1/math.pi) for r in range(nrows)]
    return seats, radii, row_spacing/2


def _get_uniform_plus_three_seats_centers(nseats: int, *,
                                          min_nrows: int,
                                          ) -> dict[tuple[float, float], float]:
    seats, radii, row_thicc = get_uniform_plus_three_rows(nseats, min_nrows=min_nrows)

    positions = {}
    for nseats_this_row, row_arc_radius in zip(seats, radii):
        if nseats_this_row == 1:
            positions[1., row_arc_radius] = math.pi/2
            continue
        angle_margin = math.asin(row_thicc/row_arc_radius)
        angle_increment = (math.pi-2*angle_margin) / (nseats_this_row-1)
        for s in range(nseats_this_row):
            angle = angle_margin + s*angle_increment
            positions[row_arc_radius*math.cos(angle)+1, row_arc_radius*math.sin(angle)] = angle

    return positions

def get_seats_centers(nseats: int, *,
                      min_nrows: int = 0,
                      filling_strategy: FillingStrategy = FillingStrategy.DEFAULT,
                      span_angle: float = _DEFAULT_SPAN_ANGLE,
                      ) -> dict[tuple[float, float], float]:
    """
    Returns a list of nseats seat centers as (angle, x, y) tuples.
    The canvas is assumed to be of 2 in width and 1 in height, with the y axis pointing up.
    The angle is calculated from the (1., 0.) center of the hemicycle, in radians,
    with 0° for the leftmost seats, 90° for the center and 180° for the rightmost.

    The minimum number of rows required to contain the given number of seats
    will be computed automatically.
    If min_nrows is higher, that will be the number of rows, otherwise the parameter is ignored.
    Passing a higher number of rows will make the diagram sparser.

    seat_radius_factor should be between 0 and 1,
    with seats touching their neighbors in packed rows at seat_radius_factor=1.
    It is only taken into account when placing the seats at the extreme left and right of the hemicycle
    (which are the seats at the bottom of the diagram),
    although the placement of these seats impacts in turn the placement of the other seats.

    span_angle is the angle in degrees from the rightmost seats,
    through the center, to the leftmost seats.
    It defaults to 180° to make a true hemicycle.
    Values above 180° are not supported.
    """
    if filling_strategy == FillingStrategy.UNIFORM_PLUS_THREE:
        if span_angle != 180:
            raise ValueError(f"{FillingStrategy.UNIFORM_PLUS_THREE} only supports a span_angle of 180, not {span_angle}")
        return _get_uniform_plus_three_seats_centers(nseats, min_nrows=min_nrows)

    nrows = max(min_nrows, _cached_get_nrows_from_nseats(nseats, span_angle))
    # thickness of a row in the same unit as the coordinates
    row_thicc = get_row_thickness(nrows)
    span_angle_margin = (1 - span_angle/180)*math.pi /2

    maxed_rows = _cached_get_rows_from_nrows(nrows, span_angle)

    match filling_strategy:
        case FillingStrategy.DEFAULT:
            starting_row = 0
            filling_ratio = nseats/sum(maxed_rows)

        case FillingStrategy.EMPTY_INNER:
            rows = list(maxed_rows)
            while sum(rows[1:]) >= nseats:
                rows.pop(0)
            # here, rows represents the rows which are enough to contain nseats,
            # and their number of seats

            # this row will be the first one to be filled
            # the innermore ones are empty
            starting_row = nrows-len(rows)
            filling_ratio = nseats/sum(rows)
            del rows

        case FillingStrategy.OUTER_PRIORITY:
            rows = list(maxed_rows)
            while sum(rows) > nseats:
                rows.pop(0)
            # here, rows represents the rows which will be fully filled,
            # and their number of seats

            # this row will be the only one to be partially filled
            # the innermore ones are empty, the outermore ones are fully filled
            starting_row = nrows-len(rows)-1
            seats_on_starting_row = nseats-sum(rows)
            del rows

        case _:
            raise ValueError(f"Unrecognized strategy : {filling_strategy}")

    positions = {}
    for r in range(starting_row, nrows):
        if r == nrows-1: # if it's the last, outermost row
            # fit all the remaining seats
            nseats_this_row = nseats-len(positions)
        elif filling_strategy == FillingStrategy.OUTER_PRIORITY:
            if r == starting_row:
                nseats_this_row = seats_on_starting_row
            else:
                nseats_this_row = maxed_rows[r]
        else:
            # fullness of the diagram times the maximum number of seats in the row
            nseats_this_row = round(filling_ratio * maxed_rows[r])
            # actually more precise rounding : avoid rounding errors to accumulate too much
            # nseats_this_row = round((nseats-len(positions)) * maxed_rows[r]/sum(maxed_rows[r:]))

        # row radius : the radius of the circle crossing the center of each seat in the row
        row_arc_radius = .5 + 2*r*row_thicc

        if nseats_this_row == 1:
            positions[1., row_arc_radius] = math.pi/2
        else:
            # the angle necessary in this row to put the first (and last) seats fully in the canvas
            angle_margin = math.asin(row_thicc/row_arc_radius)
            # add the margin to make up the side angle
            angle_margin += span_angle_margin
            # alternatively, allow the centers of the seats by the side to reach the angle's boundary
            # angle_margin = max(angle_margin, span_angle_margin)

            # the angle separating two seats of that row
            angle_increment = (math.pi-2*angle_margin) / (nseats_this_row-1)
            # a fraction of the remaining space,
            # keeping in mind that the same elevation on start and end limits that remaining place to less than 2pi

            for s in range(nseats_this_row):
                angle = angle_margin + s*angle_increment
                # an oriented angle, so it goes trig positive (counterclockwise)
                positions[row_arc_radius*math.cos(angle)+1, row_arc_radius*math.sin(angle)] = angle

    return positions

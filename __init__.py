import functools
import math

def get_rows_from_number_of_rows(nrows:int)->list[int]:
    """
    Returns a list of number of seats per row, from inner to outer.
    The length of the list is nrows.
    This indicates the maximal number of seats for each row for a given number of rows.
    """
    rv = []

    # thickness of a row (as an annulus) compared to the outer diameter of the hemicycle
    # this is equal to the diameter of a single seat
    rad = 1 / (4*nrows - 2)
    # if you divide the half-disk of the hemicycle
    # into one half-disk of half the radius
    # and one half-annulus outside it,
    # the innermost row lies on the border between the two,
    # and the outermost row lies entirely inside the half-annulus.
    # So, looking at the line cutting those in half (the bottom border of the diagram),
    # all rows minus one half of the innermost are on the left, same on the right,
    # and the radius of the void at the center is equal to that value again.
    # So, total = 4 * (nrows-.5) = 4*nrows - 2

    for r in range(nrows):
        # row radius : the radius of the circle crossing the center of each seat in the row
        R = .5 + 2*r*rad

        rv.append(int(math.pi*R/(2*rad)))

    return rv

@functools.cache
def _cached_get_rows_from_number_of_rows(nrows:int)->tuple[int]:
    """
    Returns tuples to avoid cache mutation issues.
    """
    return tuple(get_rows_from_number_of_rows(nrows))

def get_nrows_from_number_of_seats(nseats:int)->int:
    """
    Returns the minimal number of rows necessary to contain nseats seats.
    """
    i = 1
    while sum(_cached_get_rows_from_number_of_rows(i)) < nseats:
        i += 1
    return i

_cached_get_nrows_from_number_of_seats = functools.cache(get_nrows_from_number_of_seats)


def get_seats_centers(nseats:int, nrows:int=None, *, outer_fill_first:bool=False, _seat_radius:float=None)->list[tuple[float, float, float]]:
    """
    Returns a list of seat centers as (angle, x, y) tuples.
    The canvas is assumed to be of 2 in width and 1 in height, with the y axis pointing up.
    The angle is calculated from the (1., 0.) center of the hemicycle, in radians,
    with 0° for the leftmost seats, 90° for the center and 180° for the rightmost.

    outer_fill_first is the legacy dense_rows
    """
    # _seat_radius is in the same unit as the coordinates
    # TODO: figure out if _seat_radius is relevant or should be removed
    
    if nrows is None:
        nrows = _cached_get_nrows_from_number_of_seats(nseats)
    if _seat_radius is None:
        _seat_radius = 1 / (4*nrows - 2)

    maxed_rows = _cached_get_rows_from_number_of_rows(nrows)
    maxed_nseats = sum(maxed_rows)
    filling_ratio = nseats/maxed_nseats
    
    positions = []
    for r in range(1, nrows+1):
        # row radius : the radius of the circle crossing the center of each seat in the row
        R = .5 + 2*(r-1)*_seat_radius

        if r == nrows: # if it's the last row
            # fit all the remaining seats
            nseats_this_row = nseats-len(positions)
        else:
            # fullness of the diagram times the maximum number of seats in the row
            nseats_this_row = round(filling_ratio * maxed_rows[r-1])

        if nseats_this_row == 1:
            positions.append((math.pi/2, 1., R))
        else:
            for s in range(nseats_this_row):
                # angle of the seat's position relative to the hemicycle center
                angle = s * (math.pi-2*math.asin(_seat_radius/R)) / (nseats_this_row-1) + math.asin(_seat_radius/R)

                positions.append((angle, R*math.cos(angle)+1, R*math.sin(angle)))
    
    positions.sort(reverse=True)
    return positions

import functools
import math

def get_rows_from_number_of_rows(nrows):
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
def _cached_get_rows_from_number_of_rows(nrows):
    """
    Returns tuples to avoid cache mutation issues.
    """
    return tuple(get_rows_from_number_of_rows(nrows))

def get_rows_from_number_of_seats(nseats):
    """
    Returns the minimal number of rows necessary to contain nseats seats.
    """
    i = 1
    while sum(_cached_get_rows_from_number_of_rows(i)) < nseats:
        i += 1
    return i

_cached_get_rows_from_number_of_seats = functools.cache(get_rows_from_number_of_seats)

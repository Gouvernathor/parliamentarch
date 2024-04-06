Parliamentarch
==============

Utility math functions for the generation of arch-styled parliamentary arches.

Base math and layout
--------------------

The idea is to lay a certain number of seats in the form of a hemicycle. The
shape we're after can be mathematically described as follows:

- Take two concentric circles, and considet the area between the two, which is
  called an annulus.
- Cut the annulus in half, following a diameter of the larger circle.

The result is the hemicycle. Now, to place the seats so that they make the form
of the hemicycle:

- The hemicycle fits in a 2:1 rectangle, which we will consider in a "landscape"
  orientation, and with the cut diameter being on the bottom (the top left and
  top right corners of the rectangle are empty).
- The seats will placed in rows, such that:
  - Each seat is described from two concentric circles, with one bigger actual
    radius and one smaller apparent radius, respectively. The apparent radius
    divided by the actual radius makes the "seat radius factor", which may be 1
    in which case the two radii are equal (radii is the plural of radius).
  - The rows are semicircular arcs concentric to the inner and outer arcs.
  - The difference between the radii of two consecutive rows is a constant.
  - The actual diameter of the seats is equal to that constant.
  - The center of a seat is on the arc of that seat's row.
  - In a given row, the distance between two neighboring seats is a constant.
  - The innermost row's arc is the inner arc.
  - The outermost row's arc's radius is equal to the outer arc's radius minus
    the big radius of a seat, so that no seat may overlap the outer arc.
  - The bottom-most seats of each row, which means the first and last seat of
    each row, are placed such that their apparent circumferences are tangent to
    the bottom of the rectangle.
  - When only one seat is placed in a row, the previous rule does not apply and
    the seat is placed at the horizontal center of the diagram.

As a result, there is a maximum number of seats that can be placed on a
given number of rows. For numbers of seats inferior to that value, there exists
several strategies to distribute the seats among the rows.

It should be noted that all of the above applies for the classical case of a
180°-spanning hemicycle. If you specify a smaller angle, the initial annulus
is to be cut using two radii of the larger circle. For seat placements, what
applied to the bottom of the rectangle now applies to the two cut radii.

Tweakable rules
---------------

As hinted above, there are several parameters that can be tweaked to change the
layout of the hemicycle. Among them:

- The span angle of the hemicycle can be set to a value lower than 180° (higher
  values are not supported).
- The number of rows can be set higher than the minimum required to hold the
  provided number of seats.
- The seat radius factor can be changed between 0 and 1, with the seats touching
  their lateral neighbors when the factor is 1.
- As long as the number of seats is not the maximum number the number of rows
  can hold, different strategies can be chosen to distribute the seats.

Main module contents
--------------------

``get_nrows_from_nseats(nseats: int, span_angle: float = 180.) -> int``

Returns the minimum number of rows required to hold the given number of seats,
in a diagram with the given span angle.

``get_rows_from_nrows(nrows: int, span_angle: float = 180.) -> list[int]``

From a given number of rows (and span angle), returns a list of each row's
maximum seat capacity, starting from inner to outer. The list is increasing and
its length is the number of rows.

``FillingStrategy``

This is an enumeration of the different implemented strategies to fill the seats
among the rows. The strategies are:

- ``FillingStrategy.DEFAULT``: The seats distributed proportionally to the
  maximum number of seats each row can hold. The result is that the lateral
  distance between neighboring seats is close between the rows.
- ``FillingStrategy.EMPTY_INNER``: This selects as few outermost rows as
  necessary to hold the given seats, then distributes the seats proportionally
  among them. Depending on the number of seats and of rows, this either leaves
  empty inner rows, or is equivalent to the ``DEFAULT`` strategy. This is
  equivalent to the legacy "dense rows" option, in that not counting the
  potential empty rows, the distance between neighboring seats is the smallest
  possible, and is close between the rows.
- ``FillingStrategy.OUTER_PRIORITY``: This fills the rows to their maximum
  capacity, starting with the outermost rows going in. The result is that given
  a number of rows, adding one seat makes a change in only one row.

``get_seats_from_nseats(nseats: int, *, min_nrows: int = 0, span_angle: float = 180., seat_radius_factor: float = 1., filling_strategy: FillingStrategy = FillingStrategy.DEFAULT) -> list[tuple[float, float]]``

This is the main function. It returns a list of tuples, each tuple corresponding
to a seat's center. The tuple elements are ``(angle, x, y)``, where:

- The angle is in radians, calculated from the left-outermost point of the
  annulus arc, to the center of the arcs, to the center of the seat.
- The x and y coordinates are cartesian starting from the bottom-left of the
  rectangle, with the x axis pointing right and the y axis pointing up. The
  radius of the outermost circle (or of the outermost row) is 1, so x goes from
  0 to 2 and y goes from 0 to 1.

Todos and future features
-------------------------

- Add a submodule for SVG export
- Add the option for all rows to contain an even number of seats
- Add a CLI for SVG files generation

Parliamentarch
==============

Utility math functions for the generation of arch-styled parliamentary arches.

Base math and layout
--------------------

The idea is to lay a certain number of seats in the form of a hemicycle. The
shape we're after can be mathematically described as follows:

- Take two concentric circles where the outer one's radius is twice the inner's
- Consider the area between the two, which is called an annulus.
- Cut the annulus in half, following a diameter of the larger circle.

The result is the hemicycle. Now, to place the seats so that they make the form
of the hemicycle:

- The hemicycle fits in a 2:1 rectangle, which we will consider in a "landscape"
  orientation, and with the cut diameter being on the bottom (the top left and
  top right corners of the rectangle are empty).
- The seats will placed in rows, such that:
  - The rows are semicircular arcs concentric to the inner and outer arcs.

  - The difference between the radii of two consecutive rows is a constant
    called the "row thickness" (radii is the plural of radius).

  - The seat are circles (or disks) of equal radius. That radius divided by half
    of the row thickness makes the "seat radius factor".

  - The center of a seat is on the arc of that seat's row.
  - In a given row, the distance between two neighboring seats is a constant.
  - The innermost row's arc is the inner arc.
  - The radius of the outermost row's arc is equal to the radius of the outer
    arc minus half of the row thickness, such that no seat may overlap the
    outer arc.

  - The bottom-most seats of each row, which means the first and last seat of
    each row, are tangent to the bottom of the rectangle.

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
  values are not supported). However, values so low as to prevent some row from
  containing even one seat are not supported, will yield incorrect results, and
  may raise errors in future versions.
- The number of rows can be set higher than the minimum required to hold the
  provided number of seats.
- The seat radius factor can be changed between 0 and 1, with the seats touching
  their lateral neighbors when the factor is 1.
- As long as the number of seats is not the maximum number the number of rows
  can hold, different strategies can be chosen to distribute the seats.

Main module content
-------------------

These are found in the ``parliamentarch`` module.

``SeatData``

This class is defined and explained in the SVG submodule below, but it is
exposed as part of the main module.

``write_svg_from_attribution(file, attrib, **kwargs)``

This function writes an SVG file representing a hemicycle. The parameters are as
follows:

- ``file: str|io.TextIOBase``: a file-like object open in text mode, or the path
  to the file to write on. If a path is provided, the file will be created if it
  doesn't exist, and otherwise overwritten.
- ``attrib: dict[SeatData, int]``: a mapping from a SeatData object applying to
  a number of seats in the resulting hemicycle, to the number of seats each
  object applies to. Typically, each SeatData object corresponds to a group or
  party. The ordering of the keys matter, and the elements will be arranged from
  left to right in the hemicycle.
- ``**kwargs``: all optional keyword parameters taken by
  ``parliamentarch.geometry.get_seats_centers`` or by
  ``parliamentarch.svg.write_svg`` can be passed to this function.

``get_svg_from_attribution(attrib, **kwargs) -> str``

Instead of writing it to a file, this function returns the SVG content as a
string. The parameters are otherwise the same.

Command-line interface
----------------------

See ``py -m parliamentarch -h`` for the accepted parameters.

Geometry submodule contents
---------------------------

These are found in the ``parliamentarch.geometry`` submodule.

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

- ``FillingStrategy.DEFAULT``: The seats are distributed proportionally to the
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

``get_seats_centers(nseats: int, *, min_nrows: int = 0, span_angle: float = 180., seat_radius_factor: float = 1., filling_strategy: FillingStrategy = FillingStrategy.DEFAULT) -> list[tuple[float, float]]``

This is the main function. Other than self-explanatory parameters similar to
the functions above:

- ``min_nrows``: The minimum number of rows to use. Only taken into account if
  the required number of rows to hold the given number of seats is less than
  that. Defaults to 0, which means using the minimum number of rows possible.
- ``seat_radius_factor``: The ratio of the seats radius over the row thickness.
  Defaults to 1, which makes seats touch their neighbors.

The function returns a dict-like object representing the ensemble of seats. The
keys are ``(x, y)``, the cartesian coordinates of the center of the seat. The
coordinates start from the bottom-left corner of the rectangle, with the x axis
pointing right and the y axis pointing up. The radius of the outermost circle
(equal to the height and half the width of the rectangle) is 1, so x goes from
0 to 2 and y goes from 0 to 1.

The value of each entry is the angle, in radians, calculated from the
right-outermost point of the annulus arc, to the center of the arcs, to the
center of the seat.

In addition, the return value has the following attributes:

- ``row_thickness``: the thickness of the rows, in the same unit as the
  coordinates.
- ``seat_actual_radius``: the radius of the seats, in the same unit as the
  coordinates.
- ``nrows``: as passed to the function.
- ``seat_radius_factor``: as passed to the function.

Calling ``sorted(di, key=di.get, reverse=True)`` will return a list of the seats
arranged from left to right.

SVG submodule content
---------------------

These are found in the ``parliamentarch.svg`` submodule.

``SeatData(data, color, border_size=0, border_color="#000")``

A class representing how to display a given seat or set of seats.

- ``data: str``: metadata about the group of seats, which will end up in the
  SVG file. Typically the name of the party or of the member.
- ``color: Color``: the color with which to fill the seat circles. This may take
  any number of formats: a "#RGB", "#RRGGBB", "#RGBA" or "#RRGGBBAA" string, a
  RBG ``tuple[int, int, int]``, or a RGBA ``tuple[int, int, int, int]`` with
  ints between 0 and 255. CSS color names are also supported.
- ``border_size: float``: the size of the border around the seat circle. (to be
  documented at greater length)
- ``border_color: Color``: the color of the border.

``write_svg(file, seat_centers, seat_actual_radius, *, canvas_size=175, margins=5., write_number_of_seats=True, font_size_factor=...)``

This function writes an SVG file representing a hemicycle. The parameters are as
follows:

- ``file: str|io.TextIOBase``: a file-like object open in text mode, or the path
  to the file to write on. If a path is provided, the file will be created if it
  doesn't exist, and otherwise overwritten.
- ``seat_centers: dict[tuple[float, float], SeatData]``: a mapping from the
  (x, y) coordinates of each seat's center to a SeatData object.
- ``seat_actual_radius: float``: as output by ``get_seats_centers``.
- ``canvas_size: float``: the height of the 2:1 rectangle in which the hemicycle
  will be drawn.
- ``margins: float|tuple[float, float]|tuple[float, float, float, float]``:
  the margins around that rectangle. If four values are given, they are the
  left, top, right, and bottom margins, in that order. If two values are given,
  they are the horizontal and vertical margins, in that order. If one value is
  given, it is used for all four margins.
- ``write_number_of_seats: bool``: whether to write the total number of seats at
  the bottom center of the diagram - in the well of the House.
- ``font_size_factor: float``: a factor you should tweak to change the font size
  of the number of seats. The default value is around 0.2. Keeping this constant
  will keep the font size in scale when changing the canvas size.

``write_grouped_svg(file, seat_centers_by_group, *args, **kwargs)``

This takes the relationship between seats and SeatData a different way, which is
way more optimized both in SVG file size and in time. The other parameters are
the same.

- ``seat_centers_by_group: dict[SeatData, list[tuple[float, float]]]``: a
  mapping from the SeatData of a group of seats to a list of (x, y) seat center
  coordinates as output by ``get_seats_centers``.

These two functions have equivalents which return the content of the SVG file a
string. They take the same parameters except for the ``file``, and are named
``get_svg`` and ``get_grouped_svg``.

``dispatch_seats(group_seats, seats) -> dict[SeatData, list[S]]``

A function helps make the transition from
``parliamentarch.get_seats_centers``'s output to the way ``write_grouped_svg``
expects it:

- ``group_seats: dict[SeatData, int]``: a mapping from the SeatData of a group
  of seats to the number of seats in that group. Key ordering matters.
- ``seats: Iterable[S]``: an iterable of seats in whatever format, but intended
  to be (x, y) tuples. Its length must be the sum of the values of
  ``group_seats``. Its ordering matters.

Typically the groups are ordered from left to right, and the seats are ordered
from left to right. ``sorted(di, key=di.get, reverse=True)`` helps with that.

SeatData and dispatch_seats may be moved to another module in the future.

Todos and future features
-------------------------

- Have the main functions support a sequence of SeatData objects using ``dict.fromkeys(seq, 1)``
- Allow SeatData to take some <a> element properties (like href), and if so use <a> instead of <g>
- Allow SeatData to contain more creative SVG content like gradients
  - Maybe give it a .wrap method that wraps the circles in a g or a, and make it subclassable ?
  - Maybe just give a style method ?
- Add tests
- Add the option to force all rows to contain an even number of seats
- Add a simpler way to input parameters in CLI
  - Maybe by allowing the use of the standard input to pass JSON content ?

# coding: utf-8
"""
    cairocffi.fonts
    ~~~~~~~~~~~~~~~

    Bindings for font-related objects.

    :copyright: Copyright 2013 by Simon Sapin
    :license: BSD, see LICENSE for details.

"""

from . import ffi, cairo, _check_status, constants, _keepref
from .matrix import Matrix
from .compat import xrange


def _encode_string(string):
    """Return a byte string, encoding Unicode with UTF-8."""
    if not isinstance(string, bytes):
        string = string.encode('utf8')
    return ffi.new('char[]', string)


class FontFace(object):
    """The base class for all font face types.

    Should not be instantiated directly, but see :doc:`cffi_api`.
    An instance may be returned for cairo font face types
    that are not (yet) defined in cairocffi.

    """
    def __init__(self, pointer):
        self._pointer = ffi.gc(
            pointer, _keepref(cairo, cairo.cairo_font_face_destroy))
        self._check_status()

    def _check_status(self):
        _check_status(cairo.cairo_font_face_status(self._pointer))

    @staticmethod
    def _from_pointer(pointer, incref):
        """Wrap an existing :c:type:`cairo_font_face_t *` cdata pointer.

        :type incref: bool
        :param incref:
            Whether increase the :ref:`reference count <refcounting>` now.
        :return:
            A new instance of :class:`FontFace` or one of its sub-classes,
            depending on the face’s type.

        """
        if pointer == ffi.NULL:
            raise ValueError('Null pointer')
        if incref:
            cairo.cairo_font_face_reference(pointer)
        self = object.__new__(FONT_TYPE_TO_CLASS.get(
            cairo.cairo_font_face_get_type(pointer), FontFace))
        FontFace.__init__(self, pointer)  # Skip the subclass’s __init__
        return self


class ToyFontFace(FontFace):
    """Creates a font face from a triplet of family, slant, and weight.
    These font faces are used in implementation of cairo’s "toy" font API.

    If family is the zero-length string ``""``,
    the platform-specific default family is assumed.
    The default family then can be queried using :meth:`get_family`.

    The :meth:`Context.select_font_face` method uses this to create font faces.
    See that method for limitations and other details of toy font faces.

    :param family: a font family name, as an Unicode or UTF-8 string.
    :param slant: The :ref:`FONT_SLANT` string for the font face.
    :param weight: The :ref:`FONT_WEIGHT` string for the font face.

    """
    def __init__(self, family='', slant=constants.FONT_SLANT_NORMAL,
                 weight=constants.FONT_WEIGHT_NORMAL):
        FontFace.__init__(self, cairo.cairo_toy_font_face_create(
            _encode_string(family), slant, weight))

    def get_family(self):
        """Return this font face’s family name."""
        return ffi.string(cairo.cairo_toy_font_face_get_family(
            self._pointer)).decode('utf8', 'replace')

    def get_slant(self):
        """Return this font face’s :ref:`FONT_SLANT` string."""
        return cairo.cairo_toy_font_face_get_slant(self._pointer)

    def get_weight(self):
        """Return this font face’s :ref:`FONT_WEIGHT` string."""
        return cairo.cairo_toy_font_face_get_weight(self._pointer)


FONT_TYPE_TO_CLASS = {
    constants.FONT_TYPE_TOY: ToyFontFace,
}


class ScaledFont(object):
    """Creates a :class:`ScaledFont` object from a font face and matrices
    that describe the size of the font
    and the environment in which it will be used.

    :param font_face: A :class:`FontFace` object.
    :type font_matrix: Matrix
    :param font_matrix:
        Font space to user space transformation matrix for the font.
        In the simplest case of a N point font,
        this matrix is just a scale by N,
        but it can also be used to shear the font
        or stretch it unequally along the two axes.
        If omitted, a scale by 10 matrix is assumed (ie. a 10 point font size).
        See :class:`Context.set_font_matrix`.
    :type ctm: Matrix
    :param ctm:
        User to device transformation matrix with which the font will be used.
        If omitted, an identity matrix is assumed.
    :param options:
        The :class:`FontOptions` object to use
        when getting metrics for the font and rendering with it.
        If omitted, the default options are assumed.

    """
    def __init__(self, font_face, font_matrix=None, ctm=None, options=None):
        if font_matrix is None:
            font_matrix = Matrix()
            font_matrix.scale(10)  # Default font size
        if ctm is None:
            ctm = Matrix()
        if options is None:
            options = FontOptions()
        self._init_pointer(cairo.cairo_scaled_font_create(
            font_face._pointer, font_matrix._pointer,
            ctm._pointer, options._pointer))

    def _init_pointer(self, pointer):
        self._pointer = ffi.gc(
            pointer, _keepref(cairo, cairo.cairo_scaled_font_destroy))
        self._check_status()

    def _check_status(self):
        _check_status(cairo.cairo_scaled_font_status(self._pointer))

    @staticmethod
    def _from_pointer(pointer, incref):
        """Wrap an existing :c:type:`cairo_scaled_font_t *` cdata pointer.

        :type incref: bool
        :param incref:
            Whether increase the :ref:`reference count <refcounting>` now.
        :return: A new :class:`ScaledFont` instance.

        """
        if pointer == ffi.NULL:
            raise ValueError('Null pointer')
        if incref:
            cairo.cairo_scaled_font_reference(pointer)
        self = object.__new__(ScaledFont)
        ScaledFont._init_pointer(self, pointer)
        return self

    def get_font_face(self):
        """Return the font face that this scaled font uses.

        :returns:
            A new instance of :class:`FontFace` (or one of its sub-classes).
            Might wrap be the same font face passed to :class:`ScaledFont`,
            but this does not hold true for all possible cases.

        """
        return FontFace._from_pointer(
            cairo.cairo_scaled_font_get_font_face(self._pointer), incref=True)

    def get_font_options(self):
        """Copies the scaled font’s options.

        :returns: A new :class:`FontOptions` object.

        """
        font_options = FontOptions()
        cairo.cairo_scaled_font_get_font_options(
            self._pointer, font_options._pointer)
        return font_options

    def get_font_matrix(self):
        """Copies the scaled font’s font matrix.

        :returns: A new :class:`Matrix` object.

        """
        matrix = Matrix()
        cairo.cairo_scaled_font_get_font_matrix(self._pointer, matrix._pointer)
        self._check_status()
        return matrix

    def get_ctm(self):
        """Copies the scaled font’s font current transform matrix.

        Note that the translation offsets ``(x0, y0)`` of the CTM
        are ignored by :class:`ScaledFont`.
        So, the matrix this method returns always has 0 as ``x0`` and ``y0``.

        :returns: A new :class:`Matrix` object.

        """
        matrix = Matrix()
        cairo.cairo_scaled_font_get_ctm(self._pointer, matrix._pointer)
        self._check_status()
        return matrix

    def get_scale_matrix(self):
        """Copies the scaled font’s scaled matrix.

        The scale matrix is product of the font matrix
        and the ctm associated with the scaled font,
        and hence is the matrix mapping from font space to device space.

        :returns: A new :class:`Matrix` object.

        """
        matrix = Matrix()
        cairo.cairo_scaled_font_get_scale_matrix(
            self._pointer, matrix._pointer)
        self._check_status()
        return matrix

    def extents(self):
        """Return the scaled font’s extents.
        See :meth:`Context.font_extents`.

        :returns:
            A ``(ascent, descent, height, max_x_advance, max_y_advance)``
            tuple of floats.

        """
        extents = ffi.new('cairo_font_extents_t *')
        cairo.cairo_scaled_font_extents(self._pointer, extents)
        self._check_status()
        return (
            extents.ascent, extents.descent, extents.height,
            extents.max_x_advance, extents.max_y_advance)

    def text_extents(self, text):
        """Returns the extents for a string of text.

        The extents describe a user-space rectangle
        that encloses the "inked" portion of the text,
        (as it would be drawn by :meth:`show_text`).
        Additionally, the :obj:`x_advance` and :obj:`y_advance` values
        indicate the amount by which the current point would be advanced
        by :meth:`show_text`.

        :param text: The text to measure, as an Unicode or UTF-8 string.
        :returns:
            A ``(x_bearing, y_bearing, width, height, x_advance, y_advance)``
            tuple of floats.
            See :meth:`Context.text_extents` for details.

        """
        extents = ffi.new('cairo_text_extents_t *')
        cairo.cairo_scaled_font_text_extents(
            self._pointer, _encode_string(text), extents)
        self._check_status()
        return (
            extents.x_bearing, extents.y_bearing,
            extents.width, extents.height,
            extents.x_advance, extents.y_advance)

    def glyph_extents(self, glyphs):
        """Returns the extents for a list of glyphs.

        The extents describe a user-space rectangle
        that encloses the "inked" portion of the glyphs,
        (as it would be drawn by :meth:`show_glyphs`).
        Additionally, the :obj:`x_advance` and :obj:`y_advance` values
        indicate the amount by which the current point would be advanced
        by :meth:`show_glyphs`.

        :param glyphs:
            A list of glyphs, as returned by :meth:`text_to_glyphs`.
            Each glyph is a ``(glyph_id, x, y)`` tuple
            of an integer and two floats.
        :returns:
            A ``(x_bearing, y_bearing, width, height, x_advance, y_advance)``
            tuple of floats.
            See :meth:`Context.text_extents` for details.

        """
        glyphs = ffi.new('cairo_glyph_t[]', glyphs)
        extents = ffi.new('cairo_text_extents_t *')
        cairo.cairo_scaled_font_glyph_extents(
            self._pointer, glyphs, len(glyphs), extents)
        self._check_status()
        return (
            extents.x_bearing, extents.y_bearing,
            extents.width, extents.height,
            extents.x_advance, extents.y_advance)

    def text_to_glyphs(self, x, y, text, with_clusters):
        """Converts a string of text to a list of glyphs,
        optionally with cluster mapping,
        that can be used to render later using this scaled font.

        The output values can be readily passed to
        :meth:`Context.show_text_glyphs`, :meth:`Context.show_glyphs`
        or related methods,
        assuming that the exact same :class:`ScaledFont`
        is used for the operation.

        :type x: float
        :type y: float
        :type with_clusters: bool
        :param x: X position to place first glyph.
        :param y: Y position to place first glyph.
        :param text: The text to convert, as an Unicode or UTF-8 string.
        :param with_clusters: Whether to compute the cluster mapping.
        :returns:
            A ``(glyphs, clusters, clusters_flags)`` tuple
            if :obj:`with_clusters` is true, otherwise just :obj:`glyphs`.
            See :meth:`Context.show_text_glyphs` for the data structure.

        .. note::

            This method is part of
            what the cairo designers call the "toy" text API.
            It is convenient for short demos and simple programs,
            but it is not expected to be adequate
            for serious text-using applications.
            See :ref:`fonts` for details
            and :meth:`Context.show_glyphs`
            for the "real" text display API in cairo.

        """
        glyphs = ffi.new('cairo_glyph_t **', ffi.NULL)
        num_glyphs = ffi.new('int *')
        if with_clusters:
            clusters = ffi.new('cairo_text_cluster_t **', ffi.NULL)
            num_clusters = ffi.new('int *')
            cluster_flags = ffi.new('cairo_text_cluster_flags_t *')
        else:
            clusters = ffi.NULL
            num_clusters = ffi.NULL
            cluster_flags = ffi.NULL
        # TODO: Pass len_utf8 explicitly to support NULL bytes?
        status = cairo.cairo_scaled_font_text_to_glyphs(
            self._pointer, x, y, _encode_string(text), -1,
            glyphs, num_glyphs, clusters, num_clusters, cluster_flags)
        glyphs = ffi.gc(glyphs[0], _keepref(cairo, cairo.cairo_glyph_free))
        if with_clusters:
            clusters = ffi.gc(
                clusters[0], _keepref(cairo, cairo.cairo_text_cluster_free))
        _check_status(status)
        glyphs = [
            (glyph.index, glyph.x, glyph.y)
            for i in xrange(num_glyphs[0])
            for glyph in [glyphs[i]]]
        if with_clusters:
            clusters = [
                (cluster.num_bytes, cluster.num_glyphs)
                for i in xrange(num_clusters[0])
                for cluster in [clusters[i]]]
            return glyphs, clusters, cluster_flags[0]
        else:
            return glyphs


class FontOptions(object):
    """An opaque object holding all options that are used when rendering fonts.

    Individual features of a :class:`FontOptions`
    can be set or accessed using method
    named :meth:`set_FEATURE_NAME` and :meth:`get_FEATURE_NAME`,
    like :meth:`set_antialias` and :meth:`get_antialias`.

    New features may be added to :class:`FontOptions` in the future.
    For this reason, ``==``, :meth:`copy`, :meth:`merge`, and :func:`hash`
    should be used to check for equality copy,, merge,
    or compute a hash value of :class:`FontOptions` objects.

    :param values:
        Call the corresponding :meth:`set_FEATURE_NAME` methods
        after creating a new :class:`FontOptions`::

            options = FontOptions()
            options.set_antialias(cairocffi.ANTIALIAS_BEST)
            assert FontOptions(antialias=cairocffi.ANTIALIAS_BEST) == options

    """
    def __init__(self, **values):
        self._init_pointer(cairo.cairo_font_options_create())
        for name, value in values.items():
            getattr(self, 'set_' + name)(value)

    def _init_pointer(self, pointer):
        self._pointer = ffi.gc(
            pointer, _keepref(cairo, cairo.cairo_font_options_destroy))
        self._check_status()

    def _check_status(self):
        _check_status(cairo.cairo_font_options_status(self._pointer))

    def copy(self):
        """Return a new :class:`FontOptions` with the same values."""
        cls = type(self)
        other = object.__new__(cls)
        cls._init_pointer(other, cairo.cairo_font_options_copy(self._pointer))
        return other

    def merge(self, other):
        """Merges non-default options from :obj:`other`,
        replacing existing values.
        This operation can be thought of as somewhat similar
        to compositing other onto options
        with the operation of :obj:`OVER <OPERATOR_OVER>`.

        """
        cairo.cairo_font_options_merge(self._pointer, other._pointer)
        _check_status(cairo.cairo_font_options_status(self._pointer))

    def __hash__(self):
        return cairo.cairo_font_options_hash(self._pointer)

    def __eq__(self, other):
        return cairo.cairo_font_options_equal(self._pointer, other._pointer)

    def __ne__(self, other):
        return not self == other

    equal = __eq__
    hash = __hash__

    def set_antialias(self, antialias):
        """Changes the :ref:`ANTIALIAS` for the font options object.
        This specifies the type of antialiasing to do when rendering text.

        """
        cairo.cairo_font_options_set_antialias(self._pointer, antialias)
        self._check_status()

    def get_antialias(self):
        """Return the :ref:`ANTIALIAS` string for the font options object."""
        return cairo.cairo_font_options_get_antialias(self._pointer)

    def set_subpixel_order(self, subpixel_order):
        """Changes the :ref:`SUBPIXEL_ORDER` for the font options object.
         The subpixel order specifies the order of color elements
         within each pixel on the display device
         when rendering with an antialiasing mode of
         :obj:`SUBPIXEL <ANTIALIAS_SUBPIXEL>`.

        """
        cairo.cairo_font_options_set_subpixel_order(
            self._pointer, subpixel_order)
        self._check_status()

    def get_subpixel_order(self):
        """Return the :ref:`SUBPIXEL_ORDER` string
        for the font options object.

        """
        return cairo.cairo_font_options_get_subpixel_order(self._pointer)

    def set_hint_style(self, hint_style):
        """Changes the :ref:`HINT_STYLE` for the font options object.
        This controls whether to fit font outlines to the pixel grid,
        and if so, whether to optimize for fidelity or contrast.

        """
        cairo.cairo_font_options_set_hint_style(self._pointer, hint_style)
        self._check_status()

    def get_hint_style(self):
        """Return the :ref:`HINT_STYLE` string for the font options object."""
        return cairo.cairo_font_options_get_hint_style(self._pointer)

    def set_hint_metrics(self, hint_metrics):
        """Changes the :ref:`HINT_METRICS` for the font options object.
        This controls whether metrics are quantized
        to integer values in device units.

        """
        cairo.cairo_font_options_set_hint_metrics(self._pointer, hint_metrics)
        self._check_status()

    def get_hint_metrics(self):
        """Return the :ref:`HINT_METRICS` string
        for the font options object.

        """
        return cairo.cairo_font_options_get_hint_metrics(self._pointer)

    def set_variations(self, variations):
        """Sets the OpenType font variations for the font options object.

        Font variations are specified as a string with a format that is similar
        to the CSS font-variation-settings. The string contains a
        comma-separated list of axis assignments, which each assignment
        consists of a 4-character axis name and a value, separated by
        whitespace and optional equals sign.

        :param variations: the new font variations, or ``None``.

        *New in cairo 1.16.*

        *New in cairocffi 0.9.*

        """
        if variations is None:
            variations = ffi.NULL
        else:
            variations = _encode_string(variations)
        cairo.cairo_font_options_set_variations(self._pointer, variations)
        self._check_status()

    def get_variations(self):
        """Gets the OpenType font variations for the font options object.

        See :meth:`set_variations` for details about the
        string format.

        Return value: the font variations for the font options object. The
        returned string belongs to the ``options`` and must not be modified.
        It is valid until either the font options object is destroyed or the
        font variations in this object is modified with :meth:`set_variations`.

        *New in cairo 1.16.*

        *New in cairocffi 0.9.*

        """
        variations = cairo.cairo_font_options_get_variations(self._pointer)
        if variations != ffi.NULL:
            return ffi.string(variations).decode('utf8', 'replace')

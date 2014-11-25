__copyright__ = "Copyright (c) 2014 Yclept Nemo"
__license__ = "GNU GPL v3"


import decorator

from gi.repository import Pango, PangoCairo


class PushPop(object):
    def __init__(self, *args):
        self.keys = args
        self.ctxs = []

    def store(self, mapping):
        for k,v in mapping:
            if k in self.keys:
                self.ctxs.append(v)

    def push(self):
        for ctx in self.ctxs:
            ctx.save()

    def pop(self):
        for ctx in self.ctxs:
            ctx.restore()

    def wrapper(self, func, *args, **kwargs):
        self.store(enumerate(args))
        self.store(kwargs.items())
        self.push()
        result = func(*args, **kwargs)
        self.pop()
        return result

    def __call__(self, func):
        return decorator.decorator(self.wrapper, func)


def get_max_device_ink_size\
    ( glyph_iterable
    , pango_context=None
    , pango_fontmap=None
    , pango_fontdescription=None
    ):
    if pango_context is None and pango_fontmap is None:
        pango_fontmap = PangoCairo.FontMap.get_default()
    if pango_context is None:
        pango_context = Pango.Context.new()
    if pango_fontmap is not None:
        pango_context.set_font_map(pango_fontmap)
    if pango_fontdescription is not None:
        pango_context.set_font_description(pango_fontdescription)

    dimensions = [0,0]
    pango_layout = Pango.Layout.new(pango_context)
    for glyph in glyph_iterable:
        pango_layout.set_text(glyph, 1)
        ink_rect = pango_layout.get_extents()[0]
        ink_dimensions =\
            [ i / Pango.SCALE
              for i in
              (ink_rect.width, ink_rect.height)
            ]
        dimensions =\
            [ max(d)
              for d
              in zip(dimensions, ink_dimensions)
            ]
    return dimensions

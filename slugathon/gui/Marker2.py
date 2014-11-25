#!/usr/bin/env python

__copyright__ = "Copyright (c) 2005-2012 David Ripton"
__license__ = "GNU GPL v2"


import tempfile
import os

from gi.repository import Gtk, GdkPixbuf, Pango, PangoCairo
import cairo

from slugathon.util import fileutils
from slugathon.util.Rectangle import Rectangle
from slugathon.util.cairoutils import PushPop, get_max_device_ink_size


CHIT_SCALE_FACTOR = 3


class Marker(Rectangle, Gtk.EventBox):
    font_description = Pango.FontDescription("Monospace 10")
    font_fg = Rectangle\
        ( (0,0)
        , get_max_device_ink_size\
            ( "0123456789"
            , pango_fontdescription=font_description
            )
        )
    font_limits = Rectangle.from_absolute((0.6, 0.6), (0.9, 0.9))
    font_scale = font_fg.scale_inscribe(font_limits)
    font_fg[1:1] = font_limits[1:1]
    font_border = (0.05, 0.05)
    font_bg = Rectangle.from_absolute\
        ( font_fg[0:0] - font_border
        , font_fg[1:1] + font_border
        )
    font_bg_color = (1,1,1)
    font_fg_color = (0,0,0)

    """Clickable GUI legion marker"""

    def __init__(self, legion, show_height, location=(0,0), scale=15):
        size = CHIT_SCALE_FACTOR * scale
        super().__init__(location, (size, size))
        self.legion = legion
        self.name = legion.markerid
        self.chit_scale = CHIT_SCALE_FACTOR * scale
        self.show_height = show_height
        self.image_path = fileutils.basedir("images/legion/{}.png".format(self.name))
        self.location = None    # (x, y) of top left corner
        image = self.render_image()
        self.add(image)


    def render_image(self):
        source = cairo.ImageSurface.create_from_png(self.image_path)
        target = cairo.ImageSurface\
            ( cairo.FORMAT_ARGB32
            , self.chit_scale
            , self.chit_scale
            )
        ctx = cairo.Context(target)
        ctx.scale\
            ( target.get_width() / source.get_width()
            , target.get_height() / source.get_height()
            )
        ctx.set_source_surface(source)
        ctx.paint()
        self.render_text(ctx)
        image = Gtk.Image.new_from_surface(target)
        return image


#    def render_image(self):
#        self.height = len(self.legion)
#        input_surface = cairo.ImageSurface.create_from_png(self.image_path)
#        self._render_text(input_surface)
#        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.chit_scale,
#                                          self.chit_scale)
#        ctx = cairo.Context(self.surface)
#        ctx.scale(float(self.chit_scale) / input_surface.get_width(),
#                  float(self.chit_scale) / input_surface.get_height())
#        ctx.set_source_surface(input_surface)
#        ctx.paint()
#        with tempfile.NamedTemporaryFile(prefix="slugathon",
#                                         suffix=".png", delete=False) \
#                as tmp_file:
#            tmp_path = tmp_file.name
#        self.surface.write_to_png(tmp_path)
#        pixbuf = GdkPixbuf.Pixbuf.new_from_file(tmp_path)
#        os.remove(tmp_path)
#        self.event_box = Gtk.EventBox()
#        self.event_box.marker = self
#        self.image = Gtk.Image()
#        self.image.set_from_pixbuf(pixbuf)
#        self.event_box.add(self.image)

    def __repr__(self):
        return "Marker %s in %s" % (self.name, self.legion.hexlabel)

    def point_inside(self, point):
        if not self.location:
            return False
        return guiutils.point_in_square(point, self.location, self.chit_scale)

    def update_height(self):
        if self.show_height and self.height != len(self.legion):
            self.render_image()

    def show(self):
        self.event_box.show()
        self.image.show()

    def connect(self, event, method):
        self.event_box.connect(event, method)

    @PushPop(1)
    def render_text(self, ctx):
        """ Add legion height to a Cairo surface
        """
        if not self.show_height:
            return
        ctx.identity_matrix()
        ctx.scale\
            ( ctx.get_target().get_width()
            , ctx.get_target().get_height()
            )
        ctx.set_source_rgb(*self.font_bg_color)
        ctx.rectangle\
            ( self.font_fg.location.x
            , self.font_fg.location.y
            , self.font_fg.width
            , self.font_fg.height
            )
        ctx.fill()


        print("-----------------------------------")


        cairo_fontoptions = cairo.FontOptions()
        cairo_fontoptions.set_hint_metrics(cairo.HINT_METRICS_OFF)
        cairo_fontoptions.set_hint_style(cairo.HINT_STYLE_NONE)



        ctx.set_font_options(cairo_fontoptions)
        ctx.identity_matrix()
        pango_context = PangoCairo.create_context(ctx)

        l1 = Pango.Layout(pango_context)
        l1.set_font_description(self.font_description)
        l1.set_text("8",1)
        e1 = l1.get_extents()[0]
        print(e1.x / Pango.SCALE, e1.y / Pango.SCALE, e1.width / Pango.SCALE, e1.height / Pango.SCALE)

        PangoCairo.context_set_resolution(pango_context, 192)
        l1 = Pango.Layout(pango_context)
        l1.set_font_description(self.font_description)
        l1.set_text("8",1)
        e1 = l1.get_extents()[0]
        print(e1.x / Pango.SCALE, e1.y / Pango.SCALE, e1.width / Pango.SCALE, e1.height / Pango.SCALE)

        PangoCairo.context_set_resolution(pango_context, 48)
        l1 = Pango.Layout(pango_context)
        l1.set_font_description(self.font_description)
        l1.set_text("8",1)
        e1 = l1.get_extents()[0]
        print(e1.x / Pango.SCALE, e1.y / Pango.SCALE, e1.width / Pango.SCALE, e1.height / Pango.SCALE)

        PangoCairo.context_set_resolution(pango_context, 5)
        l1 = Pango.Layout(pango_context)
        l1.set_font_description(self.font_description)
        l1.set_text("8",1)
        e1 = l1.get_extents()[0]
        print(e1.x / Pango.SCALE, e1.y / Pango.SCALE, e1.width / Pango.SCALE, e1.height / Pango.SCALE)

        PangoCairo.context_set_resolution(pango_context, 96)
        l1 = Pango.Layout(pango_context)
        l1.set_font_description(self.font_description)
        l1.set_text("8",1)
        e1 = l1.get_extents()[0]
        print(e1.x / Pango.SCALE, e1.y / Pango.SCALE, e1.width / Pango.SCALE, e1.height / Pango.SCALE)


        print("-----------------------------------")


        ctx.set_font_options(cairo_fontoptions)

        ctx.identity_matrix()
        ctx.scale(*(1,)*2)
        layout = PangoCairo.create_layout(ctx)
        layout.set_font_description(self.font_description)
        layout.set_text("8",1)
        e1 = layout.get_extents()[0]
        print(e1.x / Pango.SCALE, e1.y / Pango.SCALE, e1.width / Pango.SCALE, e1.height / Pango.SCALE)

        ctx.identity_matrix()
        ctx.scale(*(10,)*2)
        layout = PangoCairo.create_layout(ctx)
        layout.set_font_description(self.font_description)
        layout.set_text("8",1)
        e1 = layout.get_extents()[0]
        print(e1.x / Pango.SCALE, e1.y / Pango.SCALE, e1.width / Pango.SCALE, e1.height / Pango.SCALE)

        ctx.identity_matrix()
        ctx.scale(*(1/25,)*2)
        layout = PangoCairo.create_layout(ctx)
        layout.set_font_description(self.font_description)
        layout.set_text("8",1)
        e1 = layout.get_extents()[0]
        print(e1.x / Pango.SCALE, e1.y / Pango.SCALE, e1.width / Pango.SCALE, e1.height / Pango.SCALE)


        print("-----------------------------------")


        ctx.identity_matrix()
        pango_context = PangoCairo.create_context(ctx)
        PangoCairo.context_set_resolution(pango_context, self.font_scale * 96)
        #layout = PangoCairo.create_layout(ctx)
        layout = Pango.Layout.new(pango_context)
        layout.set_font_description(self.font_description)
        layout.set_text(str(len(self.legion)), 1)
        #dimensions = get_max_device_ink_size("0123456789", PangoCairo.create_context(ctx))
        #r1 = Rectangle((0,0), dimensions)
        #r1.scale_inscribe(self.font_limits)
        #r1[1:1] = self.font_limits[1:1]
        #print(r1)
        r = layout.get_extents()[0]
        rx = r.x / Pango.SCALE
        ry = r.y / Pango.SCALE
        rw = r.width / Pango.SCALE
        rh = r.height / Pango.SCALE
        print(rx, ry, rw, rh)
        print(self.font_fg, self.font_fg / self.font_scale)
        print(self.font_limits)
        ctx.move_to(self.font_fg.location.x*135, self.font_fg.location.y*135)
        #ctx.scale(self.font_scale, self.font_scale)
        ctx.set_source_rgb(*self.font_fg_color)
        PangoCairo.show_layout(ctx, layout)

#    def _render_text(self, surface):
#        """Add legion height to a Cairo surface."""
#        if not self.show_height:
#            return
#        ctx = cairo.Context(surface)
#        ctx.set_antialias(cairo.ANTIALIAS_SUBPIXEL)
#        layout = PangoCairo.create_layout(ctx)
#        # TODO Vary font size with scale
#        desc = Pango.FontDescription("Monospace 17")
#        layout.set_font_description(desc)
#        layout.set_alignment(Pango.Alignment.CENTER)
#        size = surface.get_width()
#
#        layout.set_text(str(self.height), -1)
#        #layout.set_text("g", -1)
#        width, height = layout.get_pixel_size()
#        x = 0.65 * size
#        y = 0.55 * size
#        ctx.set_source_rgb(1, 1, 1)
#        ctx.rectangle(x, y + 0.15 * height, 0.9 * width, 0.7 * height)
#        ctx.fill()
#
#        ctx.set_source_rgb(0, 0, 0)
#        ctx.move_to(x, y)
#        PangoCairo.show_layout(ctx, layout)


if __name__ == "__main__":
    #import time
    #from slugathon.data import creaturedata
    #from slugathon.game import Creature, Player, Game, Legion

    #now = time.time()
    #creatures = [Creature.Creature(name) for name in
    #             creaturedata.starting_creature_names]
    #playername = "test"
    #game = Game.Game("g1", playername, now, now, 2, 6)
    #player = Player.Player(playername, game, 0)
    #player.color = "Red"
    #legion = Legion.Legion(player, "Rd01", creatures, 1)
    class LegionMime(object):
        def __len__(self):
            return 8
        def __init__(self):
            self.markerid = "Rd01"
    legion = LegionMime()
    marker = Marker(legion, True, scale=45)
    window = Gtk.Window()
    window.connect("destroy", Gtk.main_quit)
    window.add(marker)
    window.show_all()
    Gtk.main()

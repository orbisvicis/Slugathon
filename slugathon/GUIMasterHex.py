#!/usr/bin/env python

import gtk
import math
import pango
import guiutils
import colors

SQRT3 = math.sqrt(3.0)
RAD_TO_DEG = 180. / math.pi

# Where to place the label, by hexside.  Derived experimentally.
x_font_position = [0.5, 0.75, 0.75, 0.5, 0.25, 0.25]
y_font_position = [0.1, 0.125, 0.875, 0.95, 0.875, 0.125]

class GUIMasterHex:

    def __init__(self, hex, guiboard):
        self.hex = hex
        self.guiboard = guiboard
        scale = self.guiboard.scale
        self.cx = hex.x * 4 * scale
        self.cy = hex.y * 4 * SQRT3 * scale
        if not hex.inverted:
            self.cy += SQRT3 * scale
        self.fillcolor = guiutils.RgbToGtk(colors.RgbColors[
                colors.terrainColors[self.hex.terrain]])
        self.center = (self.cx + 3 * scale, self.cy + 1.5 * SQRT3 * scale)

        self.initVertexes()
        self.initGates()
        self.initOverlay()


    def initVertexes(self):
        """Setup the hex vertexes.

           Each vertex is the midpoint between the vertexes of the two
           bordering hexes.
        """
        self.vertexes = []
        for i in range(6):
            self.vertexes.append(None)
        cx = self.cx
        cy = self.cy
        scale = self.guiboard.scale
        if self.hex.inverted:
            self.vertexes[0] = (cx + scale, cy)
            self.vertexes[1] = (cx + 5 * scale, cy)
            self.vertexes[2] = (cx + 6 * scale, cy + SQRT3 * scale)
            self.vertexes[3] = (cx + 4 * scale, cy + 3 * SQRT3 * scale)
            self.vertexes[4] = (cx + 2 * scale, cy + 3 * SQRT3 * scale)
            self.vertexes[5] = (cx, cy + SQRT3 * scale)
        else:
            self.vertexes[0] = (cx + 2 * scale, cy)
            self.vertexes[1] = (cx + 4 * scale, cy)
            self.vertexes[2] = (cx + 6 * scale, cy + 2 * SQRT3 * scale)
            self.vertexes[3] = (cx + 5 * scale, cy + 3 * SQRT3 * scale)
            self.vertexes[4] = (cx + scale, cy + 3 * SQRT3 * scale)
            self.vertexes[5] = (cx, cy + 2 * SQRT3 * scale)

    def drawHexagon(self, gc, style):
        """Create the polygon, filled with the terrain color."""
        colormap = self.guiboard.area.get_colormap()
        fg = colormap.alloc_color(*self.fillcolor)
        gc.foreground = fg
        self.guiboard.area.window.draw_polygon(gc, True, self.allPoints)

        # outline
        colormap = self.guiboard.area.get_colormap()
        fg = colormap.alloc_color('white')
        gc.foreground = fg
        self.guiboard.area.window.draw_polygon(gc, False, self.allPoints)



    def initGates(self):
        """Setup the entrance and exit gates.

           There are up to 3 gates to draw on a hexside.  Each is 1/6
           of a hexside square.  The first is positioned from 1/6 to 1/3
           of the way along the hexside, the second from 5/12 to 7/12, and
           the third from 2/3 to 5/6.  The inner edge of each is on the
           hexside, and the outer edge is 1/12 of a hexside outside.

           Since exits extend into adjacent hexes, they can be overdrawn,
           so we need to draw both exits and entrances for both hexes.
        """
        hex = self.hex
        vertexes = self.vertexes
        self.allPoints = []
        for i in range(6):
            gp = [vertexes[i]]
            n = (i + 1) % 6
            if hex.exits[i] != None:
                li = self.initGate(vertexes[i][0], vertexes[i][1],
                          vertexes[n][0], vertexes[n][1], hex.exits[i])
                gp.extend(li)
            if hex.entrances[i] != None:
                li = self.initGate(vertexes[n][0], vertexes[n][1],
                          vertexes[i][0], vertexes[i][1], hex.entrances[i])
                li.reverse()
                gp.extend(li)
            self.allPoints.extend(gp)

    def initGate(self, vx1, vy1, vx2, vy2, gateType):
        """Setup gate on one entrance / exit hexside."""
        x0 = vx1 + (vx2 - vx1) / 6.
        y0 = vy1 + (vy2 - vy1) / 6.
        x1 = vx1 + (vx2 - vx1) / 3.
        y1 = vy1 + (vy2 - vy1) / 3.
        theta = math.atan2(vy2 - vy1, vx2 - vx1)
        #third = self.guiboard.scale / 3.
        third = self.guiboard.scale / 1.75

        if gateType == 'BLOCK':
            return initBlock(x0, y0, x1, y1, theta, third)
        elif gateType == 'ARCH':
            return initArch(x0, y0, x1, y1, theta, third)
        elif gateType == 'ARROW':
            return initArrow(x0, y0, x1, y1, theta, third)
        elif gateType == 'ARROWS':
            return initArrows(vx1, vy1, vx2, vy2, theta, third)



    def initOverlay(self):
        """Setup the overlay with terrain name and image."""
        scale = self.guiboard.scale
        self.bboxsize = (6 * scale, int(3 * SQRT3 * scale))

        myboxsize = [0.85 * mag for mag in self.bboxsize]
        self.dest_x = self.center[0] - myboxsize[0] / 2
        self.dest_y = self.center[1] - myboxsize[1] / 2

        image_filename = guiutils.IMAGE_DIR + self.hex.overlay_filename
        pixbuf = gtk.gdk.pixbuf_new_from_file(image_filename)
        self.pixbuf = pixbuf.scale_simple(myboxsize[0], myboxsize[1],
                                          gtk.gdk.INTERP_BILINEAR)


    def drawOverlay(self, gc, style):
        self.pixbuf.render_to_drawable(self.guiboard.area.window, gc,
                0, 0, self.dest_x, self.dest_y,
                -1, -1,
                gtk.gdk.RGB_DITHER_NORMAL, 0, 0)


    def drawLabel(self, gc, style):
        """Display the hex label."""
        # TODO Font size should vary with scale and actual width of font.
        self.guiboard.area.modify_font(pango.FontDescription('monospace 8'))
        # TODO Fix deprecation warning.
        font = style.get_font()
        label = str(self.hex.label)
        half_text_width = 0.5 * font.string_width(label)
        half_text_height = 0.5 * font.string_height(label)
        side = self.hex.label_side

        x = (self.cx + self.bboxsize[0] * x_font_position[side] -
                half_text_width)
        y = (self.cy + self.bboxsize[1] * y_font_position[side] +
                half_text_height)

        colormap = self.guiboard.area.get_colormap()
        fg = colormap.alloc_color('black')
        gc.foreground = fg

        self.guiboard.area.window.draw_text(font, gc, x, y, label)


    def update(self, gc, style):
        self.drawHexagon(gc, style)
        self.drawOverlay(gc, style)
        self.drawLabel(gc, style)


def initBlock(x0, y0, x1, y1, theta, third):
    xy = []
    xy.append((x0, y0))
    xy.append((x0 + third * math.sin(theta), y0 - third * math.cos(theta)))
    xy.append((x1 + third * math.sin(theta), y1 - third * math.cos(theta)))
    xy.append((x1, y1))
    return xy


def initArch(x0, y0, x1, y1, theta, third):
    sixth = third / 2.0
    p0 = ((x0 + sixth * math.sin(theta), y0 - sixth * math.cos(theta)))
    p1 = ((x1 + sixth * math.sin(theta), y1 - sixth * math.cos(theta)))

    xy = []

    xy.append((x0, y0))
    xy.append(p0)

    arcpoints = guiutils.get_semicircle_points(p0[0], p0[1], p1[0], p1[1], 10)
    xy.extend(arcpoints)

    xy.append(p1)
    xy.append((x1, y1))

    return xy

def initArrow(x0, y0, x1, y1, theta, third):
    xy = []
    xy.append((x0, y0))
    xy.append(((x0 + x1) / 2. + third * math.sin(theta),
               (y0 + y1) / 2. - third * math.cos(theta)))
    xy.append((x1, y1))
    return xy


def initArrows(vx1, vy1, vx2, vy2, theta, third):
    xy = []
    for i in range(3):
        x0 = vx1 + (vx2 - vx1) * (2 + 3 * i) / 12.
        y0 = vy1 + (vy2 - vy1) * (2 + 3 * i) / 12.
        x1 = vx1 + (vx2 - vx1) * (4 + 3 * i) / 12.
        y1 = vy1 + (vy2 - vy1) * (4 + 3 * i) / 12.
        xy.extend(initArrow(x0, y0, x1, y1, theta, third))
    return xy

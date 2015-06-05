"""\
Sprite module. Imported conditionally by the visualization module if import of
Visual succeeds.

@author: Aaron Mavrinac
@organization: University of Windsor
@contact: mavrin1@uwindsor.ca
@license: GPL-3
"""
from sys import platform as _platform
if _platform == "darwin" or _platform == "win32":
    import visual
    VIS_LIB = True
    vis_type = visual.frame
elif _platform == "linux" or _platform == "linux2":
    import pyglet
    VIS_LIB = False
    vis_type = pyglet.sprite.Sprite
    emissive_material = {'GL_EMISSION': 0.5}


class Sprite(vis_type):
    """\
    Sprite class.

    A L{Sprite} object is a frame bound to a single Visual display containing
    one or more primitives. Normally, this is used by the L{Visualizable} class
    to handle manifestations across multiple displays, but it can also be
    instantiated directly to produce visualization elements in one particular
    display.
    """
    def __init__(self, primitives, parent=None, frame=None):
        """\
        Constructor.

        @param primitives: A formatted list of visual primitives. Each element
                           of the list is a dictionary; C{type} keys the Visual
                           object class, and the remainder of the keys are
                           passed as keyword arguments to its constructor.
                           Materials and textures are dereferenced from strings
                           if necessary.
        @type primitives: C{list} of C{dict}
        @param parent: The parent object of this sprite.
        @type parent: C{object}
        @param frame: The parent frame for the sprite.
        @type frame: C{visual.frame}
        """
        if VIS_LIB:
            super(Sprite, self).__init__(frame=frame)
        else:
            super(Sprite, self).__init__(group=frame)
        self.primitives = primitives
        self.members = []
        for primitive in self.primitives:
            if 'material' in primitive \
            and isinstance(primitive['material'], str):
                primitive['material'] = \
                    getattr(visual.materials, primitive['material'])
            elif 'texture' in primitive \
            and isinstance(primitive['texture'], str):
                primitive['material'] = visual.materials.texture(data=\
                    visual.materials.loadTGA(primitive['texture']),
                    mapping=primitive['mapping'])
            self.members.append(getattr(visual, primitive['type'])(**primitive))
            self.members[-1].frame = self
        self._opacity = 1.0
        self._highlighted = False
        self.parent = parent

    def __del__(self):
        self.destroy()

    def destroy(self):
        """\
        Remove all internal implicit and explicit references to Visual objects.
        """
        try:
            self.visible = False
            del self.members
        except AttributeError:
            pass
        try:
            del self.parent
        except AttributeError:
            pass

    def get_visible(self):
        """\
        Sprite visibility.
        """
        return super(Sprite, self).get_visible()

    def set_visible(self, value):
        """\
        Set sprite visibility.
        """
        # Explicitly set child visibility for memory management.
        for member in self.members:
            member.visible = value
        super(Sprite, self).set_visible(value)

    visible = property(get_visible, set_visible)

    def get_opacity(self):
        """\
        Sprite opacity.
        """
        return self._opacity

    def set_opacity(self, value):
        """\
        Set the opacity of this sprite.

        @param value: The value to which to set the opacity in [0, 1].
        @type value: C{float}
        """
        for i, member in enumerate(self.members):
            try:
                try:
                    member.opacity = self.primitives[i]['opacity'] * value
                except KeyError:
                    member.opacity = value
            except RuntimeError:
                pass
        self._opacity = value

    opacity = property(get_opacity, set_opacity)

    def highlight(self, color=(0, 1, 0)):
        """\
        Highlight this sprite with a bright uniform color.

        @param color: The color of the highlight.
        @type color: C{tuple}
        """
        for i, member in enumerate(self.members):
            if not self._highlighted:
                if isinstance(member.color, tuple):
                    self.primitives[i]['color'] = tuple(member.color)
                else:
                    self.primitives[i]['color'] = tuple(member.color[0])
                self.primitives[i]['material'] = member.material
                member.material = visual.materials.emissive
            member.color = color
        self._highlighted = True

    def unhighlight(self):
        """\
        Unhighlight this sprite (if highlighted).
        """
        if not self._highlighted:
            return
        for i, member in enumerate(self.members):
            member.color = self.primitives[i]['color']
            member.material = self.primitives[i]['material']
        self._highlighted = False

    def transform(self, pose):
        """\
        Execute a 3D transformation on this sprite. This sets the absolute pose
        of the sprite to the specified pose.

        @param pose: The pose.
        @type pose: L{Pose}
        """
        self.pos = tuple(pose.T)
        self.axis = (1, 0, 0)
        self.up = (1, 0, 0)
        angle, axis = pose.R.to_axis_angle()
        self.rotate(axis=tuple(axis), angle=angle)

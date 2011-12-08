"""\
Robot module.

@author: Aaron Mavrinac
@organization: University of Windsor
@contact: mavrin1@uwindsor.ca
@license: GPL-3
"""

from math import pi

from .geometry import Point, Rotation, Pose
from .posable import SceneObject


class RobotPiece(SceneObject):
    """\
    Robot piece class.

    A L{RobotPiece} is a rigid unit of a robot between two joints. It adds some
    functionality related to its robot parent.
    """
    def __init__(self, name, parent, pose=Pose(), mount_pose=Pose(), mount=None,
                 primitives=[], triangles=[]):
        super(RobotPiece, self).__init__(name, pose=pose, mount_pose=mount_pose,
              mount=mount, primitives=primitives, triangles=triangles)
        self.parent = parent

    def visualize(self):
        """\
        Override the parent setting for the sprites generated by a robot piece
        to the robot itself.
        """
        super(RobotPiece, self).visualize()
        for display in self.displays:
            self.actuals[display].parent = self.parent


class Robot(SceneObject):
    """\
    Sprite-based robot class.

    A L{Robot} object is a composite L{SceneObject}. Externally, it mimics the
    basic L{SceneObject} interface. Internally, it is composed of a number of
    sub-objects called "pieces" mounted sequentially; the overall pose affects
    the base (first piece), and the mount pose is taken from the end effector
    (last piece). The configuration of the pieces is dictated by each piece's
    pose and mount pose, which are essentially joints and offsets of forward
    kinematics, although the poses are arbitrary. The joint configuration
    string induces a set of such poses based on its definition (a range of
    possible joint values and whether the joint is revolute or prismatic).
    """
    def __init__(self, name, pose=Pose(), mount=None, pieces=[], config=None,
                 occlusion=True):
        super(Robot, self).__init__(name, pose=pose, mount=mount)
        self.pieces = []
        nextpose = pose
        for i, piece in enumerate(pieces):
            offset = piece['offset']
            try:
                mount = self.pieces[i - 1]
            except IndexError:
                mount = self.mount
            try:
                assert occlusion
                triangles = piece['triangles']
            except (AssertionError, KeyError):
                triangles = []
            try:
                primitives = piece['primitives']
            except KeyError:
                primitives = []
            self.pieces.append(RobotPiece('%s-%i' % (name, i), self,
                pose=nextpose, mount_pose=offset, mount=mount,
                primitives=primitives, triangles=triangles))
            nextpose = self.generate_joint_pose(piece['joint'])
        self.joints = [piece['joint'] for piece in pieces]
        self._config = [joint['home'] for joint in self.joints]
        if config:
            self.config = config
        self._visible = False

    @property
    def config(self):
        """\
        The configuration of this robot.

        @rtype: C{list} of C{float}
        """
        return self._config

    @config.setter
    def config(self, value):
        if not len(value) == len(self.pieces):
            raise ValueError('incorrect configuration length')
        for i, position in enumerate(value):
            try:
                self.pieces[i + 1].set_relative_pose(self.generate_joint_pose(\
                    self.joints[i], position))
            except IndexError:
                self._mount_pose = \
                    self.generate_joint_pose(self.joints[i], position)
            self._config[i] = position
        self._pose_changed_hook()

    @property
    def visible(self):
        """\
        Visibility of this robot.
        """
        return self._visible

    @visible.setter
    def visible(self, value):
        self._visible = value
        for piece in self.pieces:
            piece.visible = value

    def highlight(self, color=(0, 1, 0)):
        """\
        Highlight this robot with a bright uniform color.

        @param color: The color of the highlight.
        @type color: C{tuple}
        """
        for piece in self.pieces:
            piece.highlight(color)

    def unhighlight(self):
        """\
        Unhighlight this robot (if highlighted).
        """
        for piece in self.pieces:
            piece.unhighlight()

    def mount_pose(self):
        """\
        Return the overall pose transformation to the end effector.

        @return: The overall end effector pose.
        @rtype: L{Pose}
        """
        return self.pieces[-1].mount_pose()

    @property
    def pose(self):
        """\
        The pose of the robot.
        """
        return self.pieces[0].pose

    def set_absolute_pose(self, pose):
        """\
        Set the absolute (world frame) pose of the robot.

        @param pose: The absolute pose to set.
        @type pose: L{Pose}
        """
        self.pieces[0].set_absolute_pose(pose)
        super(Robot, self).set_absolute_pose(pose)

    def set_relative_pose(self, pose):
        """\
        Set the relative (mounted) pose of the robot.

        @param pose: The relative pose to set.
        @type pose: L{Pose}
        """
        self.pieces[0].set_relative_pose(pose)
        super(Robot, self).set_relative_pose(pose)

    @staticmethod
    def generate_joint_pose(joint, position=None):
        """\
        Generate the pose of the piece required to effect the forward kinematic
        transformation induced by the position value subject to joint
        properties.

        @param joint: The joint description.
        @type joint: C{dict}
        @param position: The position to set (if None, use home position).
        @type position: C{float}
        @return: The pose induced by the forward kinematic transformation.
        @rtype: L{Pose}
        """
        if position is None:
            position = joint['home']
        else:
            if position < joint['limits'][0] or position > joint['limits'][1]:
                raise ValueError('position out of joint range')
        if joint['type'] == 'revolute':
            position *= pi / 180.0
            return Pose(R=Rotation.from_axis_angle(position,
                Point(joint['axis'])))
        elif joint['type'] == 'prismatic':
            return Pose(T=(position * Point(joint['axis'])))
        else:
            raise ValueError('invalid joint type')

    @property
    def triangles(self):
        """\
        Occluding triangles.
        """
        return reduce(lambda a, b: a | b,
            [piece.triangles for piece in self.pieces])

    def visualize(self):
        """\
        Visualize this robot.
        """
        for piece in self.pieces:
            piece.visualize()
        self._visible = True

    def update_visualization(self):
        """\
        Update this robot's visualization.
        """
        for piece in self.pieces:
            piece.opacity = self.opacity
            piece.update_visualization()
        for child in self.children:
            try:
                child.update_visualization()
            except AttributeError:
                pass
        
    def toggle_triangles(self):
        """\
        Toggle display of occluding triangles in the visualization.
        """
        for piece in self.pieces:
            piece.toggle_triangles()
        self.opacity = self.pieces[0].opacity
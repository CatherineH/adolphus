"""\
Standard library of interface commands.

Commands are functions prefixed with 'cmd_' and taking two positional
arguments -- a reference to the experiment object and a list of strings
comprising the command arguments -- as well as (optionally) a 'response'
keyword argument specifying the response string format. Possible values for the
response format are:

  - C{pickle} - pickled Python object generated with C{pickle.dumps()}
  - C{csv} - comma-delimited values terminated with hash (C{#}) character
  - C{text} - human-readable text format (can include newlines)

@author: Aaron Mavrinac
@organization: University of Windsor
@contact: mavrin1@uwindsor.ca
@license: GPL-3
"""

try:
    import cPickle as pickle
except ImportError:
    import pickle

import yaml

from .geometry import Point, DirectionalPoint
from .visualization import Sprite
from .robot import Robot
from .yamlparser import YAMLParser


class CommandError(Exception):
    pass


### File Operations

def cmd_loadmodel(ex, args):
    """\
    Load a model from a YAML file.

    usage: %s filename
    """
    cmd_clear(ex, [])
    cmd_modify(ex, [])
    cmd_cameraview(ex, [])
    cmd_cameranames(ex, [])
    for sceneobject in ex.model:
        ex.model[sceneobject].visible = False
    try:
        ex.model, ex.tasks = YAMLParser(args[0]).experiment
    except IOError, e:
        raise CommandError(e)
    ex.model.visualize()
    ex.display.select()

def cmd_loadconfig(ex, args):
    """\
    Load viewer configuration from a YAML file.

    usage: %s filename
    """
    try:
        config = yaml.load(open(args[0]))
    except IOError, e:
        raise CommandError(e)
    except IndexError:
        import pkg_resources
        config = yaml.load(pkg_resources.resource_string(__name__,
            'resources/config.yaml'))
    try:
        ex.keybindings = config['keybindings']
    except KeyError:
        ex.keybindings = {}

def cmd_event(ex, args):
    """\
    Set the generic experiment event.
    """
    ex.event.set()

def cmd_exit(ex, args):
    """\
    Exit the viewer.
    """
    for display in ex.altdisplays:
        display.visible = False
    ex.display.visible = False
    ex.exit = True

### Visualization

def cmd_clear(ex, args):
    """\
    Clear all point coverage visualizations.
    """
    for key in ex.coverage.keys():
        del ex.coverage[key]

def cmd_axes(ex, args):
    """\
    Toggle display of 3D axes.
    """
    ex.axes.visible = not ex.axes.visible

def cmd_centerdot(ex, args):
    """\
    Toggle display of a center indicator dot.
    """
    ex.centerdot.visible = not ex.centerdot.visible

def cmd_setcenter(ex, args):
    """\
    Set the position of the display center.

    usage: %s x y z
    """
    if ex.display.in_camera_view:
        raise CommandError('cannot set center in camera view')
    pos = (float(args[0]), float(args[1]), float(args[2]))
    ex.display.set_center(pos)
    ex.centerdot.pos = pos

def cmd_shiftcenter(ex, args):
    """\
    Shift the display center from its current position by the amount specified.

    usage: %s x y z
    """
    if ex.display.in_camera_view:
        raise CommandError('cannot shift center in camera view')
    pos = list(ex.display.center)
    for i in range(3):
        pos[i] += float(args[i])
    ex.display.set_center(tuple(pos))
    ex.centerdot.pos = tuple(pos)

def cmd_triangles(ex, args):
    """\
    Toggle display of occluding triangles.
    """
    for sceneobject in ex.model:
        ex.model[sceneobject].toggle_triangles()

def cmd_cameranames(ex, args):
    """\
    Toggle display of camera identifiers.
    """
    ex.camera_names()

def cmd_cameraview(ex, args):
    """\
    Switch to camera view for the specified camera.
    
    usage: %s name
    """
    if len(args):
        if ex.zoom:
            raise CommandError('no camera view with external zoom enabled')
        try:
            ex.display.camera_view(ex.model[args[0]])
            ex.modifier.visible = False
            ex.modifier.parent = None
        except KeyError:
            raise CommandError('invalid camera name')
    else:
        try:
            ex.display.camera_view()
        except RuntimeError:
            pass

### Geometric

def cmd_pose(ex, args, response='pickle'):
    """\
    Return the (absolute) pose of an object. If using CSV or text response,
    a rotation format may be specified (one of 'quaternion', 'matrix',
    'axis-angle', or 'euler-zyx').
    
    usage: %s name [rformat]
    """
    try:
        pose = ex.model[args[0]].pose
        if response == 'pickle':
            return pickle.dumps(pose)
        elif response == 'csv':
            flatpose = tuple(pose.T)
            try:
                if args[1] == 'quaternion':
                    raise IndexError
                elif args[1] == 'matrix':
                    flatpose += tuple(pose.R.to_rotation_matrix().flatten())
                elif args[1] == 'axis-angle':
                    angle, axis = pose.R.to_axis_angle()
                    flatpose += (angle,) + tuple(axis)
                elif args[1] == 'euler-zyx':
                    flatpose += tuple(pose.R.to_euler_zyx())
                else:
                    raise CommandError('invalid rotation format')
            except IndexError:
                flatpose += (pose.R.Q.a,) + tuple(pose.R.Q.v)
            return ','.join([str(float(e)) for e in flatpose]) + '#'
        elif response == 'text':
            tstr = 'T: (%.2f, %.2f, %.2f)\n' % ex.model[args[0]].pose.T
            try:
                if args[1] == 'quaternion':
                    raise IndexError
                elif args[1] == 'matrix':
                    return tstr + \
                        ('R:\t%.4f\t%.4f\t%.4f\n' \
                        + '\t%.4f\t%.4f\t%.4f\n' \
                        + '\t%.4f\t%.4f\t%.4f') \
                        % tuple(pose.R.to_rotation_matrix().flatten())
                elif args[1] == 'axis-angle':
                    angle, axis = pose.R.to_axis_angle()
                    return tstr + \
                        u'R: \u03d1 = %.2f about (%.2f, %.2f, %.2f)' \
                        % ((angle,) + axis)
                elif args[1] == 'euler-zyx':
                    return tstr + \
                        u'R: \u03d1 = %.2f, \u03d5 = %.2f, \u0471 = %.2f' \
                        % pose.R.to_euler_zyx()
                else:
                    raise CommandError('invalid rotation format')
            except IndexError:
                return tstr + 'R: %s' % (pose.R.Q,)
    except KeyError:
        raise CommandError('invalid object name')

def cmd_modify(ex, args):
    """\
    Enable interactive pose modification for the specified object, or disable
    modification if no object is specified.
    
    usage: %s [name]
    """
    try:
        if len(args) and not ex.modifier.parent == ex.model[args[0]]:
                ex.modifier.pos = ex.model[args[0]].pose.T
                ex.modifier.visible = True
                ex.modifier.parent = ex.model[args[0]]
        else:
            ex.modifier.visible = False
            ex.modifier.parent = None
    except KeyError:
        raise CommandError('invalid object name')

def cmd_position(ex, args, response='pickle'):
    """\
    Set the position of the specified robot, or return its position if no new
    position is specified.

    usage: %s robot [position]
    """
    try:
        assert isinstance(ex.model[args[0]], Robot)
        if len(args) > 1:
            ex.model[args[0]].config = [float(arg) for arg in args[1:]]
            ex.model[args[0]].update_visualization()
        else:
            if response == 'pickle':
                return pickle.dumps(ex.model[args[0]].config)
            elif response == 'csv':
                return ','.join([str(e) for e in \
                    ex.model[args[0]].config]) + '#'
            elif response == 'text':
                return str(ex.model[args[0]].config)
    except AssertionError:
        raise CommandError('not a robot')
    except KeyError:
        raise CommandError('invalid robot name')

### Coverage Operations

def cmd_active(ex, args):
    """name"""
    try:
        ex.model[args[0]].active = not ex.model[args[0]].active
        ex.model[args[0]].update_visualization()
    except IndexError:
        for camera in ex.model.cameras:
            cmd_active(ex, [camera])
    except KeyError:
        raise CommandError('invalid camera name')

def cmd_strength(ex, args, response='pickle'):
    """\
    Return the coverage strength of the specified point with respect to the
    task parameters of the specified task.
    
    usage: %s task x y z [rho eta]
    """
    try:
        task = ex.tasks[args.pop(0)]
    except IndexError:
        raise CommandError('incorrect arguments')
    except KeyError:
        raise CommandError('invalid task name')
    if len(args) == 3:
        p = Point([float(args[i]) for i in range(3)])
    elif len(args) == 5:
        p = DirectionalPoint([float(args[i]) for i in range(5)])
    else:
        raise CommandError('invalid point')
    strength = ex.model.strength(p, task.params)
    if response == 'pickle':
        return pickle.dumps(strength)
    elif response == 'csv':
        return '%f#' % strength
    elif response == 'text':
        return '%f' % strength

def cmd_coverage(ex, args, response='pickle'):
    """
    Return the coverage performance for the specified task(s).

    usage: %s name*
    """
    cmd_clear(ex, [])
    try:
        ex.display.message('Calculating coverage...')
        ex.display.userspin = False
        performance = {}
        if not args:
            args = ex.tasks.keys()
        for arg in args:
            ex.coverage[arg] = ex.model.coverage(ex.tasks[arg])
            ex.coverage[arg].visualize()
            performance[arg] = ex.model.performance(ex.tasks[arg],
                coverage=ex.coverage[arg])
        if response == 'pickle':
            return pickle.dumps(performance)
        elif response == 'csv':
            return ','.join(['%s:%f' % (key, performance[key]) \
                for key in performance]) + '#'
        elif response == 'text':
            return '\n'.join(['%s: %.4f' % (key, performance[key]) \
                for key in performance])
    except KeyError:
        raise CommandError('invalid task name')
    except Exception, e:
        raise CommandError(e)
    finally:
        ex.display.userspin = True

def cmd_rangecoverage(ex, args, response='pickle'):
    """
    Return the monocular range imaging coverage performance based on laser and
    transport parameters.

    usage: %s laser target lpitch tpitch tx ty tz tstyle
    """
    cmd_clear(ex, [])
    try:
        ex.display.message('Calculating range imaging coverage...')
        ex.display.userspin = False
        taxis = Point([float(t) for t in args[4:7]])
        coverage, task = ex.model.range_coverage(args[0], args[1],
            float(args[2]), float(args[3]), taxis, args[7])
        ex.coverage['range'] = coverage
        ex.coverage['range'].visualize()
        performance = ex.model.performance(task, coverage=coverage)
        if response == 'pickle':
            return pickle.dumps(performance)
        elif response == 'csv':
            return 'range:%f#' % performance
        elif response == 'text':
            return 'range: %.4f' % performance
    except AttributeError:
        raise CommandError('not a range model')
    except IndexError:
        raise CommandError('incorrect arguments')
    except KeyError:
        raise CommandError('invalid laser or target name')
    except Exception, e:
        raise CommandError(e)
    finally:
        ex.display.userspin = True

def cmd_showval(ex, args):
    """
    Display a value in [0, 1] in 'bar graph' style next to the specified camera,
    or remove the display if no value is specified.
    
    usage: %s name [value]
    """
    if args[0] in ex.valvis:
        ex.valvis[args[0]].visible = False
        del ex.valvis[args[0]]
    try:
        value = float(args[1])
        ex.valvis[args[0]] = Sprite([{'type': 'cylinder',
            'color': (0.8, 0.8, 0.8), 'pos': (80, -30, 0), 'axis': (0,
            (1.0 - value) * 60, 0), 'radius': 6}, {'type': 'cylinder',
            'color': (1, 0, 0), 'pos': (80, -30 + (1.0 - value) * 60.0,
            0), 'axis': (0, value * 60.0, 0), 'radius': 6}])
        try:
            ex.valvis[args[0]].frame = ex.model[args[0]].actuals['main']
        except KeyError:
            raise CommandError('invalid camera name')
    except IndexError:
        pass

### Information

def cmd_objecthierarchy(ex, args, response='pickle'):
    """\
    Return a scene object hierarchy in the form C{{'object': (parent, type)}}.

    usage: %s
    """
    if response != 'pickle':
        raise CommandError('command cannot return %s response' % response)
    hierarchy = {}
    for so in ex.model:
        try:
            hierarchy[so] = (ex.model[so].mount.name,
                ex.model[so].__class__.__name__)
        except AttributeError:
            hierarchy[so] = (None, ex.model[so].__class__.__name__)
    for task in ex.tasks:
        try:
            hierarchy[task] = (ex.tasks[task].mount.name,
                ex.tasks[task].__class__.__name__)
        except AttributeError:
            hierarchy[task] = (None, ex.tasks[task].__class__.__name__)
    return pickle.dumps(hierarchy)

def cmd_select(ex, args):
    """\
    Select a scene object.

    usage: %s [object]
    """
    if not args:
        ex.select()
    else:
        try:
            ex.select(ex.model[args[0]])
        except KeyError:
            raise CommandError('invalid object')

### Debug

def cmd_eval(ex, args):
    """\
    Execute arbitrary code.
    
    usage: %s code
    """
    return str(eval(' '.join(args)))

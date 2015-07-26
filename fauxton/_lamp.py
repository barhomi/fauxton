from os.path import dirname
from shutil import rmtree

try: from cv2 import IMREAD_UNCHANGED, imread
except ImportError: imread = None

from numpy import (array, arccos, arctan2, cos, cross, dot, hstack, load, pi,
                   sin, square, sqrt)

from _core import BlenderModule
from _scene import Prop

__name__ = 'fauxton'
__all__ = ['Lamp']

#===============================================================================
# Private Symbols
#===============================================================================

bl_lamp = BlenderModule('''
    from contextlib import contextmanager
    from os.path import join
    from numpy import array, reshape, save

    def create(type_):
        lamp = bpy.data.objects.new('', bpy.data.lamps.new(''))
        lamp['__type__'] = type_
        return lamp

    def get_color(lamp):
        return lamp.color

    def set_color(lamp, color):
        lamp['color'] = color

    def get_source(lamp):
        return lamp.get('source', None)

  ''')

#===============================================================================
# Public Symbols
#===============================================================================

class Lamp(Prop):
    '''
    A prop that can take snapshots of its surroundings.

    :param dict \**properties: Initial values of instance variables.

    :var numpy.ndarray field_of_view: *y* and *x* viewing angles, in radians.
    :var numpy.ndarray resolution: *y* and *x* resolution, in pixels.
    :var str source: OSL source to use as an emissive material when rendering.
    :var str render_pass: Blender render pass to use (e.g. "z" or "color").
    :var str render_engine: Blender render engine to use (e.g. "CYCLES").
    '''
    resource_type = 'LAMP'

    def __new__(cls, **properties):
        result = bl_lamp.create(cls.resource_type)
        [setattr(result, k, v) for k, v in properties.items()]
        return result

    @property
    def source(self):
        return bl_lamp.get_source(self)

    @property
    def get_color(self):
        return array(bl_lamp.get_color(self))

    @property.setter
    def set_color(self, color):
        return bl_lamp.set_color(self, color)

    @source.setter
    def source(self, source):
        bl_lamp.set_source(self, source)


from numpy import array
from _core import BlenderModule, BlenderResource

__name__ = 'fauxton'
__all__ = ['Action', 'Prop', 'Scene', 'read_scene', 'write_scene']

#===============================================================================
# Private Symbols
#===============================================================================

bl_prop = BlenderModule('''
    def create(type_, data):
        prop = bpy.data.objects.new('', data)
        prop['__type__'] = type_
        return prop

    def get_position(prop):
        return list(prop.location)

    def get_color(prop):
        return list(prop.color)

    def set_color(prop, color):
        prop.color = color

    def set_position(prop, position):
        prop.location = position

    def get_rotation(prop):
        prop.rotation_mode = 'QUATERNION'
        return list(prop.rotation_quaternion)

    def set_rotation(prop, rotation):
        prop.rotation_mode = 'QUATERNION'
        prop.rotation_quaternion = rotation

    def get_scale(prop):
        return list(prop.scale)

    def set_scale(prop, scale):
        prop.scale = scale

    def get_action(prop):
        prop.rotation_mode = 'QUATERNION'
        return prop.animation_data.action if prop.animation_data else None

    def set_action(prop, action):
        if prop.animation_data is None:
            prop.animation_data_create()
        prop.rotation_mode = 'QUATERNION'
        prop.animation_data.action = action
  ''')

bl_action = BlenderModule('''
    def create(type_):
        action = bpy.data.actions.new('')
        action['__type__'] = type_
        return action

    def get_position(action):
        return action.get('position', [])

    def set_position(action, position):
        action['position'] = position
        for curve in list(action.fcurves):
            if curve.data_path == 'location':
                action.fcurves.remove(curve)
        for i in range(3):
            curve = action.fcurves.new('location', i)
            curve.keyframe_points.add(len(position))
            for j, point in enumerate(position):
                curve.keyframe_points[j].co = point[0], point[1 + i]
                curve.keyframe_points[j].interpolation = 'LINEAR'

    def get_rotation(action):
        return action.get('rotation', [])

    def set_rotation(action, rotation, interpolation = 'LINEAR'):
        action['rotation'] = rotation
        for curve in list(action.fcurves):
            if curve.data_path == 'rotation_quaternion':
                action.fcurves.remove(curve)
        for i in range(4): # for each rotation dimension (quaternion wxyz)
            curve = action.fcurves.new('rotation_quaternion', i) #
            curve.keyframe_points.add(len(rotation)) # add a number of keypoints frames
            for j, point in enumerate(rotation):
                curve.keyframe_points[j].co = point[0], point[1 + i] # (frame_index, quaternion[i])
                curve.keyframe_points[j].interpolation = interpolation

    def get_scale(action):
        return action.get('scale', [])

    def set_scale(action, scale):
        action['scale'] = scale
        for curve in list(action.fcurves):
            if curve.data_path == 'scale':
                action.fcurves.remove(curve)
        for i in range(3):
            curve = action.fcurves.new('scale', i)
            curve.keyframe_points.add(len(scale))
            for j, point in enumerate(scale):
                curve.keyframe_points[j].co = point[0], point[1 + i]
                curve.keyframe_points[j].interpolation = 'LINEAR'
  ''')

bl_scene = BlenderModule('''
    from random import randint

    def create(type_):
        scene = bpy.data.scenes.new('')
        scene.world = bpy.data.worlds.new('')
        scene.world.horizon_color = (0, 0, 0)
        scene['__type__'] = type_
        scene['global_names'] = {}
        scene['local_names'] = {}
        return scene

    def get_size(scene):
        return len(scene.objects)

    def get_prop_names(scene):
        return scene['global_names'].keys()

    def contains(scene, name):
        return name in scene['global_names']

    def get_by_name(scene, name):
        global_name = scene['global_names'][name]
        return bpy.data.objects[global_name]

    def set_by_name(scene, name, prop):
        if contains(scene, name):
            scene.objects.unlink(get_by_name(scene, name))
        scene.objects.link(prop)
        scene['global_names'][name] = prop.name
        scene['local_names'][prop.name] = name

    def remove_by_name(scene, name):
        prop = get_by_name(scene, name)
        scene.objects.unlink(prop)
        del scene['global_names'][name]
        del scene['local_names'][prop.name]

    def add(scene, prop):
        def unused_name():
            name = str(randint(0, 2*32))
            return name if name not in scene['global_names'] else unused_name()
        set_by_name(scene, unused_name(), prop)
        return prop

    def remove(scene, prop):
        remove_by_key(scene['local_names'][prop])
        return prop

    def get_time(scene):
        return scene.frame_current

    def set_time(scene, time):
        scene.frame_current = time

    def read(path):
        with bpy.data.libraries.load(path) as (src, dst):
            local_names = list(src.objects)
            dst.scenes = [src.scenes[0]]
            dst.objects = src.objects
        scene = dst.scenes[0]
        global_names = [o.name for o in dst.objects]
        scene['global_names'] = dict(zip(local_names, global_names))
        scene['local_names'] = dict(zip(global_names, local_names))
        return scene

    def write(path, scene):
        conflicting_scene = bpy.data.scenes.get('0', None)
        if conflicting_scene: conflicting_scene.name = ''
        old_scene_name = scene.name
        scene.name = '0'

        removed_objects = {}
        for s in bpy.data.scenes[1:]:
            removed_objects[s.name] = list(s.objects)
            [s.objects.unlink(o) for o in s.objects]

        old_object_names = {o: o.name for o in bpy.data.objects}
        for global_name, local_name in scene['local_names'].items():
            bpy.data.objects[global_name].name = local_name

        bpy.ops.wm.save_as_mainfile(filepath=path)

        for o, name in old_object_names.items():
            o.name = name

        for s in bpy.data.scenes[1:]:
            [s.objects.link(o) for o in removed_objects[s.name]]

        if conflicting_scene: conflicting_scene.name = '0'
        scene.name = old_scene_name

    #------------------------------------------------------------------------------#
    def add_ground(scene, texture_fname):

        import os
        # create plane
        bpy.ops.mesh.primitive_plane_add(location=(0,0,0))
        plane = bpy.context.object

        mat = bpy.data.materials.new('mat')
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        n_imt = nodes.new('ShaderNodeTexImage')
        add_material_to_object(plane, mat)

        links = mat.node_tree.links
        n_db = nodes[1] # Diffuse BSDF
        n_mo = nodes[0] # Material Output
        links.new(n_imt.outputs[0], n_db.inputs[0])
        links.new(n_mo.inputs[0], n_db.outputs[0])
        tex_fname = os.path.expanduser(texture_fname)
        n_imt.image = bpy.data.images.load(tex_fname)
        bpy.ops.uv.smart_project()
        scene.objects.link(plane)

    #------------------------------------------------------------------------------#
    def add_material_to_object(ob, mat):
        try:
            while True:
                ob.data.materials.pop()
        except:
            ob.data.materials.append(mat)

        return ob

    #------------------------------------------------------------------------------#
    def add_light(scene, light_path, color = [1,1,1, 1], light_intensity = 10):

        import bpy
        import os
        from math import pi

        with bpy.data.libraries.load(light_path) as (data_from, data_to):
            data_to.materials = data_from.materials

        bpy.ops.object.camera_add(location = (3.9427, -2.73999, 3.79962), rotation = (pi/3, 0, pi/3))

        #############################
        bpy.ops.mesh.primitive_plane_add(radius = 10)
        pl1 = bpy.context.object
        pl1.location[0] = 17.64783
        pl1.location[1] = 11.18092
        pl1.location[2] = 8.22011
        pl1.rotation_euler[1] = pi/2.84
        pl1.rotation_euler[2] = pi/4.98
        bpy.context.object.cycles_visibility.camera = False

        # changing the light color and intensity
        mat = bpy.data.materials["key_light"]
        mat.node_tree.nodes[1].inputs[0].default_value = color
        mat.node_tree.nodes[1].inputs[1].default_value = light_intensity
        add_material_to_object(pl1, mat)

        pl1.parent = bpy.data.objects['Camera']
        pl1.matrix_parent_inverse = bpy.data.objects['Camera'].matrix_world.inverted()
        scene.objects.link(pl1)

        ################################
        bpy.ops.mesh.primitive_plane_add(radius = 10)
        pl2 = bpy.context.object
        pl2.location[0] = 5.35114
        pl2.location[1] = -20.50936
        pl2.location[2] = 13.60414
        pl2.rotation_euler[1] = pi/2.84
        pl2.rotation_euler[2] = -pi/2.53
        bpy.context.object.cycles_visibility.camera = False

        # changing the light color and intensity
        mat = bpy.data.materials["filling_light"]
        mat.node_tree.nodes[1].inputs[0].default_value = color
        mat.node_tree.nodes[1].inputs[1].default_value = light_intensity
        add_material_to_object(pl2, mat)

        pl2.data.materials.append(mat)
        pl2.parent = bpy.data.objects['Camera']
        pl2.matrix_parent_inverse = bpy.data.objects['Camera'].matrix_world.inverted()
        scene.objects.link(pl2)

        ################################
        bpy.ops.mesh.primitive_plane_add(radius = 10)
        pl3 = bpy.context.object
        pl3.location[0] = -22.28899
        pl3.location[1] = 2.22551
        pl3.location[2] = 11.02445
        pl3.rotation_euler[1] = pi/1.69
        pl3.rotation_euler[2] = -pi/9.81
        bpy.context.object.cycles_visibility.camera = False

        mat = bpy.data.materials["rim_light"]
        mat.node_tree.nodes[1].inputs[0].default_value = color
        mat.node_tree.nodes[1].inputs[1].default_value = light_intensity
        add_material_to_object(pl3, mat)

        pl3.data.materials.append(mat)
        pl3.parent = bpy.data.objects['Camera']
        pl3.matrix_parent_inverse = bpy.data.objects['Camera'].matrix_world.inverted()
        scene.objects.link(pl3)

  ''')

#===============================================================================
# Public Symbols
#===============================================================================

class Prop(BlenderResource):
    '''
    A graphical object that can be added to a ``Scene``.

    :param BlenderResource data: Resource to wrap.
    :param dict \**properties: Initial values of instance variables.

    :var numpy.ndarray position: 3D spatial location.
    :var numpy.ndarray rotation: 4D rotation quaternion.
    :var numpy.ndarray scale: 3D scale--1 component for each object-space axis.
    :var tuple pose: `(position, rotation, scale)`.
    :var Action action: Animation currently being performed.
    '''
    resource_type = 'Object'

    def __new__(cls, data=None, **properties):
        result = bl_prop.create(cls.resource_type, data)
        [setattr(result, k, v) for k, v in properties.items()]
        return result

    @property
    def position(self):
        return array(bl_prop.get_position(self))

    @position.setter
    def position(self, position):
        bl_prop.set_position(self, list(map(float, position)))

    @property
    def color(self):
        return array(bl_prop.get_color(self))

    @color.setter
    def color(self, color):
        bl_prop.set_color(self,list(map(float, color)))

    @property
    def rotation(self):
        return array(bl_prop.get_rotation(self))

    @rotation.setter
    def rotation(self, rotation):
        bl_prop.set_rotation(self, list(map(float, rotation)))

    @property
    def scale(self):
        return array(bl_prop.get_scale(self))

    @scale.setter
    def scale(self, scale):
        bl_prop.set_scale(self, list(map(float, scale)))

    @property
    def pose(self):
        return self.position, self.rotation, self.scale

    @pose.setter
    def pose(self, pose):
        self.position, self.rotation, self.scale = pose

    @property
    def action(self):
        return bl_prop.get_action(self)

    @action.setter
    def action(self, action):
        if not isinstance(action, Action):
            action = Action(action)
        bl_prop.set_action(self, action)

class Action(BlenderResource):
    '''
    A keyframe-based animation that can be applied to a ``Prop``.

    :param dict \**properties: Initial values of instance variables.

    :var numpy.ndarray position: Sequence of (t, x, y, z) keypoints.
    :var numpy.ndarray rotation: Sequence of (t, w, x, y, z) keypoints.
    :var numpy.ndarray scale: Sequence of (t, x, y, z) keypoints.
    '''
    resource_type = 'Action'

    def __new__(cls, **properties):
        result = bl_action.create(cls.resource_type)
        [setattr(result, k, v) for k, v in properties.items()]
        return result

    @property
    def position(self):
        return array(bl_action.get_position(self), 'f')

    @position.setter
    def position(self, position):
        bl_action.set_position(self, [list(map(float, e)) for e in position])

    @property
    def rotation(self):
        return array(bl_action.get_rotation(self), 'f')

    @rotation.setter
    def rotation(self, rotation, interpolation = 'LINEAR'):
        bl_action.set_rotation(self, [list(map(float, e)) for e in rotation], interpolation)

    @property
    def scale(self):
        return array(bl_action.get_scale(self), 'f')

    @scale.setter
    def scale(self, scale):
        bl_action.set_scale(self, [list(map(float, e)) for e in scale])

class Scene(BlenderResource):
    '''
    A collection of graphical objects.

    :param dict \**properties: Initial values of instance variables.

    Operations defined on a `Scene` `s`:
        ========== =============================================================
        `len(s)`   Return the number of props in `s`.
        `iter(s)`  Return an iterator over the names of props in `s`.
        `n in s`   Return whether a prop is stored in `s` under the name `n`.
        `s[n]`     Return the prop stored in `s` under the name `n`.
        `s[n] = p` Add the prop `p` to `s`, storing it under the name `n`.
        `del s[n]` Remove the prop stored under the name `n` from `s`.
        ========== =============================================================
    '''
    resource_type = 'Scene'

    def __new__(cls, **properties):
        result = bl_scene.create(cls.resource_type)
        [setattr(result, k, v) for k, v in properties.items()]
        return result

    def __len__(self):
        return bl_scene.get_size(self)

    def __iter__(self):
        return iter(bl_scene.get_prop_names(self))

    def __contains__(self, name):
        return bl_scene.contains(self, name)

    def __getitem__(self, name):
        return bl_scene.get_by_name(self, name)

    def __setitem__(self, name, prop):
        bl_scene.set_by_name(self, name, prop)

    def __delitem__(self, name):
        bl_scene.remove_by_name(self, name)

    @property
    def time(self):
        return bl_scene.get_time(self)

    @time.setter
    def time(self, time):
        bl_scene.set_time(self, float(time))

    def add(self, prop):
        '''
        Generate a name for a prop, add it to the scene, then return it.

        :param Prop prop: Prop to add.
        :rtype: Prop
        '''
        return bl_scene.add(self, prop)

    def remove(self, prop):
        '''
        Remove a prop from the scene, then return it.

        :param Prop prop: Prop to remove.
        :rtype: Prop
        '''
        return bl_scene.remove(self, prop)

    def add_ground(self, texture_fname):
        '''
        add a ground plane on which a texture file is applied

        '''
        return bl_scene.add_ground(self, texture_fname)


    def add_light(self, lighting_file, color, light_intensity):
        '''
        add 3 sources of light to the scene

        '''
        return bl_scene.add_light(self, lighting_file, color, light_intensity)


def read_scene(path):
    '''
    Read a scene from a ".blend" file into memory.

    :param str path: Location on the filesystem.
    :rtype: Scene
    '''
    return bl_scene.read(path)

def write_scene(path, scene):
    '''
    Write a scene in memory to a ".blend" file.

    :param str path: Location on the filesystem.
    :param Scene scene: Scene to write.
    '''
    bl_scene.write(path, scene)

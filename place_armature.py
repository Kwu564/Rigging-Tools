from unittest import skip
import bpy
import math
import bmesh
from mathutils import Vector
from collections import Counter
from collections import OrderedDict

import mathutils

# BONE TOOLS
#########################################################################################################################################################

# Naming

def add_suffix(context, suffix):
    obj = context.object
    if obj.type == "ARMATURE":
        selected_bones = context.selected_editable_bones
        for bone in selected_bones:
            bone.name = bone.name + suffix

def replace_string(context, suffix, replace_string):
    obj = context.object
    if obj.type == "ARMATURE":
        selected_bones = context.selected_editable_bones
        for bone in selected_bones:
            bone.name = bone.name.replace(suffix, replace_string)

# Enumerate bones of the same name while preserving its suffix.
# A dot is added followed by the enumerated number.
def enumerate_bones(context):
    obj = context.object
    if obj.type != "ARMATURE":
        return
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)

    edit_bones = context.object.data.edit_bones
    index = {
        "left" : {},
        "right" : {},
        "other" : {},
    }
    for bone in edit_bones:
        end = bone.name[-2:]
        dir = "other"
        suffix = ""
        if end == "_l":
            dir = "left"
            suffix = "_l"
        elif end == "_r":
            dir = "right"
            suffix = "_r"

        # Obtain the name without the suffix if there are any
        substrings = bone.name[:-2].split(".")
        if dir == "other":
            substrings = bone.name.split(".")
        name = substrings[0]
        # If the index at the current name and direction does not exist
        # then the index should be 0 otherwise
        # add a new entry at the current name and direction with an incremented index
        if index[dir].get(name) == None:
            index[dir][name] = 0
        else:
            index[dir][name] = index[dir][name] + 1

        # Enumerates the bone
        if len(substrings) == 2:
            if index[dir][name] == 0:
                bone.name = name + suffix
            else:
                bone.name = name + "." + str(index[dir][name]) + suffix
        else:
            bone.name = name + suffix

# Creation

def bones_from_objects(context, tip_length):
    selected_objects = context.selected_objects
    obj = bpy.data.objects["Armature"]
    context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    edit_bones = obj.data.edit_bones
    bone_names = []
    mwi = obj.matrix_world.inverted()
    for i in range(1, len(selected_objects)):
        b = edit_bones.new("bone")
        bone_names.append(b.name)
        b.head = mwi @ selected_objects[i-1].matrix_world.translation
        b.tail = mwi @ selected_objects[i].matrix_world.translation
        if len(bone_names) >= 2:
            edit_bones[bone_names[len(bone_names)-1]].use_connect = True
            edit_bones[bone_names[len(bone_names)-1]].parent = edit_bones[bone_names[len(bone_names)-2]]
        if (i+1) % 3 == 0:
            tip = edit_bones.new("bone")
            bone_names.append(tip.name)
            tip.head = b.tail
            tip.tail = tip.head + b.vector.normalized() * tip_length
            edit_bones[bone_names[len(bone_names)-1]].use_connect = True 
            edit_bones[bone_names[len(bone_names)-1]].parent = edit_bones[bone_names[len(bone_names)-2]]

def bones_from_verts(context, reverse):
    mesh_obj = context.object
    mesh = mesh_obj.data
    bm = bmesh.from_edit_mesh(mesh)
    selected_verts = {v.index:v for v in bm.verts if v.select}  
    adj_dict = {}
    for vi in selected_verts:
        l = list()
        adj_dict[vi] = l
        for e in bm.edges:
            adj_vert = e.other_vert(selected_verts[vi])
            if adj_vert != None and adj_vert in selected_verts.values():
                adj_dict[vi].append(adj_vert.index)
    #print(adj_dict)
    obj = bpy.data.objects["Armature"]
    context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    for bone in obj.data.edit_bones:
        bone.select = False

    edit_bones = obj.data.edit_bones
    mwi = obj.matrix_world.inverted()
    b = None
    last_b = None
    curr_i = 0
    last_i = 0
    for i in range(len(selected_verts)):
        if i == 0:
            v = bm.select_history.active
            curr_i = adj_dict[v.index][0]
            last_i = v.index 
        else:
            #print(curr_i)
            b = edit_bones.new("bone")
            b.head = mwi @ mesh_obj.matrix_world @ selected_verts[last_i].co
            b.tail = mwi @ mesh_obj.matrix_world @ selected_verts[curr_i].co
            if last_b != None:
                b.use_connect = True
                b.parent = last_b
            last_b = b
            for vi in adj_dict[curr_i]:
                if last_i != vi:
                    last_i = curr_i
                    curr_i = vi
                    break
# Alignment

# Align bones on a specified axis, taking in a selection that contains the start and end of the bone chain to align
# This will bend the bones between the start and end bone while preserving the positions of the head of the start bone and the
# tail of the last bone
# Note: All bones in the chain must be connected and start and end bones must be selected in edit mode for this to work properly,
# only works on a chain of three bones in pose mode
class IK_Bone_Settings():
    use_ik_limit_x = 0
    use_ik_limit_y = 0
    use_ik_limit_z = 0
    ik_min_x = 0
    ik_max_x = 0
    ik_min_y = 0
    ik_max_y = 0
    ik_min_z = 0
    ik_max_z = 0
    def __init__(self, use_ik_limit_x, use_ik_limit_y, use_ik_limit_z, ik_min_x, ik_max_x, ik_min_y, ik_max_y, ik_min_z, ik_max_z,):
        self.use_ik_limit_x = use_ik_limit_x
        self.use_ik_limit_y = use_ik_limit_y
        self.use_ik_limit_z = use_ik_limit_z
        self.ik_min_x = ik_min_x
        self.ik_max_x = ik_max_x
        self.ik_min_y = ik_min_y
        self.ik_max_y = ik_max_y
        self.ik_min_z = ik_min_z
        self.ik_max_z = ik_max_z

# Planar_align_bones helper function
# Sets the ik limits so that the ik solver bends the chain around the specified axis, saves the original ik limits to a dictionary
def set_bone_limits(arm, ik_bone_settings, axis, eb):
    pb = arm.pose.bones[eb.name]
    # Save the settings first before making changes so we can later reset our ik settings to their original values
    ik_bone_settings[eb.name] = IK_Bone_Settings(
            pb.use_ik_limit_x,
            pb.use_ik_limit_y,
            pb.use_ik_limit_z,
            pb.ik_min_x,
            pb.ik_max_x,                
            pb.ik_min_y,
            pb.ik_max_y,
            pb.ik_min_z,
            pb.ik_max_z,              
        )
    if axis == "x":
        pb.use_ik_limit_y = True
        pb.use_ik_limit_z = True
        pb.ik_min_y = 0
        pb.ik_max_y = 0
        pb.ik_min_z = 0
        pb.ik_max_z = 0
    if axis == "y":
        pb.use_ik_limit_x = True
        pb.use_ik_limit_z = True
        pb.ik_min_x = 0
        pb.ik_max_x = 0
        pb.ik_min_z = 0
        pb.ik_max_z = 0
    if axis == "z": 
        pb.use_ik_limit_x = True
        pb.use_ik_limit_y = True                  
        pb.ik_min_x = 0
        pb.ik_max_x = 0
        pb.ik_min_y = 0
        pb.ik_max_y = 0

def planar_align_bones(context, axis):
    arm = context.object
    if arm.type != "ARMATURE":
        return
    context.view_layer.objects.active = arm
    
    bpy.ops.object.mode_set(mode='EDIT')

    selected_edit_bones = context.selected_editable_bones
    edit_bones = arm.data.edit_bones

    # Create ik target bone and make it face in the reverse of where the last bone in the selection is facing
    tb = edit_bones.new("bone")
    target = tb.name
    tb.head = selected_edit_bones[-1].tail
    tb.tail = selected_edit_bones[-1].head

    # If the end bone in the selection has children, break that connection temporarily
    # The parent will be reparented to its child after we finish aligning the bone chain
    tip_children = selected_edit_bones[-1].children_recursive
    tip_child_name = None
    isTipChildConnected = None
    if len(tip_children) > 0:
        # Save the connection flag before unparenting since
        # setting its parent to none also sets use_connect to false
        isTipChildConnected = tip_children[0].use_connect
        tip_children[0].parent = None
        tip_child_name = tip_children[0].name

    # Straighten all bones between the selected bones
    edit_bones.active = selected_edit_bones[0]
    bpy.ops.armature.align()

    # Limit the bend around the inputed axis
    # Sets the limit for each bone in between the start and end selected bone skipping the start bone and gets the chain length
    ik_bone_settings = {}
    eb = selected_edit_bones[0]
    chain_length = 1
    while eb != selected_edit_bones[-1]:
        # Skip the first bone (root) to allow it to have a free range of motion, this will ensure the tip tail point remains in the same position
        # after applying the ik solver
        if eb == selected_edit_bones[0]:
            eb = eb.children[0]
            chain_length += 1
            continue
        set_bone_limits(arm, ik_bone_settings, axis, eb)
        eb = eb.children[0]
        chain_length += 1
    set_bone_limits(arm, ik_bone_settings, axis, eb)

    bpy.ops.object.mode_set(mode='POSE')

    selected_edit_bones = context.selected_pose_bones

    # Bend the bones so that the tip point is back at its original position
    arm.data.bones.active = selected_edit_bones[-1].bone
    ab = context.active_pose_bone
    ik = ab.constraints.new("IK")
    ik.chain_count = chain_length
    ik.target = arm
    ik.subtarget = target

    bpy.ops.pose.armature_apply(selected=False)
    ab.constraints.remove(ik)

    bpy.ops.object.mode_set(mode='EDIT')

    selected_edit_bones = context.selected_editable_bones

    # Remove the target bone we used for ik
    edit_bones = arm.data.edit_bones
    edit_bones.remove(edit_bones.get(target))

    # Reparent the tip bone's child back to its original bone parent
    # tip_children will contain garbage data since we switched from edit to pose (where it is first initialized) and
    # then back to edit mode, however its length appears to stay the same
    if len(tip_children) > 0:
        tip_child = edit_bones.get(tip_child_name)
        tip_child.parent = selected_edit_bones[-1]
        tip_child.use_connect = isTipChildConnected

    # Reset each bone's ik settings back to their original values
    for i, b in enumerate(selected_edit_bones):
        if b == selected_edit_bones[0]:
            continue
        pb = arm.pose.bones[b.name]
        setting = ik_bone_settings[b.name]
        pb.use_ik_limit_x = setting.use_ik_limit_x
        pb.use_ik_limit_y = setting.use_ik_limit_y    
        pb.use_ik_limit_z = setting.use_ik_limit_z
        pb.ik_min_x = setting.ik_min_x
        pb.ik_max_x = setting.ik_max_x
        pb.ik_min_y = setting.ik_min_y
        pb.ik_max_y = setting.ik_max_y
        pb.ik_min_z = setting.ik_min_z
        pb.ik_max_z = setting.ik_max_z

def straighten_bones(context):
    obj = context.object
    if obj.type != "ARMATURE":
        return
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    selected_bones = context.selected_editable_bones
    pole_dir = (selected_bones[len(selected_bones)-1].tail - selected_bones[0].head).normalized()
    for i in range(len(selected_bones)-1):
        angle = selected_bones[i].vector.angle(pole_dir)
        opp_len = selected_bones[i].length * math.sin(angle)
        adj_len = selected_bones[i].length * math.cos(angle)
        right_pt = selected_bones[i].head + pole_dir * adj_len
        opp_dir = (right_pt - selected_bones[i].tail).normalized()
        selected_bones[i].tail = selected_bones[i].tail + opp_dir * opp_len

# Uncategorized

def reapply_auto_weights(context):
    obj = context.object
    if obj.type != "ARMATURE":
        return
    bpy.ops.paint.weight_from_bones(type='AUTOMATIC')

def parent_consecutive_selected_bones(context):
    obj = context.object
    if obj.type != "ARMATURE":
        return    
    selected_bones = context.selected_editable_bones
    d = {}
    for bone in selected_bones:
        substrings = bone.name.split(".")
        key = ""
        if len(substrings) == 2:
            key = int(substrings[1])
        else:
            key = 0
        d[key] = bone
    od = OrderedDict(sorted(d.items()))
    for i, key in enumerate(od):
        if i == 0:
            continue
        od[key].use_connect = True
        od[key].parent = od[i-1]

# VERTEX GROUP TOOLS
#########################################################################################################################################################

# Diagnostics

def check_vertex_groups(context):
    objects = context.selected_editable_objects
    intersect = set([vg.name for vg in objects[0].vertex_groups])
    no_diff = True
    for i in range(1, len(objects)):
        intersect = intersect & set([vg.name for vg in objects[i].vertex_groups])
    for obj in objects:
        diff = intersect ^ set([vg.name for vg in obj.vertex_groups])
        if len(diff) > 0:
            no_diff = False
            print(obj.name)
            print(str(diff) + "\n")
            obj.select_set(True)
        else:
            obj.select_set(False)
    if no_diff:
        print("No differences detected.")
    print("")

# Locked vertex group operations

def add_locked_vertex_groups(context):
    objects = context.selected_editable_objects    
    locked_list = [vg.name for vg in context.view_layer.objects.active.vertex_groups if vg.lock_weight == True]

    for ob in objects:
        if ob != context.view_layer.objects.active:
            ob_vgs = [vg.name for vg in ob.vertex_groups]
            for vg in locked_list:
                if vg not in ob_vgs:
                    ob.vertex_groups.new(name=vg)

def remove_locked_vertex_groups(context):
    objects = context.selected_editable_objects
    locked_list = [vg.name for vg in context.view_layer.objects.active.vertex_groups if vg.lock_weight == True]

    for ob in objects:
        for vg in ob.vertex_groups:
            if vg.name in locked_list:
                ob.vertex_groups.remove(vg)

def replace_locked_vertex_groups(context):
    objects = context.selected_editable_objects
    locked_list = [vg for vg in context.view_layer.objects.active.vertex_groups if vg.lock_weight == True]

    for ob in objects:
        for vg in ob.vertex_groups:
            for lvg in locked_list:
                if vg.index == lvg.index:
                    vg.name = lvg.name

def lock_selected_vertex_groups(context):
    objects = context.selected_editable_objects
    locked_list = [vg.name for vg in context.view_layer.objects.active.vertex_groups if vg.lock_weight == True]

    for ob in objects:
        for vg in ob.vertex_groups:
            if vg.name in locked_list:
                vg.lock_weight = True

# Vertex group operations

def mirror_empty_vertex_groups(context):
    objects = context.selected_editable_objects
    for ob in objects:
        vgs_names = [vg.name for vg in ob.vertex_groups]
        for vg in ob.vertex_groups:
            if vg.name[-2:] == "_r" and vg.name[:-2] + "_l" not in vgs_names:
                ob.vertex_groups.new(name = vg.name[:-2] + "_l")
            elif vg.name[-2] == "_l" and vg.name[:-2] + "_r" not in vgs_names:
                ob.vertex_groups.new(name = vg.name[:-2] + "_r")

def remove_vertex_groups(context):
    for ob in context.selected_editable_objects:
        for vg in ob.vertex_groups:
            ob.vertex_groups.remove(vg)

def replace_list_vertex_groups(context):
    objects = context.selected_editable_objects
    replace_list = [
        ['thorac', "forearm.1_r"]
    ]
    for ob in objects:
        for n in replace_list:
            if n[0] in ob.vertex_groups:
                ob.vertex_groups[n[0]].name = n[1]

# SPINE RIGGING TOOLS
#########################################################################################################################################################

# Helper function for remove_constraints
# Remove all constraints of the type on bone b
def remove_constraints_on_bone(b):
    # Create a list of all the copy location constraints on this bone
    copyLocConstraints = [ c for c in b.constraints if c.type == 'SPLINE_IK' ]

    # Iterate over all the bone's copy location constraints and delete them all
    for c in copyLocConstraints:
        b.constraints.remove(c)

# Create_spine_rig helper function
# Clears and previous constraints used by the spine rig creator
def remove_constraints(start_bone, end_bone):
    b = start_bone
    while b != end_bone:
        remove_constraints_on_bone(b)
        b = b.children[0]
    remove_constraints_on_bone(b)

def create_bezier_spine(context, arm_obj, selected_pose_bones, flip_start_handles, flip_end_handles, preserve_length, handle_length):
    # If bone 0 has children then set it to start_bone and bone 1 to end_bone otherwise
    # set bone 0 to end_bone and bone 1 to start_bone
    if len(selected_pose_bones[0].children) > 0:
        start_bone = selected_pose_bones[0]
        end_bone = selected_pose_bones[1]
        print("start: " + selected_pose_bones[0].name + " end: " + selected_pose_bones[1].name)
    else:
        start_bone = selected_pose_bones[1]
        end_bone = selected_pose_bones[0]
        print("start: " + selected_pose_bones[1].name + " end: " + selected_pose_bones[0].name)

    # Create new curve and assign its start and end controls to the start and end bone positions
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.view3d.snap_cursor_to_center()
    bpy.ops.curve.primitive_bezier_curve_add()
    spline_obj = context.object
    
    # Transform each bone position from pose space to the curve's object space then assign them to the bezier points
    bezier_points = spline_obj.data.splines.active.bezier_points
    mwi = spline_obj.matrix_world.inverted()
    bezier_points[0].co = mwi @ arm_obj.matrix_world @ start_bone.head
    bezier_points[1].co = mwi @ arm_obj.matrix_world @ end_bone.tail

    # Get the distances between the left and right handle of bezier point 0 and 1
    handle0_length_left = (bezier_points[0].handle_left - bezier_points[0].co).length
    handle0_length_right = (bezier_points[0].handle_right - bezier_points[0].co).length
    handle1_length_left = (bezier_points[1].handle_left - bezier_points[1].co).length
    handle1_length_right = (bezier_points[1].handle_right - bezier_points[1].co).length
    # Set all handle lengths to handle_length
    if not preserve_length:
        handle0_length_left = handle_length
        handle0_length_right = handle_length
        handle1_length_left = handle_length
        handle1_length_right = handle_length

    # Convert the start and end bone direction vectors from pose bone space to curve object space before setting the direction
    start_handles_dir = (mwi @ arm_obj.matrix_world @ start_bone.vector).normalized()
    end_handles_dir = (mwi @ arm_obj.matrix_world @ end_bone.vector).normalized()
        
    # Flip direction if flipping is true
    if flip_start_handles:
        start_handles_dir *= -1
    if flip_end_handles:
        end_handles_dir *= -1

    bezier_points[0].handle_left = bezier_points[0].co + start_handles_dir * handle0_length_left
    bezier_points[0].handle_right = bezier_points[0].co + start_handles_dir * handle0_length_right
    bezier_points[1].handle_left = bezier_points[1].co + end_handles_dir * handle1_length_left
    bezier_points[1].handle_right = bezier_points[1].co + end_handles_dir * handle1_length_right

    return spline_obj

# Create_spine_rig helper function
# Create bone controls for the spine, returns the end bone name
def create_spine_ctrls(context, arm_obj, start_bone, end_bone, spline_obj, bone_control_length, start_bone_name, end_bone_name):

    context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')
    edit_bones = arm_obj.data.edit_bones
    # Specify the direction the control bones should face
    mwi = arm_obj.matrix_world.inverted()
    dir = mwi @ Vector([1, 0, 0])

    # Create a bone to control the location and orientation of the start spline control point
    start_bone_default_name = "start_bone"
    start_bone_name = start_bone_default_name if len(start_bone_name) == 0 else start_bone_name 
    name = start_bone_name + "_ctrl"
    b = edit_bones.new(name)
    b.head = edit_bones.get(start_bone.name).head
    b.tail = edit_bones.get(start_bone.name).head + dir * bone_control_length
    b.parent = None
    b.use_deform = False
    # Creating a hook in edit seems to create some offset between the point and bone so need to create a hook in object mode
    bpy.ops.object.mode_set(mode='OBJECT')
    # Hook bezier points 0 to the start bone control and 1 to the end bone control
    hm = spline_obj.modifiers.new(name = start_bone_name + "_hook", type='HOOK')
    hm.object = arm_obj
    hm.subtarget = name
    # vertex index = (control point index * 3) + 1
    # so control point 0 is vertex index 1
    hm.vertex_indices_set([1])

    bpy.ops.object.mode_set(mode='EDIT')

    # Create a bone to control the location and orientation of the end spline control point
    end_bone_default_name = "end_bone"
    end_bone_name = end_bone_default_name if len(end_bone_name) == 0 else end_bone_name 
    name = end_bone_name + "_ctrl"
    b = edit_bones.new(name)
    b.head = edit_bones.get(end_bone.name).tail
    b.tail = edit_bones.get(end_bone.name).tail + dir * bone_control_length
    b.parent = None
    b.use_deform = False
    # Creating a hook in edit seems to create some offset between the point and bone so need to create a hook in object mode
    bpy.ops.object.mode_set(mode='OBJECT')
    # Hook bezier points 0 to the start bone control and 1 to the end bone control
    hm = spline_obj.modifiers.new(name = end_bone_name + "_hook", type='HOOK')
    hm.object = arm_obj
    hm.subtarget = name
    # vertex index = (control point index * 3) + 1
    # so control point 1 is vertex index 4
    hm.vertex_indices_set([4])

    return name

# Add_spine_twist helper function
# Rotates pose bone b at index i to create a spiraling twist like motion in the spine bone chain
def add_twist_driver_to_bone(arm_obj, chain_count, start_bone, end_bone_name, twist_start_bone, b, i):
    # To prevent additive rotation from inheriting the bone's parent rotation when twisting the spine
    b.bone.use_inherit_rotation = False

    # Remove any rotation drivers, set rotation mode to euler xyz order
    # Then add a new driver at the y rotation channel
    path = 'rotation_euler'
    b.driver_remove(path)
    if twist_start_bone:
        b.rotation_mode = 'XYZ'
        fcurve = b.driver_add(path, 1)

        # Create a new driver variable that gets the local rotation z of the end control bone
        var = fcurve.driver.variables.new()
        var.type = 'TRANSFORMS'
        target = var.targets[0]
        target.id = arm_obj
        target.bone_target = end_bone_name
        target.transform_type = 'ROT_Z'
        target.rotation_mode = 'XYZ'
        target.transform_space = 'LOCAL_SPACE'

        # Take the local rotation z stored in the variable and divide by the chain length + 1 or only chain length if the start bone is omitted 
        # Then multiply it by the index to get the final rotation of the bone corresponding to the index
        fcurve.driver.expression = fcurve.driver.variables[0].name +  "/" + str(chain_count + 1 if twist_start_bone else 0) + "*" + str(i)
    elif b != start_bone:
        b.rotation_mode = 'XYZ'
        fcurve = b.driver_add(path, 1)

        # Create a new driver variable that gets the local rotation z of the end control bone
        var = fcurve.driver.variables.new()
        var.type = 'TRANSFORMS'
        target = var.targets[0]
        target.id = arm_obj
        target.bone_target = end_bone_name
        target.transform_type = 'ROT_Z'
        target.rotation_mode = 'XYZ'
        target.transform_space = 'LOCAL_SPACE'

        # Take the local rotation z stored in the variable and divide by the chain length + 1
        # Then multiply it by the index to get the final rotation of the bone corresponding to the index
        fcurve.driver.expression = fcurve.driver.variables[0].name +  "/" + str(chain_count) + "*" + str(i)
    
# Create_spine_rig helper function
# Traverse the spine chain adding drivers to create a twist motion
def add_spine_twist(arm_obj, start_bone, end_bone, end_bone_name, twist_start_bone):
    b = start_bone
    chain_count = 1
    # Get chain length from the start to end bone
    while b != end_bone:
        chain_count += 1
        b = b.children[0]

    b = start_bone
    i = 1 if twist_start_bone else 0
    while b != end_bone:
        add_twist_driver_to_bone(arm_obj, chain_count, start_bone, end_bone_name, twist_start_bone, b, i)      
        i += 1
        b = b.children[0]
    add_twist_driver_to_bone(arm_obj, chain_count, start_bone, end_bone_name, twist_start_bone, b, i)

# Create_spine_rig helper function
# IK constrain spine bones to the spline
def constrain_bones_spline(context, arm_obj, spline_obj, start_bone, end_bone):
    bpy.ops.object.mode_set(mode='POSE')
    for bone in arm_obj.data.bones:
        bone.select = False
    arm_obj.data.bones.active = end_bone.bone
    splineIK = context.selected_pose_bones_from_active_object[0].constraints.new(type='SPLINE_IK')
    splineIK.target = spline_obj
    b = start_bone
    chain_count = 1
    while b != end_bone:
        chain_count += 1
        b = b.children[0]
    splineIK.chain_count = chain_count
    splineIK.use_curve_radius = False
    splineIK.y_scale_mode = 'NONE'
    splineIK.xz_scale_mode = 'NONE'

# Places a new curve between the selected start and end bones of a spine
# Note: each bone in that spine between the start and end bones need to only have one child and you need to select the start and end bones in
# pose mode
def create_spine_rig(context, flip_start_handles, flip_end_handles, twist_start_bone, preserve_length, handle_length, bone_control_length, start_bone_name, end_bone_name):
    arm_obj = context.object

    selected_pose_bones = context.selected_pose_bones
    if arm_obj.type != "ARMATURE" or arm_obj.type == "ARMATURE" and len(selected_pose_bones) < 2:
        return
    
    # Obtain start and end bones
    start_bone = selected_pose_bones[0]
    end_bone = selected_pose_bones[1]

    remove_constraints(start_bone, end_bone)

    spline_obj = create_bezier_spine(context, arm_obj, selected_pose_bones, flip_start_handles, flip_end_handles, preserve_length, handle_length)

    end_bone_name = create_spine_ctrls(context, arm_obj, start_bone, end_bone, spline_obj, bone_control_length, start_bone_name, end_bone_name)

    constrain_bones_spline(context, arm_obj, spline_obj, start_bone, end_bone)

    add_spine_twist(arm_obj, start_bone, end_bone, end_bone_name, twist_start_bone)

# Perform adjustments to the selected spline. Logic is identical to create_spine_rig but does not create a new curve.
def update_spline(context, flip_start_handles, flip_end_handles, preserve_length, handle_length):
    obj = context.object

    if obj.type != 'CURVE':
        return

    # Transform each bone position from pose space to the curve's object space then assign them to the bezier points
    bezier_points = context.object.data.splines.active.bezier_points
    mwi = context.object.matrix_world.inverted()

    # Get the distances between the left and right handle of bezier point 0 and 1
    handle0_length_left = (bezier_points[0].handle_left - bezier_points[0].co).length
    handle0_length_right = (bezier_points[0].handle_right - bezier_points[0].co).length
    handle1_length_left = (bezier_points[1].handle_left - bezier_points[1].co).length
    handle1_length_right = (bezier_points[1].handle_right - bezier_points[1].co).length
    # Set all handle lengths to handle_length
    if not preserve_length:
        handle0_length_left = handle_length
        handle0_length_right = handle_length
        handle1_length_left = handle_length
        handle1_length_right = handle_length

    # Calculate direction from the left and right handles
    start_handles_dir = (bezier_points[0].handle_left - bezier_points[0].handle_right).normalized()
    end_handles_dir = (bezier_points[1].handle_left - bezier_points[1].handle_right).normalized()
        
    # Flip direction if flipping is true
    if flip_start_handles:
        start_handles_dir *= -1
    if flip_end_handles:
        end_handles_dir *= -1

    bezier_points[0].handle_left = bezier_points[0].co + start_handles_dir * handle0_length_left
    bezier_points[0].handle_right = bezier_points[0].co + start_handles_dir * handle0_length_right
    bezier_points[1].handle_left = bezier_points[1].co + end_handles_dir * handle1_length_left
    bezier_points[1].handle_right = bezier_points[1].co + end_handles_dir * handle1_length_right

# MODIFIER TOOLS
#########################################################################################################################################################

def remove_modifier(context, delete_modifier_name):
    for o in context.selected_objects:
        modifier = o.modifiers.get(delete_modifier_name)
        print(delete_modifier_name + " " + str(modifier))
        if modifier != None:
            o.modifiers.remove(modifier)
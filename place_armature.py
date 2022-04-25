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

def create_bezier_spine(context, arm, start_bone, end_bone, flip_start_handles, flip_end_handles, preserve_length, handle_length):

    # Create new curve and assign its start and end controls to the start and end bone positions
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.view3d.snap_cursor_to_center()
    bpy.ops.curve.primitive_bezier_curve_add()
    spline_obj = context.object
    
    # Transform each bone position from pose space to the curve's object space then assign them to the bezier points
    bezier_points = spline_obj.data.splines.active.bezier_points
    mwi = spline_obj.matrix_world.inverted()
    bezier_points[0].co = mwi @ arm.matrix_world @ start_bone.head
    bezier_points[1].co = mwi @ arm.matrix_world @ end_bone.tail

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
    start_handles_dir = (mwi @ arm.matrix_world @ start_bone.vector).normalized()
    end_handles_dir = (mwi @ arm.matrix_world @ end_bone.vector).normalized()
        
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
# Create bone controls for the spine, returns the start and end control names
def create_spine_ctrls(context, arm, start_bone, end_bone, spline_obj, bone_control_length, start_bone_name, end_bone_name):

    context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    edit_bones = arm.data.edit_bones
    # Specify the direction the control bones should face
    mwi = arm.matrix_world.inverted()
    dir = mwi @ Vector([1, 0, 0])

    # Create a bone to control the location and orientation of the start spline control point
    start_bone_default_name = "start_bone"
    start_bone_name = start_bone_default_name if len(start_bone_name) == 0 else start_bone_name 
    start_ctrl_name = start_bone_name + "_ctrl"
    b = edit_bones.new(start_ctrl_name)
    b.head = edit_bones.get(start_bone.name).head
    b.tail = edit_bones.get(start_bone.name).head + dir * bone_control_length
    b.parent = None
    b.use_deform = False
    # Creating a hook in edit seems to create some offset between the point and bone so need to create a hook in object mode
    bpy.ops.object.mode_set(mode='OBJECT')
    # Hook bezier points 0 to the start bone control and 1 to the end bone control
    hm = spline_obj.modifiers.new(name=start_bone_name + "_hook", type='HOOK')
    hm.object = arm
    hm.subtarget = start_ctrl_name
    # vertex index = (control point index * 3) + 1
    # so control point 0 is vertex index 1
    hm.vertex_indices_set([1])

    bpy.ops.object.mode_set(mode='EDIT')

    # Create a bone to control the location and orientation of the end spline control point
    end_bone_default_name = "end_bone"
    end_bone_name = end_bone_default_name if len(end_bone_name) == 0 else end_bone_name 
    end_ctrl_name = end_bone_name + "_ctrl"
    b = edit_bones.new(end_ctrl_name)
    b.head = edit_bones.get(end_bone.name).tail
    b.tail = edit_bones.get(end_bone.name).tail + dir * bone_control_length
    b.parent = None
    b.use_deform = False
    # Creating a hook in edit seems to create some offset between the point and bone so need to create a hook in object mode
    bpy.ops.object.mode_set(mode='OBJECT')
    # Hook bezier points 0 to the start bone control and 1 to the end bone control
    hm = spline_obj.modifiers.new(name=end_bone_name + "_hook", type='HOOK')
    hm.object = arm
    hm.subtarget = end_ctrl_name
    # vertex index = (control point index * 3) + 1
    # so control point 1 is vertex index 4
    hm.vertex_indices_set([4])

    return start_ctrl_name, end_ctrl_name

# Helper function to return the name of the first child in bone b_name's children that is connected to bone b_name
def get_child_name(b_name):
    arm = bpy.context.object

    bpy.ops.object.mode_set(mode='EDIT')
    children = arm.data.edit_bones.get(b_name).children
    for child in children:
        if child.use_connect:
            return child.name

def get_chain_count(start_bone_name, end_bone_name):
    chain_count = 1
    b_name = start_bone_name
    while b_name != end_bone_name:
        chain_count += 1
        b_name = get_child_name(b_name)
    return chain_count

# Add_spine_twist helper function
# Rotates pose bone b at index i to create a spiraling twist like motion in the spine bone chain
def add_twist_driver_to_bone(arm, start_bone_name, end_bone_name, start_ctrl_name, end_ctrl_name, is_twist_count_even, twist_start_bone, twist_count, b_name, i):
    
    bones = arm.pose.bones
    obj_b = arm.data.bones.get(b_name)
    pose_b = arm.pose.bones.get(b_name)
    # To prevent additive rotation from inheriting the bone's parent rotation when twisting the spine
    obj_b.use_inherit_rotation = False

    # Remove any rotation drivers, set rotation mode to euler xyz order
    # Then add a new driver at the y rotation channel
    path = 'rotation_euler'
    pose_b.driver_remove(path)

    pose_b.rotation_mode = 'XYZ'
    fcurve = pose_b.driver_add(path, 1)

    bone1_name = None
    bone2_name = None
    bone1_transform_type = None
    bone2_transform_type = None
    expression = None
    var1_name = "bone1"
    var2_name = "bone2"
    mid_index = int(math.ceil(twist_count / 2))
    mid_index = mid_index if twist_start_bone else (mid_index + 1)
    # if at start bone and twist start is enabled, then set the start bone twist angle to the average of the start control and start bone child twist angles
    if b_name == start_bone_name and twist_start_bone:  
        bone1_name = start_ctrl_name
        bone2_name = get_child_name(b_name)
        # Switch back to pose mode since get_child_name uses edit mode
        bpy.ops.object.mode_set(mode='POSE')
        bone1_transform_type = 'ROT_Z'
        bone2_transform_type = 'ROT_Y'
        expression = f"({var1_name} + {var2_name}) / 2"
    # if at the second bone and twist start is disabled, then set the second bone twist angle to the average of the start control and the second bone's child twist angles
    elif i == 2 and not twist_start_bone:
        bone1_name = start_ctrl_name
        bone2_name = get_child_name(b_name)
        # Switch back to pose mode since get_child_name uses edit mode
        bpy.ops.object.mode_set(mode='POSE')
        bone1_transform_type = 'ROT_Z'
        bone2_transform_type = 'ROT_Y'
        expression = f"({var1_name} + {var2_name}) / 2"
    elif b_name == end_bone_name:
        bone1_name = pose_b.parent.name
        bone2_name = end_ctrl_name
        bone1_transform_type = 'ROT_Y'
        bone2_transform_type = 'ROT_Z'
        expression = f"({var1_name} + {var2_name}) / 2"
    # Evenly distribute the middle rotation among two bones at the twist center if the number of twists is even
    elif is_twist_count_even and (i == mid_index or i == mid_index + 1):
        bone1_name = start_ctrl_name
        bone2_name = end_ctrl_name
        bone1_transform_type = 'ROT_Z'
        bone2_transform_type = 'ROT_Z'
        if i == mid_index:
            expression = f"({var1_name} + {var2_name}) / 2 + abs({var2_name} + {var1_name}) / (2 * {twist_count + 1})"
        elif i == mid_index + 1:
            expression = f"({var1_name} + {var2_name}) / 2 - abs({var2_name} + {var1_name}) / (2 * {twist_count + 1})"
    elif not is_twist_count_even and i == mid_index: # If the number of twists is odd the twist center is a single bone so just twist that bone
        bone1_name = start_ctrl_name
        bone2_name = end_ctrl_name
        bone1_transform_type = 'ROT_Z'
        bone2_transform_type = 'ROT_Z'
        expression = f"({var1_name} + {var2_name}) / 2"
    else: # between the start and end bone
        bone1_name = pose_b.parent.name
        bone2_name = get_child_name(b_name)
        # Switch back to pose mode since get_child_name uses edit mode
        bpy.ops.object.mode_set(mode='POSE')
        bone1_transform_type = 'ROT_Y'
        bone2_transform_type = 'ROT_Y'
        expression = f"({var1_name} + {var2_name}) / 2"

    bones = arm.pose.bones
    # Create a new driver variable that gets the local rotation z of the end control bone
    var1 = fcurve.driver.variables.new()
    var1.type = 'TRANSFORMS'
    var1.name = var1_name
    target = var1.targets[0]
    target.id = arm 
    target.bone_target = bone1_name
    target.transform_type = bone1_transform_type
    target.rotation_mode = 'XYZ'
    target.transform_space = 'LOCAL_SPACE'

    var2 = fcurve.driver.variables.new()
    var2.type = 'TRANSFORMS'
    var2.name = var2_name
    target = var2.targets[0]
    target.id = arm
    target.bone_target = bone2_name
    target.transform_type = bone2_transform_type
    target.rotation_mode = 'XYZ'
    target.transform_space = 'LOCAL_SPACE'

    # Take the local rotation z stored in the variable and divide by the chain length + 1 or only chain length if the start bone is omitted 
    # Then multiply it by the index to get the final rotation of the bone corresponding to the index
    fcurve.driver.expression = expression
    
# Create_spine_rig helper function
# Traverse the spine chain adding drivers to create a twist motion; skip the first bone if twist_start_bone is false
def add_spine_twist(arm, start_bone_name, end_bone_name, ctrl_names, twist_start_bone):
    # Determine whether the chain count is even so we know wethere or not to distribute twisting around the chain's mid section
    chain_count = get_chain_count(start_bone_name, end_bone_name)
    bpy.ops.object.mode_set(mode='POSE')
    twist_count = chain_count if twist_start_bone else chain_count - 1
    is_twist_count_even = twist_count % 2 == 0
    i = 1
    b_name = start_bone_name
    while b_name != end_bone_name:
        if b_name == start_bone_name and not twist_start_bone:
            i += 1
            b_name = get_child_name(b_name)
            continue
        add_twist_driver_to_bone(arm, start_bone_name, end_bone_name, ctrl_names[0], ctrl_names[1], is_twist_count_even, twist_start_bone, chain_count, b_name, i)
        i += 1  
        b_name = get_child_name(b_name)
        print(b_name + " i: " + str(i))
    add_twist_driver_to_bone(arm, start_bone_name, end_bone_name, ctrl_names[0], ctrl_names[1], is_twist_count_even, twist_start_bone, chain_count, b_name, i)

# Create_spine_rig helper function
# IK constrain spine bones to the spline
def constrain_bones_spline(context, arm, spline_obj, start_bone, end_bone):
    bpy.ops.object.mode_set(mode='POSE')
    for bone in arm.data.bones:
        bone.select = False
    arm.data.bones.active = end_bone.bone
    splineIK = context.selected_pose_bones_from_active_object[0].constraints.new(type='SPLINE_IK')
    splineIK.target = spline_obj
    splineIK.chain_count = get_chain_count(start_bone.name, end_bone.name)
    bpy.ops.object.mode_set(mode='POSE')    
    splineIK.use_curve_radius = False
    splineIK.y_scale_mode = 'NONE'
    splineIK.xz_scale_mode = 'NONE'

# Places a new curve between the selected start and end bones of a spine
# Note: each bone in that spine between the start and end bones need to only have one child and you need to select the start and end bones in
# pose mode
def create_spine_rig(context, flip_start_handles, flip_end_handles, twist_start_bone, preserve_length, handle_length, bone_control_length, start_bone_name, end_bone_name):
    arm = context.object

    selected_pose_bones = context.selected_pose_bones
    if arm.type != "ARMATURE" or arm.type == "ARMATURE" and len(selected_pose_bones) < 2:
        return
    
    # Set to rest before rigging otherwise the rig will have offsets
    arm.data.pose_position = 'REST'

    # Set the active bone as the end bone and the other bone as the start bone
    start_bone = selected_pose_bones[0]
    end_bone = selected_pose_bones[1]
    if arm.data.bones.active == selected_pose_bones[0]:
        start_bone = selected_pose_bones[1]
        end_bone = selected_pose_bones[0]

    print("start: " + start_bone.name + " end: " + end_bone.name)

    remove_constraints(start_bone, end_bone)

    spline_obj = create_bezier_spine(context, arm, start_bone, end_bone, flip_start_handles, flip_end_handles, preserve_length, handle_length)

    ctrl_names = create_spine_ctrls(context, arm, start_bone, end_bone, spline_obj, bone_control_length, start_bone_name, end_bone_name)

    constrain_bones_spline(context, arm, spline_obj, start_bone, end_bone)

    add_spine_twist(arm, start_bone.name, end_bone.name, ctrl_names, twist_start_bone)

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

# OBJECT ALIGNMENT TOOLS
#########################################################################################################################################################

# Align origin
def align_origin(context):
    active_obj = context.active_object
    # Align every selected object's origin with the active object
    # Alignment occurs by first storing the original verts' positions, rotating the mesh and then setting the rotated mesh's verts' positions back to its original verts' positions
    for obj in context.selected_objects:
        if obj != active_obj:    
            me = obj.data
            # Copy original world positions of the selected object's verts  
            original_world_verts = [obj.matrix_world @ v.co for v in me.vertices]#bmesh.from_edit_mesh(obj.data).verts  
            # print("before rotation_euler")
            # print("obj.matrix_world:")
            # print(obj.matrix_world)

            # Copy rotation of active to selected objects
            previous_mode = obj.rotation_mode
            active_previous_mode = active_obj.rotation_mode 
            obj.rotation_mode = "XYZ"
            active_obj.rotation_mode = "XYZ" 
            obj.rotation_euler = active_obj.rotation_euler
            obj.rotation_mode  = previous_mode
            active_obj.rotation_mode = active_previous_mode           
            bpy.context.view_layer.update()
            # print("after rotation_euler")
            # print("obj.matrix_world:")
            # print(obj.matrix_world)
            
            # Get a BMesh representation
            bm = bmesh.new()   # create an empty BMesh
            bm.from_mesh(me)   # fill it in from a Mesh
            
            # Set the rotated mesh's verts back to the positions of its original verts
            for i, v in enumerate(bm.verts):
                v.co = obj.matrix_world.inverted() @ original_world_verts[i]

            # Finish up, write the bmesh back to the mesh
            bm.to_mesh(me)
            bm.free()  # free and prevent further access

bl_info = {
    "name": "Rigging Tools",
    "blender": (2, 81, 6),
    "category": "Object",
}

import importlib
if "bpy" in locals():
    if "place_armature" in locals():
        importlib.reload(place_armature)

import bpy

from bpy.props import (
    StringProperty,
    BoolProperty,
    IntProperty,
    FloatProperty,
    FloatVectorProperty,
    EnumProperty,
    PointerProperty,
)

from bpy.types import (
    Panel,
    Menu,
    Operator,
    PropertyGroup,  
)

# Specifies all properties used by the tooling methods
class Properties(PropertyGroup):
    suffix_string: StringProperty (
        name="Suffix",
        description="Enter suffix",
        default="",
        maxlen=1024,
    )
    replace_string: StringProperty (
        name="Replace String",
        description="Enter string",
        default="",
        maxlen=1024,
    )
    tip_length: FloatProperty (
        name="Tip Length",
        description="Enter length",
        default=0.5,
    )
    reverse_bones: BoolProperty (
        name="Reverse Bones",
        description="Changes bone order",
        default=False,
    )
    align_axis: EnumProperty(
        name="Axis",
        description="Alignment axis",
        items=[
            ("x", "x axis", ""),
            ("y", "y axis", ""),
            ("z", "z axis", ""),
        ]
    )
    start_bone_name: StringProperty (
        name="Start Bone Name",
        description="Enter name",
        default="",
        maxlen=1024,
    )
    end_bone_name: StringProperty (
        name="End Bone Name",
        description="Enter name",
        default="",
        maxlen=1024,
    )
    bone_control_length: FloatProperty (
        name="Bone Control Length",
        description="Enter Bone length",
        default=0.5,
    )
    flip_start_handles: BoolProperty (
        name="Flip Start Handles",
        description="Flip the direction of the start handles",
        default=False,
    )
    flip_end_handles: BoolProperty (
        name="Flip End Handles",
        description="Flip the direction of the end handles",
        default=False,
    )
    preserve_length: BoolProperty (
        name="Preserve Length",
        description="Preserve handle lengths",
        default=False,
    )
    twist_start_bone: BoolProperty (
        name="Twist Start Bone",
        description="Allow twisting around the first bone in the spine chain",
        default=False,
    )
    handle_length: FloatProperty (
        name="Handle Length",
        description="Enter length",
        default=0.5,
    )
    delete_modifier_name: StringProperty (
        name="Modifier name",
        description="Enter modifier name to delete from the selected objects",
        default="",
        maxlen=1024,
    )

# Sepcifies the tool panels, sub panels and the labels, properties, and operators within those labelss
# e.g. in this case a panel named rigging tools with several panels under it such as a panel named bone tools and 
# another named vertex tools. Bone tools and vertex tools then have several more sub panels each then containing
# labels, propertiees, and operators

class ToolPanel(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tool"

class OBJECT_PT_riggingToolsPanel(ToolPanel):
    bl_idname = "OBJECT_PT_riggingToolsPanel"
    bl_label = "Rigging Tools"
    #bl_context = "objectmode"

    def draw(self, context):
        return

class OBJECT_PT_boneTools(ToolPanel):
    bl_parent_id = "OBJECT_PT_riggingToolsPanel"
    bl_label = "Bone Tools"

    def draw(self, context):
        return

class OBJECT_PT_boneToolsNaming(ToolPanel):
    bl_parent_id = "OBJECT_PT_boneTools"
    bl_label = "Naming"

    def draw(self, context):
        layout = self.layout
        bone_tool = context.scene.bone_tool
        
        layout.label(text="Add/Replace Suffix")
        layout.prop(bone_tool, "suffix_string")
        layout.prop(bone_tool, "replace_string")
        layout.operator("bone_tool.add_suffix")
        layout.operator("bone_tool.replace_string")

        layout.label(text="Reenumerate bones")
        layout.operator("bone_tool.enumerate_bones")

class OBJECT_PT_boneToolsCreation(ToolPanel):
    bl_parent_id = "OBJECT_PT_boneTools"
    bl_label = "Creation"

    def draw(self, context):
        layout = self.layout
        bone_tool = context.scene.bone_tool

        layout.label(text="Create bones from objects")
        layout.prop(bone_tool, "tip_length")
        layout.operator("bone_tool.bones_from_objects")

        layout.label(text="Create bones from verts")
        layout.prop(bone_tool, "reverse_bones")
        layout.operator("bone_tool.bones_from_verts")

class OBJECT_PT_boneToolsAlignment(ToolPanel):
    bl_parent_id = "OBJECT_PT_boneTools"
    bl_label = "Alignment"

    def draw(self, context):
        layout = self.layout
        bone_tool = context.scene.bone_tool

        layout.label(text="Align bones")
        layout.prop(bone_tool, "align_axis", text="")
        layout.operator("bone_tool.planar_align_bones")

        layout.label(text="Straighten bones")
        layout.operator("bone_tool.straighten_bones")

class OBJECT_PT_boneToolsUncategorized(ToolPanel):
    bl_parent_id = "OBJECT_PT_boneTools"
    bl_label = "Uncategorized"

    def draw(self, context):
        layout = self.layout
        bone_tool = context.scene.bone_tool

        layout.label(text="Apply automatic weights")
        layout.operator("bone_tool.reapply_auto_weights")

        layout.label(text="Parent consecutive bones")
        layout.operator("bone_tool.parent_consecutive_selected_bones")

class OBJECT_PT_vertexGroupTools(ToolPanel):
    bl_parent_id = "OBJECT_PT_riggingToolsPanel"
    bl_label = "Vertex Tools"

    def draw(self, context):
        return

class OBJECT_PT_vertexGroupToolsDiagnostics(ToolPanel):
    bl_parent_id = "OBJECT_PT_vertexGroupTools"
    bl_label = "Diagnostics"

    def draw(self, context):
        layout = self.layout
        bone_tool = context.scene.bone_tool

        layout.label(text="Check vertex groups")
        layout.operator("bone_tool.check_vertex_groups")

class OBJECT_PT_vertexGroupToolsLockedVertexGroupOperations(ToolPanel):
    bl_parent_id = "OBJECT_PT_vertexGroupTools"
    bl_label = "Locked vertex group operations"

    def draw(self, context):
        layout = self.layout
        bone_tool = context.scene.bone_tool

        layout.label(text="Add locked vertex groups")
        layout.operator("bone_tool.add_locked_vertex_groups")

        layout.label(text="Remove locked vertex groups")
        layout.operator("bone_tool.remove_locked_vertex_groups")

        layout.label(text="Replace locked vertex groups")
        layout.operator("bone_tool.replace_locked_vertex_groups")

        layout.label(text="Lock vertex groups")
        layout.operator("bone_tool.lock_selected_vertex_groups")

class OBJECT_PT_vertexGroupToolsVertexGroupOperations(ToolPanel):
    bl_parent_id = "OBJECT_PT_vertexGroupTools"
    bl_label = "Vertex group operations"

    def draw(self, context):
        layout = self.layout
        bone_tool = context.scene.bone_tool

        layout.label(text="Mirror vertex groups")
        layout.operator("bone_tool.mirror_empty_vertex_groups")

        layout.label(text="Remove all vertex groups")
        layout.operator("bone_tool.remove_vertex_groups")

        layout.label(text="Replace vertex groups")
        layout.operator("bone_tool.replace_list_vertex_groups")

class OBJECT_PT_spineRiggingTools(ToolPanel):
    bl_parent_id = "OBJECT_PT_riggingToolsPanel"
    bl_label = "Spine Rigging Tools"

    def draw(self, context):
        return

class OBJECT_PT_spineRiggingToolsCreation(ToolPanel):
    bl_parent_id = "OBJECT_PT_spineRiggingTools"
    bl_label = "Creation"

    def draw(self, context):
        layout = self.layout
        bone_tool = context.scene.bone_tool

        layout.label(text="Create spine rig")
        layout.prop(bone_tool, "start_bone_name")
        layout.prop(bone_tool, "end_bone_name")
        layout.prop(bone_tool, "bone_control_length")
        layout.prop(bone_tool, "flip_start_handles")
        layout.prop(bone_tool, "flip_end_handles")
        layout.prop(bone_tool, "twist_start_bone")
        layout.prop(bone_tool, "preserve_length")
        if not bone_tool.preserve_length:
            layout.prop(bone_tool, "handle_length")
        layout.operator("bone_tool.create_spine_rig")
        layout.operator("bone_tool.update_spline")

class OBJECT_PT_ModifierTools(ToolPanel):
    bl_parent_id = "OBJECT_PT_riggingToolsPanel"
    bl_label = "Modifier Tools"

    def draw(self, context):
        return

class OBJECT_PT_removeModifier(ToolPanel):
    bl_parent_id = "OBJECT_PT_ModifierTools"
    bl_label = "Remove Modifier"

    def draw(self, context):
        layout = self.layout
        bone_tool = context.scene.bone_tool

        layout.label(text="Remove Modifier")
        layout.prop(bone_tool, "delete_modifier_name")
        layout.operator("bone_tool.remove_modifier")

# BONE TOOLS
#########################################################################################################################################################

# Naming

class AddSuffix(Operator):
    """Add suffix to selected objects"""
    bl_idname = "bone_tool.add_suffix"
    bl_label = "Add suffix to selected bones"
    bl_options = {"REGISTER", "UNDO"}   

    def execute(self, context):
        bone_tool = context.scene.bone_tool
        from . import place_armature
        place_armature.add_suffix(context, bone_tool.suffix_string)
        return {"FINISHED"}

class ReplaceString(Operator):
    """Replace suffix with string"""
    bl_idname = "bone_tool.replace_string"
    bl_label = "Replace suffix with string"
    bl_options = {"REGISTER", "UNDO"}   

    def execute(self, context):
        bone_tool = context.scene.bone_tool
        from . import place_armature
        place_armature.replace_string(context, bone_tool.suffix_string, bone_tool.replace_string)
        return {"FINISHED"}  

class EnumerateBones(Operator):
    """Reenumerate bones"""
    bl_idname = "bone_tool.enumerate_bones"
    bl_label = "Reenumerate bones"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from . import place_armature
        place_armature.enumerate_bones(context)
        return {"FINISHED"}

# Creation

class BonesFromObjects(Operator):
    """Creates bones from selected objects"""
    bl_idname = "bone_tool.bones_from_objects"
    bl_label = "Creates bones from selected objects"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bone_tool = context.scene.bone_tool
        from . import place_armature
        place_armature.bones_from_objects(context, bone_tool.tip_length)
        return {"FINISHED"}    

class BonesFromVerts(Operator):
    """Creates bones from selected verts"""
    bl_idname = "bone_tool.bones_from_verts"
    bl_label = "Creates bones from selected verts"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bone_tool = context.scene.bone_tool
        from . import place_armature
        place_armature.bones_from_verts(context, bone_tool.reverse_bones)
        return {"FINISHED"}

# Alignment

class PlanarAligneBones(Operator):
    """Align bones on a plane using selected bone chain root's single axis"""
    bl_idname = "bone_tool.planar_align_bones"
    bl_label = "Align bones on an axis plane"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bone_tool = context.scene.bone_tool
        from . import place_armature
        place_armature.planar_align_bones(context, bone_tool.align_axis)
        return {"FINISHED"}    

class StraightenBones(Operator):
    """Straightens selected bones while preserving the start and end locations of the chain"""
    bl_idname = "bone_tool.straighten_bones"
    bl_label = "Straightens selected bones"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from . import place_armature
        place_armature.straighten_bones(context)
        return {"FINISHED"}

# Uncategorized

class ReapplyAutoWeights(Operator):
    """Applies automatic weights on selected bones"""
    bl_idname = "bone_tool.reapply_auto_weights"
    bl_label = "Automatic weights on selected"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from . import place_armature
        place_armature.reapply_auto_weights(context)
        return {"FINISHED"} 

class ParentConsecutiveSelectedBones(Operator):
    """Parents consecutively selected bones"""
    bl_idname = "bone_tool.parent_consecutive_selected_bones"
    bl_label = "Parent selected consecutive bones"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from . import place_armature
        place_armature.parent_consecutive_selected_bones(context)
        return {"FINISHED"} 

# VERTEX GROUP TOOLS
#########################################################################################################################################################

# Diagnostics

class CheckVertexGroups(Operator):
    """Check for differences in selected object's vertex groups"""
    bl_idname = "bone_tool.check_vertex_groups"
    bl_label = "Check selected vertex groups"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from . import place_armature
        place_armature.check_vertex_groups(context)
        return {"FINISHED"}

# Locked vertex group operations

class AddLockedVertexGroups(Operator):
    """Add locked vertex groups to selected objects"""
    bl_idname = "bone_tool.add_locked_vertex_groups"
    bl_label = "Add locked vertex groups"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from . import place_armature
        place_armature.add_locked_vertex_groups(context)
        return {"FINISHED"}

class RemoveLockedVertexGroups(Operator):
    """Remove selected object's locked vertex groups"""
    bl_idname = "bone_tool.remove_locked_vertex_groups"
    bl_label = "Remove locked vertex group"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from . import place_armature
        place_armature.remove_locked_vertex_groups(context)
        return {"FINISHED"}

class ReplaceLockedVertexGroups(Operator):
    """Replace selected object's locked vertex groups"""
    bl_idname = "bone_tool.replace_locked_vertex_groups"
    bl_label = "Replace locked vertex groups"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from . import place_armature
        place_armature.replace_locked_vertex_groups(context)
        return {"FINISHED"}  

class LockSelectedVertexGroups(Operator):
    """For each selected object, lock every vertex group that matches the name of those in active object"""
    bl_idname = "bone_tool.lock_selected_vertex_groups"
    bl_label = "lock vertex groups"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from . import place_armature
        place_armature.lock_selected_vertex_groups(context)
        return {"FINISHED"}

# Vertex group operations

class MirrorEmptyVertexGroups(Operator):
    """Creates mirrored vertex groups for all selected objects"""
    bl_idname = "bone_tool.mirror_empty_vertex_groups"
    bl_label = "Mirror vertex groups"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from . import place_armature
        place_armature.mirror_empty_vertex_groups(context)
        return {"FINISHED"} 

class RemoveVertexGroups(Operator):
    """Removes all selected mesh's vertex groups"""
    bl_idname = "bone_tool.remove_vertex_groups"
    bl_label = "Remove all selected vertex groups"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from . import place_armature
        place_armature.remove_vertex_groups(context)
        return {"FINISHED"}

class ReplaceListVertexGroups(Operator):
    """Replace selected object's vertex groups using a list"""
    bl_idname = "bone_tool.replace_list_vertex_groups"
    bl_label = "Replace vertex groups"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        from . import place_armature
        place_armature.replace_list_vertex_groups(context)
        return {"FINISHED"}

# SPINE RIGGING TOOLS
#########################################################################################################################################################

# Creation

class CreateSpineRig(Operator):
    """Spline ik constrain the bones between the selected start and end bones to a new spline curve. Creates two bone controls that move the start and end points of the spline"""
    bl_idname = "bone_tool.create_spine_rig"
    bl_label = "Create spine rig"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bone_tool = context.scene.bone_tool
        from . import place_armature
        place_armature.create_spine_rig(context, bone_tool.flip_start_handles, bone_tool.flip_end_handles, bone_tool.twist_start_bone, bone_tool.preserve_length, bone_tool.handle_length, bone_tool.bone_control_length, bone_tool.start_bone_name, bone_tool.end_bone_name)
        return {"FINISHED"}

class UpdateSpline(Operator):
    """Updates the spline generated from the spine rig"""
    bl_idname = "bone_tool.update_spline"
    bl_label = "Update Spline"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bone_tool = context.scene.bone_tool
        from . import place_armature
        place_armature.update_spline(context, bone_tool.flip_start_handles, bone_tool.flip_end_handles, bone_tool.preserve_length, bone_tool.handle_length)
        return {"FINISHED"}    

# MODIFIER TOOLS
#########################################################################################################################################################

# Remove Modifier

class RemoveModifier(Operator):
    """Remove the modifier with the modifier name from all selected objects"""
    bl_idname = "bone_tool.remove_modifier"
    bl_label = "Remove Modifier"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        bone_tool = context.scene.bone_tool
        from . import place_armature
        place_armature.remove_modifier(context, bone_tool.delete_modifier_name)
        return {"FINISHED"}  

classes = (
    Properties,
    OBJECT_PT_riggingToolsPanel,

    OBJECT_PT_boneTools,
    OBJECT_PT_boneToolsNaming,
    OBJECT_PT_boneToolsCreation,
    OBJECT_PT_boneToolsAlignment,
    OBJECT_PT_boneToolsUncategorized,

    OBJECT_PT_vertexGroupTools,
    OBJECT_PT_vertexGroupToolsDiagnostics,
    OBJECT_PT_vertexGroupToolsLockedVertexGroupOperations,
    OBJECT_PT_vertexGroupToolsVertexGroupOperations,    

    OBJECT_PT_spineRiggingTools, 
    OBJECT_PT_spineRiggingToolsCreation,

    OBJECT_PT_ModifierTools,
    OBJECT_PT_removeModifier,

    AddSuffix, ReplaceString,
    EnumerateBones,

    BonesFromObjects,
    BonesFromVerts,

    PlanarAligneBones,
    StraightenBones,

    ReapplyAutoWeights,
    ParentConsecutiveSelectedBones,

    CheckVertexGroups,

    AddLockedVertexGroups,
    RemoveLockedVertexGroups,
    ReplaceLockedVertexGroups,
    LockSelectedVertexGroups,

    MirrorEmptyVertexGroups,
    RemoveVertexGroups,
    ReplaceListVertexGroups,

    CreateSpineRig,
    UpdateSpline,

    RemoveModifier,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.bone_tool = PointerProperty(type=Properties)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
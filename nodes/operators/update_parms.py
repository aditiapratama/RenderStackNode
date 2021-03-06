from bpy.props import *

from RenderStackNode.utility import *


class RSN_OT_UpdateParms(bpy.types.Operator):
    """Switch Scene Camera"""
    bl_idname = "rsn.update_parms"
    bl_label = "Update Parms"

    index: IntProperty(default=0, min=0)

    task_data = None

    def reroute(self, node):
        def is_task_node(node):
            if node.bl_idname == "RSNodeTaskNode":
                print(f">> get task node {node.name}")
                return node.name

            sub_node = node.inputs[0].links[0].from_node

            return is_task_node(sub_node)

        task_node_name = is_task_node(node)
        return task_node_name

    def get_data(self):
        nt = NODE_TREE(bpy.context.space_data.edit_tree)
        task_name = self.reroute(nt.nt.nodes.active.inputs[self.index].links[0].from_node)
        self.task_data = nt.get_task_data(task_name)

    def update_image_format(self):
        if 'color_mode' in self.task_data:
            bpy.context.scene.render.image_settings.color_mode = self.task_data['color_mode']
            bpy.context.scene.render.image_settings.color_depth = self.task_data['color_depth']
            bpy.context.scene.render.image_settings.file_format = self.task_data['file_format']
            bpy.context.scene.render.film_transparent = task_data['transparent']

    def update_frame_range(self):
        if "frame_start" in self.task_data:
            bpy.context.scene.frame_start = self.task_data['frame_start']
            bpy.context.scene.frame_end = self.task_data['frame_end']
            bpy.context.scene.frame_step = self.task_data['frame_step']

    def update_render_engine(self):
        if 'engine' in self.task_data:
            bpy.context.scene.render.engine = self.task_data['engine']
            if 'samples' in self.task_data:
                if self.task_data['engine'] == "BLENDER_EEVEE":
                    bpy.context.scene.eevee.taa_render_samples = self.task_data['samples']
                elif self.task_data['engine'] == "CYCLES":
                    bpy.context.scene.cycles.samples = self.task_data['samples']

    def update_res(self):
        if 'res_x' in self.task_data:
            bpy.context.scene.render.resolution_x = self.task_data['res_x']
            bpy.context.scene.render.resolution_y = self.task_data['res_y']
            bpy.context.scene.render.resolution_percentage = self.task_data['res_scale']

    def update_camera(self):
        if 'camera' in self.task_data:
            cam_name = self.task_data['camera']
            if cam_name:
                bpy.context.scene.camera = bpy.data.objects[cam_name]
                for area in bpy.context.screen.areas:
                    if area.type == 'VIEW_3D':
                        for region in area.regions:
                            if region.type == 'WINDOW':
                                area.spaces[0].region_3d.view_perspective = 'CAMERA'
                                break
                        break

    def execute(self, context):
        self.get_data()
        self.update_camera()
        self.update_res()
        self.update_render_engine()
        self.update_frame_range()

        return {'FINISHED'}


def register():
    bpy.utils.register_class(RSN_OT_UpdateParms)


def unregister():
    bpy.utils.unregister_class(RSN_OT_UpdateParms)

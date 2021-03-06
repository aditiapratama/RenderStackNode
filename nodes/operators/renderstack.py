import os
import time

from bpy.props import *
from RenderStackNode.utility import *


class RSN_OT_RenderStackTask(bpy.types.Operator):
    """Render Tasks"""
    bl_idname = "rsn.render_stack_task"
    bl_label = "Render Stack"

    # 渲染状态获取
    _timer = None
    stop = None
    rendering = None
    # mark
    render_mark = None
    mark_index = []
    task_data = []
    # item
    frame_list = []
    frame_current = 1


    # 检查当前帧 是否大于任务预设的的帧数
    def frame_check(self):
        if self.frame_current >= self.frame_list[0]["frame_end"]:
            self.mark_index.pop(0)
            self.task_data.pop(0)
            self.frame_list.pop(0)
            if len(self.frame_list) > 0:  # 如果帧数列表未空，则继续读取下一个
                self.frame_current = self.frame_list[0]["frame_start"]
        else:
            self.frame_current += self.frame_list[0]["frame_step"]

    # 渲染状态获取
    def pre(self, dummy, thrd=None):
        self.rendering = True

    def post(self, dummy, thrd=None):
        self.rendering = False
        self.frame_check()

    def cancelled(self, dummy, thrd=None):
        self.stop = True

    # 句柄添加
    def append_handles(self):
        bpy.app.handlers.render_pre.append(self.pre)  # 检测渲染状态
        bpy.app.handlers.render_post.append(self.post)
        bpy.app.handlers.render_cancel.append(self.cancelled)
        self._timer = bpy.context.window_manager.event_timer_add(0.5, window=bpy.context.window)  # 添加计时器检测状态
        bpy.context.window_manager.modal_handler_add(self)

    def remove_handles(self):
        bpy.app.handlers.render_pre.remove(self.pre)
        bpy.app.handlers.render_post.remove(self.post)
        bpy.app.handlers.render_cancel.remove(self.cancelled)
        bpy.context.window_manager.event_timer_remove(self._timer)

    def make_path(self, context):
        blend_path = context.blend_data.filepath
        blend_name = bpy.path.basename(blend_path)[:-6]

        directory_path = os.path.dirname(bpy.data.filepath) + "\\" + f"{blend_name}_render"
        try:
            if not os.path.exists(directory_path):
                os.makedirs(directory_path)
            return directory_path

        except(Exception) as e:
            self.report({'ERROR'}, f'File Path: Path Error')
            print(directory_path, e)

    def get_postfix(self, scn):

        task = self.task_data[0]
        task_name = task['task_name']
        cam = scn.camera

        postfix = ""
        date_now = str(time.strftime("%m-%d", time.localtime()))
        time_now = str(time.strftime("%H_%M", time.localtime()))

        # if self.use_preview_render:
        #     postfix = f"{self.preview_folder_name}/"
        # else:
        #     postfix = ""

        if 'path_format' in task:
            shot_export_name = task["path_format"]
            for string in shot_export_name.split("/"):
                for r in string.split('$'):
                    if r.startswith("date"):
                        postfix += date_now + '_'
                    elif r.startswith("time"):
                        postfix += time_now + '_'
                    # camera
                    elif r.startswith("camera"):
                        postfix += cam.name + '_'
                    elif r.startswith("res"):
                        postfix += f"{scn.render.resolution_x}x{scn.render.resolution_y}" + "_"
                    elif r.startswith("ev"):
                        postfix += scn.view_settings.exposure + "_"
                    elif r.startswith("view_layer"):
                        postfix += f"{bpy.context.window.view_layer.name}" + '_'
                    elif r.startswith("task"):
                        postfix += task_name + "_"
                    else:
                        postfix += r

                if postfix.endswith("_"): postfix = postfix[:-1]
                postfix += "/"

            if postfix.endswith("/"): postfix = postfix[:-1]

        return postfix

    # 激活下一任务
    def switch2task(self, context):
        scn = context.scene
        task = self.mark_index[0]

        bpy.ops.rsn.update_parms(index=task)

        # folder path & file name
        directory = self.make_path(context)
        postfix = self.get_postfix(scn)

        frame_format = f"{self.frame_current}"
        if len(f"{self.frame_current}") < 4:
            for i in range(0, 4 - len(f"{self.frame_current}")):
                frame_format = "0" + frame_format

        scn.render.filepath = os.path.join(directory, postfix + f"_{frame_format}" + scn.render.file_extension)
        # scn.render.filepath = os.path.join(directory, f"_{frame_format}" + scn.render.file_extension)

    # init 初始化执行
    def execute(self, context):

        context.window_manager.render_stack_modal = True
        scn = context.scene
        scn.render.use_lock_interface = True

        self.stop = False
        self.rendering = False

        # 获取列表

        nt = NODE_TREE(bpy.context.space_data.edit_tree)

        for i, task in enumerate(nt.dict):
            task_data = nt.get_task_data(task_name=task)
            self.task_data.append(task_data)
            self.mark_index.append(i)

            render_list = {}

            if "frame_start" in task_data:
                render_list["frame_start"] = task_data["frame_start"]
                render_list["frame_end"] = task_data["frame_end"]
                render_list["frame_step"] = task_data["frame_step"]
            else:
                render_list["frame_start"] = 1
                render_list["frame_end"] = 1
                render_list["frame_step"] = 1

            self.frame_list.append(render_list)

        if True in (len(self.mark_index) == 0, len(self.frame_list) == 0):
            scn.render.use_lock_interface = False
            self.report({"WARNING"}, 'Nothing to render！')
            return {"FINISHED"}

        self.frame_current = self.frame_list[0]["frame_start"]
        # 添加句柄到窗口
        self.append_handles()

        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        # 计时器内事件
        if event.type == 'TIMER':
            if True in (len(self.mark_index) == 0, self.stop is True, len(self.frame_list) == 0):  # 取消或者列表为空 停止
                self.remove_handles()
                context.window_manager.render_stack_modal = False
                context.scene.render.filepath = ""
                return {"FINISHED"}

            elif self.rendering is False:  # 进行渲染
                self.switch2task(context)
                context.scene.frame_current = self.frame_current
                bpy.ops.render.render("INVOKE_DEFAULT", write_still=True)

        return {"PASS_THROUGH"}


class RSN_OT_RenderButton(bpy.types.Operator):
    bl_idname = "rsn.render_button"
    bl_label = "Render"

    use_preview_render: BoolProperty(name="use preview render",
                                     description="render prewive image to a preview folder",
                                     default=False)

    preview_folder_name:StringProperty(name = "Preview Folder Name", default = "Preview")

    render_now: BoolProperty(name="Render right now !")

    wait_time: IntProperty(name="Time to begin render",
                           description="type in how many minutes you want to render later",
                           default=0)

    @classmethod
    def poll(self, context):
        if not context.window_manager.render_stack_modal:
            return context.scene.camera is not None

    def change_shading(self):
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D' and space.shading.type == "RENDERED":
                        space.shading.type = 'SOLID'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True

        # layout.prop(self, "use_preview_render", text="Render Preview")
        # if self.use_preview_render:
        #     layout.prop(self,"preview_folder_name", text="Folder Name")

    def execute(self, context):
        blend_path = context.blend_data.filepath

        if blend_path == "":
            self.report({"ERROR"},"Save your file first!")
            return {"FINISHED"}

        else:
            if context.scene.render.engine == "octane":
                self.change_shading()
            bpy.ops.rsn.render_stack_task()

        return {'FINISHED'}

    def invoke(self, context, event):
        self.use_preview_render = False
        return context.window_manager.invoke_props_dialog(self)


def register():
    bpy.utils.register_class(RSN_OT_RenderStackTask)
    bpy.utils.register_class(RSN_OT_RenderButton)
    bpy.types.WindowManager.render_stack_modal = BoolProperty(default=False)


def unregister():
    bpy.utils.unregister_class(RSN_OT_RenderStackTask)
    bpy.utils.unregister_class(RSN_OT_RenderButton)
    del bpy.types.WindowManager.render_stack_modal

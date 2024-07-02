from pathlib import Path
import bpy
import time
import os
import logging
import math

from .import_root import (
    get_database_path,
    get_image_folder,
    import_armature,
    import_model_root,
    import_images,
)

from . import xc3_model_py

from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, EnumProperty, BoolProperty, CollectionProperty
from mathutils import Matrix


class ImportWimdo(bpy.types.Operator, ImportHelper):
    """Import a Xenoblade Switch model"""

    bl_idname = "import_scene.wimdo"
    bl_label = "Import Wimdo"

    filename_ext = ".wimdo"

    filter_glob: StringProperty(
        default="*.wimdo",
        options={"HIDDEN"},
        maxlen=255,
    )

    files: CollectionProperty(
        type=bpy.types.OperatorFileListElement, options={"HIDDEN", "SKIP_SAVE"}
    )

    game_version: EnumProperty(
        name="Game Version",
        description="The game version for the shader database",
        items=(
            ("XC1", "Xenoblade 1 DE", "Xenoblade Chronicles 1 Definitive Edition"),
            ("XC2", "Xenoblade 2", "Xenoblade Chronicles 2"),
            ("XC3", "Xenoblade 3", "Xenoblade Chronicles 3"),
        ),
        default="XC3",
    )

    pack_images: BoolProperty(
        name="Pack Images",
        description="Pack all images into the Blender file. Increases memory usage and import times but makes the Blender file easier to share by not creating additional files",
        default=True,
    )

    # TODO: Only show this if packed is unchecked
    image_folder: StringProperty(
        name="Image Folder",
        description="The folder for the imported images. Defaults to the file's parent folder if not set",
    )

    import_all_meshes: BoolProperty(
        name="Import All Meshes",
        description="Import all meshes regardless of LOD or material name",
        default=False,
    )

    def execute(self, context: bpy.types.Context):
        # Log any errors from Rust.
        log_fmt = "%(levelname)s %(name)s %(filename)s:%(lineno)d %(message)s"
        logging.basicConfig(format=log_fmt, level=logging.INFO)

        database_path = get_database_path(self.game_version)
        image_folder = get_image_folder(self.image_folder, self.filepath)

        # TODO: merge armatures?
        folder = Path(self.filepath).parent
        for file in self.files:
            abs_path = str(folder.joinpath(file.name))
            import_wimdo(
                context,
                abs_path,
                database_path,
                self.pack_images,
                image_folder,
                self.import_all_meshes,
            )
        return {"FINISHED"}


def import_wimdo(
    context: bpy.types.Context,
    path: str,
    database_path: str,
    pack_images: bool,
    image_folder: str,
    import_all_meshes: bool,
):
    start = time.time()

    database = xc3_model_py.shader_database.ShaderDatabase.from_file(database_path)
    root = xc3_model_py.load_model(path, database)

    end = time.time()
    print(f"Load Root: {end - start}")

    start = time.time()

    model_name = os.path.basename(path)
    blender_images = import_images(
        root, model_name.replace(".wimdo", ""), pack_images, image_folder, flip=True
    )
    armature = import_armature(context, root, model_name)
    import_model_root(root, blender_images, armature, import_all_meshes, flip_uvs=True)

    # Store the path to make exporting easier later.
    armature["original_wimdo"] = path

    end = time.time()
    print(f"Import Blender Scene: {end - start}")

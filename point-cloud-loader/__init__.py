bl_info = {
    "name": "Import LAS to PLY",
    "blender": (4, 2, 0),
    "category": "Import-Export",
    "version": (1, 0, 0),
    "location": "File > Import > Import LAS to PLY",
    "description": "Convert LAS point cloud files to PLY format and import to viewport",
    "Author": "Fairuz Akmal Pradana"
}

import bpy
import sys
import subprocess
import importlib

import laspy
import open3d
import numpy

from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper

# # Function to install missing libraries
# def install_and_import(module_name):
#     try:
#         importlib.import_module(module_name)
#     except ModuleNotFoundError:
#         subprocess.check_call([sys.executable, "-m", "pip", "install", module_name, "--target", "C:\\Program Files\\Blender Foundation\\Blender 4.2\\4.2\\python\\lib\\site-packages"])
#     finally:
#         globals()[module_name] = importlib.import_module(module_name)

# # Install required libraries
# install_and_import("laspy")
# install_and_import("open3d")
# install_and_import("numpy")

# Function to convert LAS to PLY
def las_to_ply(las_file, ply_file):
    las = laspy.read(las_file)
    points = np.vstack((las.x, las.y, las.z)).transpose()
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    
    if hasattr(las, 'red') and hasattr(las, 'green') and hasattr(las, 'blue'):
        colors = np.vstack((las.red, las.green, las.blue)).transpose()
        colors = colors / 65535.0
        pcd.colors = o3d.utility.Vector3dVector(colors)
    
    o3d.io.write_point_cloud(ply_file, pcd)

# Operator to invoke the file selector and perform the conversion
class LAS2PLY_OT_Converter(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.las_to_ply"
    bl_label = "Import LAS to PLY"
    filename_ext = ".las"
    
    filter_glob: StringProperty(
        default="*.las",
        options={'HIDDEN'},
        maxlen=255,
    )
    
    def execute(self, context):
        las_file = self.filepath
        ply_file = bpy.path.ensure_ext(self.filepath, ".ply")
        las_to_ply(las_file, ply_file)
        
        # Import the PLY file into Blender's viewport
        bpy.ops.import_mesh.ply(filepath=ply_file)
        
        self.report({'INFO'}, f"Successfully converted {las_file} to {ply_file} and imported into Blender")
        return {'FINISHED'}

# Add an entry in the File > Import menu
def menu_func_import(self, context):
    self.layout.operator(LAS2PLY_OT_Converter.bl_idname, text="Import LAS to PLY (.las)")

# Register and unregister the add-on
def register():
    bpy.utils.register_class(LAS2PLY_OT_Converter)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    bpy.utils.unregister_class(LAS2PLY_OT_Converter)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
    register()

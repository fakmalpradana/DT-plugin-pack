bl_info = {
    "name": "3D Custom Data Export-Import",
    "blender": (4, 2, 0),
    "category": "Import-Export",
    "author": "Fairuz Akmal Pradana",
    "description": "Imports LAS point clouds ke dalam Blender dengan atribut warna, dan Export 3D OBJ dengan koordinat ter-georeferensi.",
    "support": "COMMUNITY",
}
import pip
import bpy
import numpy as np
from bpy_extras.io_utils import ImportHelper
from bpy_extras.io_utils import ExportHelper
from bpy.types import Operator
from bpy.props import StringProperty, EnumProperty
from bpy.utils import register_class, unregister_class
from mathutils import Vector

try:
    import laspy
except ModuleNotFoundError:
    pip.main(['install', 'laspy'])
    import laspy


class ImportLASOperator(bpy.types.Operator, ImportHelper):
    """Import LAS Point Cloud"""
    bl_idname = "import_scene.las_point_cloud"
    bl_label = "Import LAS Point Cloud"
    bl_options = {'REGISTER', 'UNDO'}
    filename_ext = ".las"
    
    filter_glob: bpy.props.StringProperty(
        default="*.las",
        options={'HIDDEN'},
        maxlen=255,
    )

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        if not self.filepath:
            self.report({'ERROR'}, "File path is not set.")
            return {'CANCELLED'}
        
        # Load the LAS file
        las = laspy.read(self.filepath)
        points = np.vstack((las.x, las.y, las.z)).transpose()

        # Check if color attributes are available
        if las.red is not None and las.green is not None and las.blue is not None:
            colors = np.vstack((las.red, las.green, las.blue)).transpose()
            colors = (colors / 65535.0).astype(np.float32)  # Normalize to [0,1]
        else:
            colors = np.full((points.shape[0], 3), 1.0, dtype=np.float32)  # Default to white

        # Calculate the centroid
        centroid = np.mean(points, axis=0)

        # Translate the points so the centroid becomes (0,0,0)
        translated_points = points - centroid

        # Create a new mesh
        mesh = bpy.data.meshes.new(name="LAS_PointCloud")
        obj = bpy.data.objects.new("LAS_PointCloud", mesh)
        context.collection.objects.link(obj)

        # Create mesh data
        vertices = [(x, y, z) for x, y, z in translated_points]
        edges = []
        faces = []

        # Create the mesh
        mesh.from_pydata(vertices, edges, faces)
        mesh.update()

        # Create a new color attribute
        color_layer = mesh.color_attributes.new(name="Col", type='FLOAT_COLOR', domain='POINT')

        # Assign colors to vertices
        color_layer.data.foreach_set("color", [color for c in colors for color in (*c, 1.0)])

        # Update the mesh to apply changes
        mesh.update()

        self.report({'INFO'}, f"LAS file imported with colors and translated to local coordinates: {self.filepath}")
        return {'FINISHED'}
    
def load_obj(file_path):
    """Load the vertex coordinates from an OBJ file."""
    vertices = []
    with open(file_path, 'r') as file:
        for line in file:
            if line.startswith('v '):  # Vertex line
                parts = line.strip().split()
                vertex = [float(parts[1]), float(parts[2]), float(parts[3])]
                vertices.append(vertex)
    return np.array(vertices)

def save_obj(file_path, vertices, original_file):
    """Save the transformed vertices to a new OBJ file."""
    with open(file_path, 'w') as file:
        with open(original_file, 'r') as original:
            for line in original:
                if line.startswith('v '):
                    vertex = vertices.pop(0)
                    file.write(f"v {vertex[0]:.6f} {vertex[1]:.6f} {vertex[2]:.6f}\n")
                else:
                    file.write(line)

def calculate_centroid(vertices):
    """Calculate the centroid of the given vertices."""
    return np.mean(vertices, axis=0)

def calculate_obj_centroid(filepath):
    vertices = []

    with open(filepath, 'r') as file:
        for line in file:
            if line.startswith('v '):
                parts = line.split()
                vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])

    vertices = np.array(vertices)
    centroid = np.mean(vertices, axis=0)
    
    return centroid

def translate_to_target(vertices, target_coords):
    """Translate the vertices to the target coordinates, maintaining the relative position."""
    centroid = calculate_centroid(vertices)
    translation_vector = target_coords #- centroid
    return vertices + translation_vector

class ExportOBJOperator(bpy.types.Operator, ExportHelper, ImportHelper):
    """Export selected objects as OBJ with georeferenced coordinates"""
    bl_idname = "export_scene.custom_obj_with_geo"
    bl_label = "Export Georeferenced OBJ"
    filename_ext = ".obj"

    # File path for the reference LAS file
    reference_las_filepath: StringProperty(
        name="Reference LAS File",
        description="Select the reference LAS file",
        subtype='FILE_PATH',
        default=""
    )

    filter_glob: StringProperty(
        default="*.obj",
        options={'HIDDEN'},
        maxlen=255,
    )

    # Axis selection properties
    forward_axis: EnumProperty(
        name="Forward Axis",
        items=(
            ('X', "X Forward", ""),
            ('Y', "Y Forward", ""),
            ('Z', "Z Forward", ""),
            ('NEGATIVE_X', "-X Forward", ""),
            ('NEGATIVE_Y', "-Y Forward", ""),
            ('NEGATIVE_Z', "-Z Forward", ""),
        ),
        default='Y',
    )

    up_axis: EnumProperty(
        name="Up Axis",
        items=(
            ('X', "X Up", ""),
            ('Y', "Y Up", ""),
            ('Z', "Z Up", ""),
            ('NEGATIVE_X', "-X Up", ""),
            ('NEGATIVE_Y', "-Y Up", ""),
            ('NEGATIVE_Z', "-Z Up", ""),
        ),
        default='Z',
    )

    def execute(self, context):
        # Load the reference LAS file and calculate its centroid
        with laspy.open(self.reference_las_filepath) as las:
            point_data = las.read()
            las_centroid = calculate_centroid(np.vstack((point_data.x, point_data.y, point_data.z)).transpose())
        
        for obj in bpy.context.selected_objects:
            # Get the vertices of the object in world coordinates
            mesh = obj.data
            vertices = np.array([obj.matrix_world @ vert.co for vert in mesh.vertices])
            
            # Translate vertices to align with the LAS centroid
            translated_vertices = translate_to_target(vertices, las_centroid)
            
            # Apply the translation back to the object
            for i, vert in enumerate(mesh.vertices):
                vert.co = obj.matrix_world.inverted() @ Vector(translated_vertices[i])

        # Export the selected objects to OBJ
        bpy.ops.wm.obj_export(filepath=self.filepath, forward_axis=self.forward_axis, up_axis=self.up_axis)

        obj = load_obj(self.filepath)
        obj_centroid = calculate_obj_centroid(self.filepath)

        target_coords = las_centroid

        # translated_vertices0 = translate_to_target(obj, -obj_centroid)
        translated_vertices = translate_to_target(obj, target_coords)

        output_path = self.filepath
        output_path = output_path.replace('.obj', '_georeferenced.obj')

        save_obj(file_path=output_path, vertices=translated_vertices.tolist(), original_file=self.filepath)



        return {'FINISHED'}




class ImportLASPanel(bpy.types.Panel):
    """Panel for importing LAS point clouds"""
    bl_label = "Import LAS Point Cloud"
    bl_idname = "IMPORT_PT_las_point_cloud"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Import-Export'

    def draw(self, context):
        layout = self.layout
        layout.operator("import_scene.las_point_cloud")

def menu_func_import(self, context):
    self.layout.operator(ImportLASOperator.bl_idname, text="Import LAS Point Cloud (.las)")
    
def menu_func_export(self, context):
    self.layout.operator(ExportOBJOperator.bl_idname, text="Export Georeferenced 3D Model (.obj)")

def register():
    bpy.utils.register_class(ImportLASOperator)
    bpy.utils.register_class(ImportLASPanel)
    bpy.utils.register_class(ExportOBJOperator)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.utils.unregister_class(ImportLASOperator)
    bpy.utils.unregister_class(ImportLASPanel)
    bpy.utils.unregister_class(ExportOBJOperator)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()

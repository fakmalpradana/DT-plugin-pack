import numpy as np
import open3d as o3d

dataname="C:/DT/data-sample/Area_1.pcd"

pcd = o3d.io.read_point_cloud(dataname)
pcd.estimate_normals(search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.1, max_nn=30))

# Poisson Method
poisson_mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=8, width=0, scale=1.0, linear_fit=False)[0]

bbox = pcd.get_axis_aligned_bounding_box()
# p_mesh_crop = poisson_mesh.crop(bbox)
p_mesh_crop = poisson_mesh

o3d.io.write_triangle_mesh("C:/DT/data-sample/Area_1_c.obj", p_mesh_crop)

# o3d.visualization.draw_geometries([p_mesh_crop])
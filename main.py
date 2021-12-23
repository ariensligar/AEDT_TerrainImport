# -*- coding: utf-8 -*-
"""
Created on Tue Dec 14 14:48:07 2021

Script will generate terrain and import shape file into HFSS

@author: asligar
"""


from terrain import terrain_prep
from shape import shape_prep
from aedt_utils import AEDTutils
from pyaedt import Hfss

import pyvista as pv

###############################################################################
#
# BEGIN USER INPUTS
#
###############################################################################

input_folder = "./shape_files/portland/Buildings"

#import terrain, centered at this location
#this would also corrospond to the shape file if you it could be read automatically
lat_lon = [45.545029694364544, -122.65121842741738] 
terrain_radius = 8000 # meters
create_hfss_proj=True

include_shape_files = True
truncate_shapes = True #if you only want to import a certain number of buildings, use this as True
number_of_shapes= 2000 #only import this number of buildings, use -1

###############################################################################
#
# END USER INPUTS
#
###############################################################################


def main(input_folder,
         lat_lon,
         create_hfss_proj=create_hfss_proj,
         truncate_shapes=False,
         number_of_shapes=1000,
         terrain_radius=1000,
         include_shape_files=True):
    #instiate terrain module
    terrainprep = terrain_prep()
    terrain_geo = terrainprep.get_terrain2(lat_lon,max_radius=terrain_radius,grid_size = 30)
    terrain_stl = terrain_geo['file_name']
    terrain_mesh = terrain_geo['mesh']
    
    if include_shape_files:
        shapeprep = shape_prep(input_folder)
        shapes = shapeprep.get_shapes(terrain_mesh=terrain_mesh,truncate_shapes=truncate_shapes,number_of_shapes=number_of_shapes)
        
    #create HFSS project
    if create_hfss_proj:
        with Hfss(non_graphical=False, new_desktop_session=False,solution_type='SBR+') as aedtapp:
            aedt = AEDTutils(aedtapp,project_name="terrain_import",version='2021.2')
            
            #import STL files
            imported_name_terrain = aedt.import_stl(terrain_stl)
            #add materials to project
            aedt.add_material('terrain',5,0.01,0)
            #assign boundary conditions to imported objects
            aedt.assign_boundary(imported_name_terrain,'terrain',bc_name= "terrain_bc")
            
            if include_shape_files:
                imported_name_buildings = aedt.import_stl(shapes['file_name'])
                aedt.add_material('buildings',4,0.01,0)
                aedt.assign_boundary(imported_name_buildings,'buildings',bc_name= "buildings_bc")
            
        
    #plot in pyvista, just for visualization
    plotter = pv.Plotter()
    if include_shape_files:
        plotter.add_mesh(shapes['mesh'],color='grey',specular=.9)
    plotter.add_mesh(terrain_geo['mesh'],color='brown',ambient=.5,specular=.9,roughness=.5)
    plotter.show()

if __name__ == "__main__":
    main(input_folder,
         lat_lon,
         create_hfss_proj,
         truncate_shapes=truncate_shapes,
         number_of_shapes=number_of_shapes,
         terrain_radius=terrain_radius,
         include_shape_files=include_shape_files)
# -*- coding: utf-8 -*-
"""
Created on Tue Dec 14 14:48:07 2021

Script will generate terrain and import shape file into HFSS

@author: asligar
"""

from buildings import buildings_prep
from roads import road_prep
from terrain import terrain_prep
from shape import shape_prep
from aedt_utils import AEDTutils
from pyaedt import Hfss
import os
import json
import pickle
import pyvista as pv
from pyaedt import Desktop

###############################################################################
#
# BEGIN USER INPUTS
#
###############################################################################



env_name = 'test_env'

#import terrain, centered at this location
#this would also corrospond to the shape file if you it could be read automatically
lat_lon = [45.545029694364544, -122.65121842741738] 
terrain_radius = 250 # meters
create_hfss_proj=True


# IF you want to use a pre-defined shape files
include_shape_files = False
truncate_shapes = True #if you only want to import a certain number of buildings, use this as True
number_of_shapes= 2000 #only import this number of buildings, use -1
input_folder = "./shape_files/portland/Buildings" #input folder if shape files is being imported

# if you want the buildings to be created from OSM
include_osm_buildings = True

# if you want to creates roads based on OSM
including_osm_roads = True

###############################################################################
#
# END USER INPUTS
#
###############################################################################


def main(lat_lon,
         env_name = 'default',
         create_hfss_proj=create_hfss_proj,
         input_folder=None,
         truncate_shapes=False,
         number_of_shapes=1000,
         terrain_radius=1000,
         include_shape_files=True,
         include_osm_buildings = True,
         including_osm_roads=True):
    
    
    base_path = os.path.dirname(os.path.realpath(__file__))

    output_path = base_path + '/environment/' + env_name + '/'
    
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    
    parts_dict = {}
    #instiate terrain module
    terrainprep = terrain_prep(cad_path = output_path)
    terrain_geo = terrainprep.get_terrain(lat_lon,max_radius=terrain_radius,grid_size = 30)
    terrain_stl = terrain_geo['file_name']
    terrain_mesh = terrain_geo['mesh']
    terrain_dict  = {'file_name':terrain_stl,'color':'brown','material':'earth'}
    parts_dict['terrain'] = terrain_dict
    print(terrain_stl)
    if include_shape_files:
        shapeprep = shape_prep(input_folder)
        shapes = shapeprep.get_shapes(terrain_mesh=terrain_mesh,truncate_shapes=truncate_shapes,number_of_shapes=number_of_shapes)
        
        
    if include_osm_buildings:
        print('Generating Building Geometry')
        buildingprep = buildings_prep(cad_path = output_path)
        building_geo =  buildingprep.generate_buildings(lat_lon,
                                                          terrain_mesh,
                                                          max_radius=terrain_radius*.8)
        building_stl = building_geo['file_name']
        building_mesh = building_geo['mesh']
        building_dict  = {'file_name':building_stl,'color':'grey','material':'concrete'}
        parts_dict['buildings'] = building_dict
        print(building_stl)
    if including_osm_roads:
        
        print('Generating Road Geometry')
        roadprep = road_prep(cad_path = output_path)
        road_geo = roadprep.create_roads(lat_lon ,
                                         terrain_mesh,
                                         max_radius=terrain_radius,
                                         z_offset=2,
                                         road_step=1,
                                         road_width=6)
        
        road_stl = road_geo['file_name']
        print(road_stl)
        road_mesh = road_geo['mesh']
        road_graph = road_geo['graph']    
        road_dict  = {'file_name':road_stl,'color':'black','material':'asphalt'}
        parts_dict['roads'] = road_dict
                

    print(parts_dict)
    json_path = output_path + env_name + '.json'
    
    
    scene= {'name':env_name,
            'version':1,
            "type": "environment",
            'center_lat_lon':lat_lon,
            'radius':terrain_radius,
            'road_network':f"{env_name}.road_network",
            'parts':parts_dict}
    
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(scene, f, indent=4)
        
    road_network_path = output_path + env_name + '.road_network'
    with open(road_network_path, 'wb') as f:
        road = {'graph':road_graph}
        pickle.dump(road, f)
    

    
    print('Done...')
    
    print('Viewing Geometry...')
    #view results
    plt = pv.Plotter()
    plt.add_mesh(building_mesh, cmap='gray', label = r"Buildings")
    plt.add_mesh(road_mesh, cmap="bone", label = r"Roads")
    plt.add_mesh(terrain_mesh, cmap='terrain',label = r"Terrain")#clim=[00, 100]
    plt.add_legend()
    plt.add_axes( line_width=2, xlabel='X', ylabel='Y', zlabel='Z')
    plt.add_axes_at_origin(x_color=None, y_color=None, z_color=None, line_width=2, labels_off=True)
    plt.show(interactive=True)

    #create HFSS project
    if create_hfss_proj:
        aedt_version = '2022.1'
        aedt = AEDTutils(project_name=env_name,
                         design_name='design',
                         version=aedt_version,
                         path =  output_path)
        #instance of HFSS
        aedt.create_aedt_proj(parts_dict)
        


if __name__ == "__main__":
    main(lat_lon,
         env_name = env_name,
         create_hfss_proj=create_hfss_proj,
         input_folder=input_folder,
         truncate_shapes=truncate_shapes,
         number_of_shapes=number_of_shapes,
         terrain_radius=terrain_radius,
         include_shape_files=include_shape_files,
         include_osm_buildings=include_osm_buildings,
         including_osm_roads=including_osm_roads)
    

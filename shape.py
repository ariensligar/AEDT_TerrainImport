# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------------- #
#      Written by : Arien Sligar (arien.sligar@ansys.com)
#      Last updated : 07.07.2020
# --------------------------------------------------------------------------------- #

import numpy as np
import pyvista as pv
import shapefile




class shape_prep(object):
    """
    contains all basic funcitons needed for interacting with AEDT
    """
    def __init__(self,cad_path):
        """
        intialize path
        """
        #import buildings from shape file
        sf = shapefile.Reader(cad_path)
        self.sf= sf
        self.cad_path=cad_path

    def get_shapes(self,terrain_mesh=None,truncate_shapes=False,number_of_shapes=1000):
        
        
        #get ceneter of shape files, used to offset all geometry to center/origin
        bbox = self.sf.bbox
        center_x = (bbox[2]-bbox[0])/2+bbox[0]
        center_y = (bbox[3]-bbox[1])/2+bbox[1]
        
        shapes = self.sf.shapes()
        
        building_meshes= pv.PolyData() #empty location where all building meshses are stored
        
        if truncate_shapes:
            if len(shapes)>number_of_shapes:
                shapes = shapes[:number_of_shapes] #if you want to truncate to a set amount of shapes
        
        for n, each in enumerate(shapes):
            building_height=np.random.randint(5,30) #can I get this value from the file?
            if n%1000==0:
                print(f'{n} of {len(shapes)} shapes')
                
            #offset center location
            points = np.array(each.points)
            points[:,0]-= center_x
            points[:,1]-= center_y
            zeros = np.zeros((points.shape[0],1)) 
            #add z dimension to array
            points = np.hstack((points,zeros)) #create [x,y,z] points
            
            if terrain_mesh:
                #The shape files do not have z/elevation postion. So for them to align to the
                #terrain we need to first get the position of the terrain at the xy position of shape file
                #this will align the buildins so they sit on the terrain no matter the location
                elevation_on_outline = []
                
                #check every point on the building shape for z elevation location
                for point in points:
                    #shoot ray to look for intersection point
                    start_ray = [point[0],point[1],-300]
                    stop_ray = [point[0],point[1],4000]
                    # Create geometry to represent ray trace
                    #ray = pv.Line(start, stop) #only use for visualization
                    #point where xy position of shape intersects terrain mesh
                    intersection_point, ind = terrain_mesh.ray_trace(start_ray, stop_ray)
                    if len(intersection_point)==0: #if doesnt 
                        elevation_on_outline.append(0)
                    else:
                        z_surface_location = intersection_point.flatten()[2]
                        elevation_on_outline.append(z_surface_location)
                #find lowest point on building outline to align location
                min_elevation = np.min(elevation_on_outline)
                max_elevation = np.max(elevation_on_outline)
                delta_elevation = max_elevation-min_elevation
                
                #change z position to minimum elevation of terrain
                points[:,2] = min_elevation
        
            try:
                if n ==1345:
                    test=1
                print(f'Building {n}')
                cloud = pv.PolyData(points)
                surf_2d = cloud.delaunay_2d() #create 2D surface of building footprint
                #extrude 2D shape to building hieght
                #addint the delta_elevation, to make sure the minimum building hight is building_height above terain
                if surf_2d.n_cells>1:
                    surf_3d = surf_2d.extrude([0, 0, building_height+delta_elevation],capping=True) 
                    building_meshes+=surf_3d #add to buildings mesh
            except:
                print(f'Building {n} cannot be created, Skipping')
        building_stl_filename = 'building_temp.stl'
        
        #save stl file to later be imported into HFSS
        building_meshes.save(building_stl_filename, binary=True)

        return {'file_name':building_stl_filename,'mesh':building_meshes}
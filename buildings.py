# -*- coding: utf-8 -*-
"""
Created on Mon Mar  7 08:12:48 2022

@author: asligar
"""

# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------------- #
#      Written by : Arien Sligar (arien.sligar@ansys.com)
#      Last updated : 06.15.2020
# --------------------------------------------------------------------------------- #

import numpy as np
import osmnx as ox
import pyvista as pv
import utm
import sys
import vtk
import os




class buildings_prep(object):
    """
    contains all basic funcitons needed for interacting with AEDT
    """
    def __init__(self,cad_path):
        """
        dfgd
        """

        self.cad_path=cad_path

    def create_building_roof(self,all_pos):
        '''
        Creates a filled in polygon from outline
        includes concave and convex shapes
        '''
        points = vtk.vtkPoints()
        for each in all_pos:
            points.InsertNextPoint(each[0],each[1], each[2])
        
        # Create the polygon
        polygon = vtk.vtkPolygon()
        polygon.GetPointIds().SetNumberOfIds(len(all_pos)) #make a quad
        for n in range(len(all_pos)):
            polygon.GetPointIds().SetId(n, n)
        
        # Add the polygon to a list of polygons
        polygons = vtk.vtkCellArray()
        polygons.InsertNextCell(polygon)
        
        # Create a PolyData
        polygonPolyData = vtk.vtkPolyData()
        polygonPolyData.SetPoints(points)
        polygonPolyData.SetPolys(polygons)
        
        # Create a mapper and actor
        mapper = vtk.vtkPolyDataMapper()
        
        mapper.SetInputData(polygonPolyData)
        
        triFilter = vtk.vtkTriangleFilter()
        # let's filter the polydata
        triFilter.SetInputData( polygonPolyData)
        triFilter.Update()
        
        polygonPolyDataFiltered = triFilter.GetOutput()
        roof =pv.PolyData(polygonPolyDataFiltered)
        return roof



    
    def generate_buildings(self,center_lat_lon,terrain_mesh,max_radius=500):

        gdf = ox.geometries.geometries_from_point(center_lat_lon, tags={'building': True},dist = max_radius )
        utm_center = utm.from_latlon(center_lat_lon[0], center_lat_lon[1])
        center_offset_x = utm_center[0]
        center_offset_y = utm_center[1]
        

        
        if len(gdf)==0:
            print("No Buildings Exists in Selected Geometry")
            return {'file_name':None,'mesh':None}
        else:
            
            gdf_proj = ox.project_gdf(gdf)
            
            geo = gdf_proj['geometry']
            try:
                levels = gdf_proj['building:levels']
                levels= levels.array
            except:
                levels = [1] * len(geo)
            try:
                height = gdf_proj['height']
                height = height.array
            except:
                height = [10] * len(geo)


            temp = [levels,height]
            geo = geo.array
            
            
            building_meshes= pv.PolyData() #empty location where all building meshses are stored
            all_buildings = []
    
            print('\nGenerating Buildings')
            skipped_buildings = []
            for n, building in enumerate(geo):
                #print(str(n))
                outline=[]
                g = geo[n]

                #try:
                if hasattr(g, 'exterior'):
                    outer = g.exterior


                
                
                    xpos = np.array(outer.xy[0])
                    ypos = np.array(outer.xy[1])
                    l = levels[n]
                    h = height[n]
                    
                    points = np.zeros((np.shape(outer.xy)[1],3))
                    points[:,0] = xpos
                    points[:,1] = ypos
                    points[:,0]-= center_offset_x
                    points[:,1]-= center_offset_y
    
    
                    delta_elevation=0
                    if terrain_mesh:
                        
                        buffer = 10 #additional distance so intersection test is further away than directly on surface
                        bb_terrain = terrain_mesh.bounds
                        start_z =  bb_terrain[4]-buffer
                        stop_z = bb_terrain[5]+buffer
                        
                        #The shape files do not have z/elevation postion. So for them to align to the
                        #terrain we need to first get the position of the terrain at the xy position of shape file
                        #this will align the buildins so they sit on the terrain no matter the location
                        elevation_on_outline = []
                        
                        #check every point on the building shape for z elevation location
                        for point in points:
                            #shoot ray to look for intersection point
                            start_ray = [point[0],point[1],start_z]
                            stop_ray = [point[0],point[1],stop_z]
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
     
                                
        
                    num_percent_bins = 40
                    percent = np.round((n+1)/(len(geo))*100,decimals=1)
                    perc_done= int(num_percent_bins*percent/100)
                    perc_left = num_percent_bins-perc_done
                    percent_symbol1 =  "." * perc_left
                    percent_symbol2 =  "#" * perc_done
                
                    i=percent_symbol2+percent_symbol1 + ' '+str(percent)+'% '
                    print(f"\rPercent Complete:{i}",end="")
                    #print("\r"+str(cur_elevation))
                    sys.stdout.flush()
                    
                    #create closed and filled polygon from outline of building
                    roof = self.create_building_roof(points)
                    if np.isnan(float(h))==False:
                        extrude_h =float(h)*2
                    elif np.isnan(float(l))==False:
                        extrude_h = float(l)*10
                    else:
                        extrude_h=15.0
                        
                    outline= pv.lines_from_points(points,close=True)
                
                    vert_walls = outline.extrude([0,0,extrude_h+delta_elevation],inplace=False)
    
                
                
                    roof_location = np.array([0,0,extrude_h+delta_elevation])
                    roof.translate(roof_location,inplace=True)
                    
                    building_meshes +=vert_walls
                    building_meshes+=roof
                    #all_buildings.append(vert_walls)
                    #all_buildings.append(roof)
    
                    # cloud = pv.PolyData(points)
                    # surf_2d = cloud.delaunay_2d() #create 2D surface of building footprint
    
                    # #extrude 2D shape to building hieght
                    # #addint the delta_elevation, to make sure the minimum building hight is building_height above terain
                    # if surf_2d.n_cells>1:
                    #     if np.isnan(float(h))==False:
                    #         extrude_h =float(h)
                    #     elif np.isnan(float(l))==False: #level used if height doesn't exist
                    #         extrude_h = float(l)*3 #hight per level
                    #     else:
                    #         extrude_h=4.0
                    #     surf_3d = surf_2d.extrude([0, 0, extrude_h+delta_elevation],capping=True) 
                    #     #building_meshes += cloud
                    #     building_meshes+=surf_3d #add to buildings mesh
    
                    # except:
                    #     print(f'Building {n} cannot be created, Skipping')
                

                    


                    
            el = building_meshes.points[:,2]

            building_meshes["Elevation"] = el.ravel(order="F")
            #move_vec = np.array([-utm_center[0],-utm_center[1],0])
            #full_scene.translate(move_vec)
            file_out = self.cad_path + '\\buildings_temp.stl'
            relative_path = os.path.relpath(file_out)
            print(relative_path)
            building_meshes.save(file_out, binary=True)
            
            return {'file_name':'buildings_temp.stl','mesh':building_meshes,'temp':temp}
    

        
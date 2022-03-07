# -*- coding: utf-8 -*-
"""
Created on Mon Mar  7 08:13:18 2022

@author: asligar
"""

# -*- coding: utf-8 -*-
"""
Created on Mon Jan 31 10:57:02 2022

@author: asligar
"""

import numpy as np
import pyvista as pv
import osmnx as ox
import sys
import utm
import os




class road_prep():
    """
    contains all basic funcitons needed for interacting with AEDT
    """
    def __init__(self,cad_path):
        """
        dfgd
        """
        self.cad_path = cad_path


    def create_roads(self,center_lat_lon,
                     terrain_mesh,
                     max_radius=1000, 
                     z_offset=0,
                     road_step=1,
                     road_width=5):
        '''
        Creates a filled in polygon from outline
        includes concave and convex shapes
        '''
        
        graph= ox.graph_from_point(center_lat_lon, 
                                dist=max_radius,
                                simplify=False,
                                network_type='all',
                                clean_periphery =True)
        
        g_projected = ox.project_graph(graph)


        utm_center = utm.from_latlon(center_lat_lon[0], center_lat_lon[1])
        center_offset_x = utm_center[0]
        center_offset_y = utm_center[1]

        nodes, edges = ox.graph_to_gdfs(g_projected)
        lines = []


        buffer = 10 #additional distance so intersection test is further away than directly on surface
        bb_terrain = terrain_mesh.bounds
        start_z =  bb_terrain[4]-buffer
        stop_z = bb_terrain[5]+buffer

        
        line = pv.PolyData()
        road_ends = pv.PolyData()
        # convert each edge into a line
        count=0
        for idx, row in edges.iterrows():
            count+=1
            num_percent_bins = 40
            percent = np.round((count)/(len(edges))*100,decimals=1)

            perc_done= int(num_percent_bins*percent/100)
            perc_left = num_percent_bins-perc_done
            percent_symbol1 =  "." * perc_left
            percent_symbol2 =  "#" * perc_done
        
            i=percent_symbol2+percent_symbol1 + ' '+str(percent)+'% '
            print(f"\rPercent Complete:{i}",end="")
            #print("\r"+str(cur_elevation))
            sys.stdout.flush()
            
            x_pts = row['geometry'].xy[0]
            y_pts = row['geometry'].xy[1]

            z_pts = np.zeros(len(x_pts))
            for n in range(len(z_pts)):
                
                #lon=row['geometry'].xy[0][n]
                #lat=row['geometry'].xy[1][n]
                #print(lat)
                #abs_pos = utm.from_latlon(lat, lon)

                x_pts[n] = row['geometry'].xy[0][n]-center_offset_x
                y_pts[n] = row['geometry'].xy[1][n]-center_offset_y
                start_ray = [x_pts[n],y_pts[n],start_z]
                stop_ray = [x_pts[n],y_pts[n],stop_z]
                points, ind = terrain_mesh.ray_trace(start_ray, stop_ray)
                if len(points)!=0:
                    z_surface_location = points.flatten()[2]
                    z_pts[n] = z_surface_location+z_offset
                    #z_pts[n] = z_offset
            pts = np.column_stack((x_pts, y_pts, z_pts))
            #always 2 points, linear interpolate to higher number of points
            dist = np.sqrt(np.power(pts[0][0]-pts[1][0],2)+np.power(pts[0][1]-pts[1][1],2)+np.power(pts[0][2]-pts[1][2],2))
            if dist>road_step:
                num_steps = int(dist/road_step)
                xpos = np.linspace(pts[0][0],pts[1][0],num=num_steps)
                ypos = np.linspace(pts[0][1],pts[1][1],num=num_steps)
                zpos = np.linspace(pts[0][2],pts[1][2],num=num_steps)
                pts = np.column_stack((xpos, ypos, zpos))

            
            line += pv.lines_from_points(pts)
            end_shape = pv.Circle(road_width,resolution=16).delaunay_2d()
            road_ends += end_shape.translate(pts[0],inplace=False)
            end_shape = pv.Circle(road_width,resolution=16).delaunay_2d()
            road_ends += end_shape.translate(pts[-1],inplace=False)
            lines.append(line)

        roads = line.ribbon(width=road_width,normal=[0,0,1])
        #roads = line.tube(radius=road_width,capping=True)
        #roads = line
        


        roads+=road_ends
        #roads = roads.merge(road_ends)
        #roads = roads.clean()
        el = roads.points[:,2]

        roads["Elevation"] = el.ravel(order="F")
        #roads= combined_lines.intersect(terrain_mesh)
        file_out = self.cad_path + '\\roads_temp.stl'
        roads.save(file_out)
        file_out = os.path.abspath(file_out)
        relative_path = os.path.relpath(file_out)
        return {'file_name':'roads_temp.stl','mesh':roads,'graph':g_projected}

        
        
        
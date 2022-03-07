# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------------- #
#      Written by : Arien Sligar (arien.sligar@ansys.com)
#      Last updated : 07.07.2020
# --------------------------------------------------------------------------------- #

import numpy as np
import pyvista as pv
import utm
import os
import glob
import urllib as ul
import zipfile
import re

import srtm

class terrain_prep(object):
    """
    contains all basic funcitons needed for interacting with AEDT
    """
    def __init__(self,cad_path='./'):
        """
        intialize path
        """

        self.cad_path=cad_path

    def get_terrain_flat(self,max_radius=500,buffer_percent=0):
        """
        temporary, just creating a plane
        """
        

        max_radius = max_radius*(1+ buffer_percent)
        pointa = [-max_radius,-max_radius, 0.0]
        pointb = [-max_radius, max_radius, 0.0]
        pointc = [max_radius,max_radius, 0.0]
        pointd = [max_radius, -max_radius, 0.0]
        rect = pv.Rectangle([pointa, pointb, pointc, pointd])

        terrain_mesh = rect.triangulate(inplace=False)
        
        file_out = self.cad_path + '\\terrain_temp.stl'
        terrain_mesh.save(file_out)
        
        return {'file_name':file_out,'mesh':terrain_mesh}
    



    
    
    def get_terrain(self,center_lat_lon,max_radius=500,grid_size = 5,buffer_percent=0,region='01'):
        """
        temporary, just creating a plane
        """


        utm_center = utm.from_latlon(center_lat_lon[0], center_lat_lon[1])
        print('Generating Terrain')
        max_radius = max_radius*(buffer_percent+1)
        all_data,all_lat_lon,all_utm = self.get_elevation(center_lat_lon,
                                                                  max_radius=max_radius,
                                                                  grid_size = grid_size,
                                                                  srtm_source = 'srtm1')
        
        all_data = np.nan_to_num(all_data,nan=-32768)
        print('Processing Geometry')
        xyz=[]
        for lat_idx in range(all_data.shape[0]):
            for lon_idx in range(all_data.shape[1]):
                
                latlat_utm_centered = all_utm[lat_idx][lon_idx][0]-utm_center[0]
                lonlon_utm_centered = all_utm[lat_idx][lon_idx][1]-utm_center[1]
                
                if all_data[lat_idx][lon_idx] != -32768: #this is missing data from srtm, don't add if it doesn't exist
                    xyz.append([latlat_utm_centered,lonlon_utm_centered,all_data[lat_idx][lon_idx]])
        xyz=np.array(xyz)
        
        file_out = self.cad_path + '/terrain_temp.stl'
        print('saving STL as ' + file_out)
        terrain_mesh = pv.PolyData(xyz)
        terrain_mesh = terrain_mesh.delaunay_2d(tol = 10/(2*max_radius)/2)#tolerance, srtm is 30meter, so as a fraction of total size this would be 30/2/radius
        terrain_mesh = terrain_mesh.smooth(n_iter=100,relaxation_factor=0.04)
        

        el = terrain_mesh.points[:,2]

        terrain_mesh["Elevation"] = el.ravel(order="F")
        
        
        terrain_mesh.save(file_out)
        relative_path = 'terrain_temp.stl'
        relative_path = os.path.relpath(file_out)
        file_out = os.path.abspath(file_out)
        return {'file_name':'terrain_temp.stl','mesh':terrain_mesh}
    def get_srtm_from_web(self,requested_file_name):
        strm1_url_base = 'https://srtm.kurviger.de/SRTM1/'
        #strm1_url_base = 'http://dds.cr.usgs.gov/srtm/version2_1/SRTM1/'
        regions = 7 #total number of possible regions
        all_urls = []
        for each in range(regions):
            all_urls.append(strm1_url_base + 'Region_0' + str(each+1) +'/')
        
        all_files = {}
        file_regions = {}
        all_contents = []
        for url in all_urls:
            print(url)
            url_stream = ul.request.urlopen(url)
            contents = url_stream.read()
            all_contents.append(contents)
            url_stream.close()
        
            urls_in_region= re.findall('href="(.*?)"', contents.decode('utf-8'))
            for file in urls_in_region:
                if file.endswith('.hgt.zip'):
                    all_files[file]=(url+file)
                    file_regions[file]=(url.replace(strm1_url_base,"").replace('/',''))


        if requested_file_name in all_files.keys():
            save_path = self.cad_path + 'srtm_data/' + file_regions[requested_file_name] + '/'
            if not os.path.exists(save_path):
                os.makedirs(save_path)
            print('downloading ' + all_files[requested_file_name])
            ul.request.urlretrieve (all_files[requested_file_name], save_path + requested_file_name)
            
            return save_path + requested_file_name
        else:
            print('file not found, verify lat/lon ' + all_files[requested_file_name])
            return None
        
    def does_local_srtm_exist(self,file_name):
        base_path = self.cad_path + 'srtm_data/'
        files = glob.glob(base_path+'**//'+file_name,recursive = True)
        if len(files)==1:
            return files[0]
        else:
            return False

    def read_elevation_from_file(self,hgt_file_zip,latlon,srtm_source = 'srtm1'):
        directory = self.cad_path + 'srtm_data/'
        if srtm_source =='srtm1':
            samples = 3601
        elif srtm_source== 'srtm3':
            samples = 1201
        else:
            samples = 1201

        
        local_copy_zip = self.does_local_srtm_exist(hgt_file_zip)
        hgt_file = hgt_file_zip.replace('.zip','')
        if local_copy_zip:
            local_copy_hgt = self.does_local_srtm_exist(hgt_file)
            if local_copy_hgt:
                extracted_file = local_copy_hgt
            else:
                archive = zipfile.ZipFile(local_copy_zip, 'r')
                extracted_file = archive.extract(hgt_file,path=directory)
        else:
            print(hgt_file + ' is missing, attempting to download')
            print('http://dds.cr.usgs.gov/srtm/version2_1/SRTM1/')
            local_copy_zip = self.get_srtm_from_web(hgt_file_zip)
            archive = zipfile.ZipFile(local_copy_zip, 'r')
            extracted_file = archive.extract(hgt_file,path=directory)
    
        with open(extracted_file, 'rb') as hgt_data:
            # HGT is 16bit signed integer(i2) - big endian(>)
            elevations = np.fromfile(hgt_data, np.dtype('>i2'), samples*samples)\
                                    .reshape((samples, samples))
    
            #elevations[elevations == -32768] = 0 #this is missing data set to this value. I can either set to zero or try and interpolat later
            
        lat_start = int(np.floor(latlon[0]))
        lat_stop = lat_start+1
        lon_start = int(np.floor(latlon[1]))
        lon_stop = lon_start+1
        
        lat_vals = np.linspace(lat_start,lat_stop,samples)
        lon_vals = np.linspace(lon_start,lon_stop,samples)
        
                
        return [elevations,lat_vals,lon_vals]

    def find_nearest(self,array, value):
        array = np.asarray(array)
        idx = (np.abs(array - value)).argmin()
        return idx
    
    def get_elevation(self,
                      center_lat_lon,
                      max_radius=500,
                      grid_size=3,
                      srtm_source = 'srtm1'):
        

        utm_center = utm.from_latlon(center_lat_lon[0], center_lat_lon[1])
        #assume never at boundary of zone number or letter
        zone_letter = utm.latitude_to_zone_letter(center_lat_lon[0])
        zone_number = utm.latlon_to_zone_number(center_lat_lon[0],center_lat_lon[1])
        print(zone_letter)
        print(zone_number)
        print(utm_center)
        utm_x_min = utm_center[0]-max_radius
        utm_x_max = utm_center[0]+max_radius
        
        utm_y_min = utm_center[1]-max_radius
        utm_y_max = utm_center[1]+max_radius
        
        
        sample_grid_size = grid_size#meters
        num_samples = int(np.ceil(max_radius*2/sample_grid_size))
        x_samples = np.linspace(utm_x_min,utm_x_max,int(num_samples))
        y_samples = np.linspace(utm_y_min,utm_y_max,int(num_samples))
        elevation_data = srtm.get_data(local_cache_dir="tmp_cache")
        
        all_data = np.zeros((num_samples,num_samples))
        all_utm = np.zeros((num_samples,num_samples,2))
        all_lat_lon = np.zeros((num_samples,num_samples,2))
        print('Terrain Points...')
        last_displayed=-1
        for n, x in enumerate(x_samples):
            for m, y in enumerate(y_samples):
                
                percent_complete = int((n*num_samples + m)/(num_samples*num_samples)*100)
                if (percent_complete%10==0 and percent_complete!=last_displayed):
                    last_displayed = percent_complete
                    print(str(percent_complete) + '%')
                zone_letter = utm.latitude_to_zone_letter(center_lat_lon[0])
                zone_number = utm.latlon_to_zone_number(center_lat_lon[0],center_lat_lon[1])
                current_lat_lon = utm.to_latlon(x, y, zone_number, zone_letter)
                all_data[n,m] = elevation_data.get_elevation(current_lat_lon[0], current_lat_lon[1])
                all_lat_lon[n,m] =current_lat_lon
                all_utm[n,m] =[x,y]
        print(str(100) + '% - Done')
        return all_data, all_lat_lon, all_utm
    


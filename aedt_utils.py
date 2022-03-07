# -*- coding: utf-8 -*-
"""
Created on Mon Nov 22 11:46:09 2021

interaction between main script and aedt is defined here, assumes
that the desktop is open, uses current active project

@author: asligar
"""

from pyaedt import Hfss
from pyaedt import Desktop
import json
import os
import uuid
import fnmatch
import numpy as np



class AEDTutils:
    def __init__(self,project_name='project1',design_name='design1',version ="2022.1",path='./'):
        
        if not os.path.exists('./tmp_cache/'):
            os.makedirs('./tmp_cache/')
        self.save_path = './tmp_cache/'
        
        self.aedtapp = None
        with Desktop(specified_version=version,non_graphical=False,new_desktop_session=False,close_on_exit=False) as d:

            
            if project_name in d.project_list():
                orig_design_name=design_name
                increment=1
                while design_name in d.design_list(project_name):
                    design_name = orig_design_name+str(increment)
                    increment+=1
                        
        self.project_name = project_name
        self.design_name = design_name
        self.version = version
        self.path = path

    def create_aedt_proj(self,scn_elements):

        #instance of HFSS
        with Hfss(projectname=self.project_name,
                      designname=self.design_name,
                      non_graphical=False, 
                      new_desktop_session=False,
                      specified_version=self.version,
                      solution_type='SBR+') as aedtapp:
            
            self.aedtapp = aedtapp
            self.setup_design()
            self.initalize_aedt_parts(scn_elements)
            

        


    def initalize_aedt_parts(self,scene_elements):
        #add materials

        #self.add_all_material()
        
        
        for part in scene_elements:
            stl_filename =self.path + scene_elements[part]['file_name']
            print(f"importing {stl_filename}")
            mesh_import = self.import_stl(stl_filename,cs_name='Global')

            
   
        




    
    def setup_design(self):
        oEditor = self.aedtapp.odesign.SetActiveEditor("3D Modeler")
        oEditor.SetModelUnits(["NAME:Units Parameter","Units:=", "meter","Rescale:=", False])
        self.time_var_name = "time_var"
        self.time = 0
        self.add_or_edit_variable(self.time_var_name,str(self.time)+'s')
                

    def release_desktop(self):
        self.aedtapp.release_desktop(close_projects=False, close_on_exit=False)

    def diff(self,li1, li2): 
        """
        used to return difference between two lists
        commonly used for when HFSS doesn't return the name of objects, for example
        when an stl file is imported, this function can be used to compare list
        of objects before and after import to return the list of imported objects

        returns: difference between lists
        """
        li_dif = [i for i in li1 + li2 if i not in li1 or i not in li2] 
        return li_dif 
    
    def add_material(self,mat_name,er,tand,cond):
        """
        adds a material to HFSS with the properties of permitivity and dielectric
        loss tanget only. If the material already exists, it will update it with
        the new properties
        """
        
        oDefinitionManager = self.aedtapp.oproject.GetDefinitionManager()

        #existing_materials = oDefinitionManager.GetInUseProjectMaterialNames()

        if oDefinitionManager.DoesMaterialExist(mat_name):
            oDefinitionManager.EditMaterial(mat_name, 
            [
                "NAME:"+mat_name,
                "CoordinateSystemType:=", "Cartesian",
                "BulkOrSurfaceType:="    , 1,
                [
                    "NAME:PhysicsTypes",
                    "set:="            , ["Electromagnetic"]
                ],
                "permittivity:="    , str(er),
                "dielectric_loss_tangent:=", str(tand),
                "bulk_conductivity:=", str(cond)
            ])
        else:
            oDefinitionManager.AddMaterial(
                [
                    "NAME:"+mat_name,
                    "CoordinateSystemType:=", "Cartesian",
                    "BulkOrSurfaceType:="    , 1,
                    [
                        "NAME:PhysicsTypes",
                        "set:="            , ["Electromagnetic"]
                    ],
                    "permittivity:="    , str(er),
                    "dielectric_loss_tangent:=", str(tand),
                    "bulk_conductivity:=", str(cond)
                ])
    def add_all_material(self):
        """
        adds a material to HFSS with the properties of permitivity and dielectric
        loss tanget only. If the material already exists, it will update it with
        the new properties
        """
        
        with open('./Lib/materials.json') as f:
            materials = json.load(f)
        

        for mat_name in materials['materials']:
            
            material_values = materials['materials'][mat_name]


            # ToDo need to support multi layered dielectrics
            t=1;er_real=1;er_im=0;mu_real=1;mu_imag=0;cond=0
            if 'thickness' in material_values.keys():
                t = material_values['thickness']
            if 'relEpsReal' in material_values.keys():
                er_real = material_values['relEpsReal']
            if 'relEpsImag' in material_values.keys():
                er_im = material_values['relEpsImag']
            if 'relMuReal' in material_values.keys():
                mu_real = material_values['relMuReal']
            if 'relMuImag' in material_values.keys():
                mu_imag= material_values['relMuImag']
            if 'conductivity' in material_values.keys():
                cond = material_values['conductivity']

            material_str = f'DielectricLayers {t},{er_real},{er_im},{mu_real},{mu_imag},{cond}'
            if 'backing' in material_values.keys():
                backing_mat = material_values['backing']
                material_str = f'{material_str}  {backing_mat}'
            if 'roughness' in material_values.keys() and 'height_standard_dev' in material_values.keys():
                roughness= material_values['roughness']
                std_dev = material_values['height_standard_dev']
    
            tand = abs(er_im/er_real)
            if mat_name =='pec':
                pass
            elif mat_name =='absorber':
                pass
            else:
                print('adding material: ' + mat_name)
                self.add_material(mat_name,er_real,tand,cond)
        
    def assign_material(self,obj_names,material):
        oEditor = self.aedtapp.odesign.SetActiveEditor("3D Modeler")
        if isinstance(obj_names, list):
            for each in obj_names:
                vol = oEditor.GetObjectVolume(each)
                if vol!=0.0:
                    oEditor.ChangeProperty(
                        [
                            "NAME:AllTabs",
                            [
                                "NAME:Geometry3DAttributeTab",
                                [
                                    "NAME:PropServers", 
                                    each
                                ],
                                [
                                    "NAME:ChangedProps",
                                    [
                                        "NAME:Material",
                                        "Value:="        , "\"" + material + "\""
                                    ]
                                ]
                            ]
                        ])
        else:
            vol = oEditor.GetObjectVolume(obj_names)
            if vol!=0.0:
                oEditor.ChangeProperty(
                    [
                        "NAME:AllTabs",
                        [
                            "NAME:Geometry3DAttributeTab",
                            [
                                "NAME:PropServers", 
                                obj_names
                            ],
                            [
                                "NAME:ChangedProps",
                                [
                                    "NAME:Material",
                                    "Value:="        , "\"" + material + "\""
                                ]
                            ]
                        ]
                    ])
        
    def assign_boundary(self,objects,material,bc_name="layered_bc1"):
        """
        assigns infinintly thick layered impedance boundary or pec boundary, 1 sided only type being used
        current, eventually expand to include 2 sided boundaries
        """
        oModule = self.aedtapp.odesign.GetModule("BoundarySetup")

        if material=="pec":
            existing_boundary_name = oModule.GetBoundariesOfType('Perfect E')
            n=1
            original_name = bc_name
            while bc_name in existing_boundary_name:
                bc_name = original_name + str(n)
                n+=1
            oModule.AssignPerfectE(
                [
                    "NAME:"+bc_name,
                    "Objects:="        , objects
                ])    
        else:
            existing_boundary_name = oModule.GetBoundariesOfType('Layered Impedance')
            n=1
            original_name = bc_name
            while bc_name in existing_boundary_name:
                bc_name = original_name + str(n)
                n+=1
            oModule.AssignLayeredImp(
                [
                    "NAME:"+bc_name,
                    "Objects:="        , objects,
                    "Frequency:="        , "0GHz",
                    "Roughness:="        , "0um",
                    "IsTwoSided:="        , False,
                    [
                        "NAME:Layers",
                        [
                            "NAME:Layer1",
                            "LayerType:="        , "Infinite",
                            "Thickness:="        , "1um",
                            "Material:="        , material
                        ]
                    ]
                ])
        return bc_name

    def set_tx_rx(self,tx_wildcard="tx",rx_wildcard="rx"):
        """
        Set Excitation to be used in the simulation to only excite the Tx antennas
        that way we don't need to run a simulation for every Tx-Rx and Rx-Tx pair
        only Tx to Rx.
        """
        oModule = self.aedtapp.odesign.GetModule("BoundarySetup")
        
        all_excitations = oModule.GetExcitationsOfType("Antenna Port")

        rx_str = ""
        tx_str = ""
        rx_list = []
        tx_list = []
        #make lists of all rx and tx antennas
        for each in all_excitations:
            #any port that has a "rx" in it is assigned rx, otherwise assign to be tx
            if rx_wildcard in each.lower():
                rx_list.append(str(each))
                rx_str = rx_str + str(each) + ","
            else:
                tx_list.append(str(each))

        #remove trailing comma
        rx_str = rx_str[:-1]    
        all_tx_rx_lists = ["NAME:SBRTxRxSettings"]

        #generate a the list of strings so all Tx and all Rx antennas pairs will be created
        for n, tx in enumerate(tx_list):
            all_tx_rx_lists.append(
                [
                    "NAME:Tx/Rx List "+str(n),
                    "Tx Antenna:="        , tx,
                    "Rx Antennas:="        , rx_str
                ])

        #set all antenna ports with the name 'tx' in them to be transmitters and similiar for 'rx'
        oModule.SetSBRTxRxSettings(    all_tx_rx_lists)
    def insert_antenna(self,name,ffd_file =None, beamwidth_el=None,beamwidth_az=None,polarization='Vertical',cs="Global"):
        """
        this creates a single parmetric antenna component and inserts into coordinate system

        returns name of inserted antenna
        """
        uid = uuid.uuid4()
        oEditor = self.aedtapp.odesign.SetActiveEditor("3D Modeler")
        previous_def_name = oEditor.Get3DComponentDefinitionNames()

        ###################
        #
        # TEMPORARY, FFD WITH SINGLE FREQ POINT WILL NOT WORK IN AEDT
        # MOST  FFD USED FOR RTR ARE SINGLE POINTS, FOR NW JUST USE BEAMWIDTH
        ##################
        if ffd_file is not None:
            ffd_file = None
            beamwidth_el = 120
            beamwidth_az = 120
        # 
        # REMOVE WHEN FIXED
        #####################
        if ffd_file is not None:
            ffd_file = os.path.abspath(ffd_file)
            ant_type = 'File Based Antenna'
            map_instance_param = 'NotVariable'
            ant_def =   [
            			"NAME:NativeComponentDefinitionProvider",
            			"Type:="		, "File Based Antenna",
            			"Unit:="		, "meter",
            			"Is Parametric Array:="	, False,
            			"Size:="		, "1meter",
            			"MatchedPortImpedance:=", "50ohm",
            			"Representation:="	, "Far Field",
            			"ExternalFile:="	, ffd_file
                        ]
        
        else:
            ant_type = 'Parametric Beam'
            map_instance_param = 'DesignVariable'
            ant_def = [
                        "NAME:NativeComponentDefinitionProvider",
                        "Type:="        , ant_type,
                        "Unit:="        , "meter",
                        "Is Parametric Array:="    , False,
                        "Size:="        , "0.1meter",
                        "MatchedPortImpedance:=", "50ohm",
                        "Polarization:="    , polarization,
                        "Representation:="    , "Far Field",
                        "Vertical BeamWidth:="    , f'{beamwidth_el}deg',
                        "Horizontal BeamWidth:=", f'{beamwidth_az}deg'
                        ]
            
        

        oEditor.InsertNativeComponent(
            [
                "NAME:InsertNativeComponentData",
                "TargetCS:="        , cs,
                "SubmodelDefinitionName:=", name,
                [
                    "NAME:ComponentPriorityLists"
                ],
                "NextUniqueID:="    , 0,
                "MoveBackwards:="    , False,
                "DatasetType:="        , "ComponentDatasetType",
                [
                    "NAME:DatasetDefinitions"
                ],
                [
                    "NAME:BasicComponentInfo",
                    "ComponentName:="    , name,
                    "Company:="        , "",
                    "Company URL:="        , "",
                    "Model Number:="    , "",
                    "Help URL:="        , "",
                    "Version:="        , "1.0",
                    "Notes:="        , "",
                    "IconType:="        , ant_type
                ],
                [
                    "NAME:GeometryDefinitionParameters",
                    [
                        "NAME:VariableOrders"
                    ]
                ],
                [
                    "NAME:DesignDefinitionParameters",
                    [
                        "NAME:VariableOrders"
                    ]
                ],
                [
                    "NAME:MaterialDefinitionParameters",
                    [
                        "NAME:VariableOrders"
                    ]
                ],
                "MapInstanceParameters:=", map_instance_param,
                "UniqueDefinitionIdentifier:=", str(uid),
                "OriginFilePath:="    , "",
                "IsLocal:="        , False,
                "ChecksumString:="    , "",
                "ChecksumHistory:="    , [],
                "VersionHistory:="    , [],
                ant_def,
                [
                    "NAME:InstanceParameters",
                    "GeometryParameters:="    , "",
                    "MaterialParameters:="    , "",
                    "DesignParameters:="    , ""
                ]
            ])
        
        curr_def_name = oEditor.Get3DComponentDefinitionNames()
        def_name = self.diff(curr_def_name,previous_def_name) #get the current 3D component name
        instance = oEditor.Get3DComponentInstanceNames(def_name[0])[0]
        print(instance)
        return instance
    
    

        
    def import_stl(self,file_name,cs_name='Global'):
        self.aedtapp.modeler.set_working_coordinate_system(cs_name)
        full_stl_path = os.path.abspath(file_name)
        oEditor = self.aedtapp.odesign.SetActiveEditor("3D Modeler")
        all_objects_before_import = oEditor.GetMatchedObjectName("*")
        oEditor.Import(
            [
                "NAME:NativeBodyParameters",
                "HealOption:="        , 0,
                "Options:="        , "-1",
                "FileType:="        , "UnRecognized",
                "MaxStitchTol:="    , -1,
                "ImportFreeSurfaces:="    , False,
                "GroupByAssembly:="    , False,
                "CreateGroup:="        , True,
                "STLFileUnit:="        , "meter",
                "MergeFacesAngle:="    , 0.02,
                "HealSTL:="        , False,
                "ReduceSTL:="        , False,
                "ReduceMaxError:="    , 0,
                "ReducePercentage:="    , 100,
                "PointCoincidenceTol:="    , 1E-06,
                "CreateLightweightPart:=", True,
                "ImportMaterialNames:="    , False,
                "SeparateDisjointLumps:=", False,
                "SourceFile:="        , full_stl_path
            ])
        all_objects_after_import = oEditor.GetMatchedObjectName("*")
        name_of_objects_imported = self.diff(all_objects_before_import,all_objects_after_import )
        return name_of_objects_imported

        
    def convert_to_3d_comp(self,name,cs_name,comp_name='comp1'):
        
        oModule = self.aedtapp.odesign.GetModule("BoundarySetup")
        
        #reutrns boundaries in format ['name',boundary type, 'name2', boundary type]
        all_boundaries = oModule.GetBoundaries()
        all_boundaries = all_boundaries[::2]
        #becuase I need boundaries to create 3D component, no easy way to get
        #bondaries only associated with this part, so I will just assume
        #based on previous functions that any boundary created with this part will
        #contain the part name.
        boundaries_to_include = []

        for bc in all_boundaries:
            if fnmatch.fnmatch(bc, comp_name+'*'):
                boundaries_to_include.append(bc)
        
        oEditor = self.aedtapp.odesign.SetActiveEditor("3D Modeler")
        
        previous_def_name = oEditor.Get3DComponentDefinitionNames()
        oEditor.ReplaceWith3DComponent(
                [
                    "NAME:ReplaceData",
                    "ComponentName:="    , comp_name,
                    "Company:="        , "",
                    "Company URL:="        , "",
                    "Model Number:="    , "",
                    "Help URL:="        , "",
                    "Version:="        , "1.0",
                    "Notes:="        , "",
                    "IconType:="        , "",
                    "Owner:="        , "Arien Sligar",
                    "Email:="        , "",
                    "Date:="        , "11:20:05 AM  Dec 03, 2021",
                    "HasLabel:="        , False,
                    "IncludedParts:="    , name,
                    "HiddenParts:="        , [],
                    "IncludedCS:="        , [cs_name],
                    "ReferenceCS:="        , cs_name,
                    "IncludedParameters:="    , [],
                    "IncludedDependentParameters:=", [],
                    "ParameterDescription:=", []
                ], 
                [
                    "NAME:DesignData",
                    "Boundaries:="		, boundaries_to_include
                ], 
                [
                    "NAME:ImageFile",
                    "ImageFile:="        , ""
                ])
        curr_def_name = oEditor.Get3DComponentDefinitionNames()
        def_name = self.diff(curr_def_name,previous_def_name) #get the current 3D component name
        instances = oEditor.Get3DComponentInstanceNames(def_name[0])
        return instances #
    
    def add_or_edit_variable(self,name,value):
        self.aedtapp[name]=value
    
    def add_dataset(self,name,data):
        '''
        Adds a data set in HFSS. If a data set already exists, it will first
        delete it, then add it
        Parameters
        ----------
        name : str
            name of data set to be created or edited.
        data : 2d list
            values used in data set.
        Returns
        -------
        None.
        '''
        

        temp_data = ["NAME:Coordinates"]
        for each in data:
            temp_data.append(["NAME:Coordinate","X:=", float(each[0]),"Y:=",
                float(each[1])])        
        ds = ["NAME:"+ name,temp_data]
    
        if self.aedtapp.odesign.HasDataset(name) == True:
            self.aedtapp.odesign.EditDataset(name,ds)
        else:
            self.aedtapp.odesign.AddDataset(ds)
    
    def move(self,object_name,pos_ds_names,reference_cs='Global'):
        if pos_ds_names:
            if 'x' in pos_ds_names.keys():
                x=f"pwl({pos_ds_names['x']},{self.time_var_name})"
            else:
                x='0'
            if 'y' in pos_ds_names.keys():
                y=f"pwl({pos_ds_names['y']},{self.time_var_name})"
            else:
                y='0'
            if 'z' in pos_ds_names.keys():
               z=f"pwl({pos_ds_names['z']},{self.time_var_name})"
            else:
               z='0'
        oEditor = self.aedtapp.odesign.SetActiveEditor("3D Modeler")
        self.aedtapp.modeler.set_working_coordinate_system(reference_cs)
        oEditor.Move(
            [
                "NAME:Selections",
                "Selections:="        , object_name,
                "NewPartsModelFlag:="    , "Model"
            ], 
            [
                "NAME:TranslateParameters",
                "TranslateVectorX:="    , x,
                "TranslateVectorY:="    , y,
                "TranslateVectorZ:="    , z
            ])
       
    def move_3dcomp(self,name,vector,units='meter'):
         """
         used for moving any 3D component along a vector
         mainly used to offset a Rx antenna lambda/2 away
         """
         vec_x = vector[0]
         vec_y = vector[1]
         vec_z = vector[2]
 
         oEditor = self.aedtapp.odesign.SetActiveEditor("3D Modeler")
         oEditor.Move(
             [
                 "NAME:Selections",
                 "Selections:="        , name,
                 "NewPartsModelFlag:="    , "Model"
             ],
             [
                 "NAME:TranslateParameters",
                 "TranslateVectorX:="    , str(vec_x)+units,
                 "TranslateVectorY:="    , str(vec_y)+units,
                 "TranslateVectorZ:="    , str(vec_z)+units
             ])
    def rotate(self,object_name,rot_ds_name,axis='X',reference_cs='Global'):
        rotate=f"pwl({rot_ds_name},{self.time_var_name})*1deg"

        oEditor = self.aedtapp.odesign.SetActiveEditor("3D Modeler")
        self.aedtapp.modeler.set_working_coordinate_system(reference_cs)
        oEditor.Rotate(
        [
            "NAME:Selections",
            "Selections:="        , object_name,
            "NewPartsModelFlag:="    , "Model"
        ], 
        [
            "NAME:RotateParameters",
            "RotateAxis:="        , axis,
            "RotateAngle:="        , rotate
        ])

   
    
    def create_cs_dataset(self,cs_name,pos_ds_names=None,euler_ds_names=None,reference_cs='Global',order='ZYZ'):
        oEditor = self.aedtapp.odesign.SetActiveEditor("3D Modeler")
        
        self.aedtapp.modeler.set_working_coordinate_system(reference_cs)
        
        exisiting_cs = oEditor.GetCoordinateSystems()
        
        if cs_name in exisiting_cs:
            return cs_name
        
        if pos_ds_names:
            if 'x' in pos_ds_names.keys():
                x=f"pwl({pos_ds_names['x']},{self.time_var_name})"
            else:
                x='0'
            if 'y' in pos_ds_names.keys():
                y=f"pwl({pos_ds_names['y']},{self.time_var_name})"
            else:
                y='0'
            if 'z' in pos_ds_names.keys():
               z=f"pwl({pos_ds_names['z']},{self.time_var_name})"
            else:
               z='0'
        else:
            x='0'
            y='0'
            z='0'
        
        if euler_ds_names:
            if 'phi' in euler_ds_names.keys():
                phi=f"pwl({euler_ds_names['phi']},{self.time_var_name})*1deg"
            else:
                phi='0deg'
            if 'theta' in euler_ds_names.keys():
                theta = f"pwl({euler_ds_names['theta']},{self.time_var_name})*1deg"
            else:
                theta='0deg'
            if 'psi' in euler_ds_names.keys():
                psi = f"pwl({euler_ds_names['psi']},{self.time_var_name})*1deg"
            else:
                psi='0deg'
        else:
            phi='0deg'
            theta='0deg'
            psi='0deg'
        orig_name = cs_name
        incrment = 1
        while cs_name in exisiting_cs:
            cs_name = orig_name + '_'+str(incrment)
            incrment+=1
        else: #creates new CS 

            oEditor.CreateRelativeCS(
                [
                    "NAME:RelativeCSParameters",
                    "Mode:="        , "Euler Angle "+ order,
                    "OriginX:="        , x,
                    "OriginY:="        , y,
                    "OriginZ:="        , z,
                    "Psi:="            , psi,
                    "Theta:="        , theta,
                    "Phi:="            , phi
                ], 
                [
                    "NAME:Attributes",
                    "Name:="        , cs_name
                ])

        self.aedtapp.modeler.set_working_coordinate_system(cs_name)
        return cs_name


    def insert_setup(self,simulation_params=None,setup_name = "Setup1"):
        """
        insert a solution setup, these settings can be modified as needed
        """
        oModule = self.aedtapp.odesign.GetModule("AnalysisSetup")

        if simulation_params is None:
            simulation_params = {}
            simulation_params['sol_freq'] =28.0
            simulation_params['range_res'] =1
            simulation_params['range_period'] =100
            simulation_params['vel_res'] =1
            simulation_params['vel_min'] =-20
            simulation_params['vel_max'] =20
            simulation_params['ray_density'] =0.1
            simulation_params['bounces'] =3
            
        oModule.InsertSetup("HfssDriven", 
            [
                "NAME:"+ setup_name,
                "IsEnabled:="        , True,
                [
                    "NAME:MeshLink",
                    "ImportMesh:="        , False
                ],
                "IsSbrRangeDoppler:="    , True,
                "SbrRangeDopplerWaveformType:=", "PulseDoppler",
                "SbrRangeDopplerTimeVariable:=", self.time_var_name,
                "SbrRangeDopplerCenterFreq:=", f"{simulation_params['sol_freq']}",
                "SbrRangeDopplerRangeResolution:=", f"{simulation_params['range_res']}meter",
                "SbrRangeDopplerRangePeriod:=", f"{simulation_params['range_period']}meter",
                "SbrRangeDopplerVelocityResolution:=", f"{simulation_params['vel_res']}m_per_sec",
                "SbrRangeDopplerVelocityMin:=", f"{simulation_params['vel_min']}m_per_sec",
                "SbrRangeDopplerVelocityMax:=", f"{simulation_params['vel_max']}m_per_sec",
                "DopplerRayDensityPerWavelength:=", simulation_params['ray_density'],
                "MaxNumberOfBounces:="    , simulation_params['bounces'],
                "FastFrequencyLooping:=", False
            ])

        return setup_name
    
    def insert_parametric_sweep(self,time_start=None,time_stop=None,time_step=None,setup_name='Setup1'):
            """
            create parametric sweep setup for the time values specified in the file
            exported from scanner for each time step

            returns name of parametric sweep
            """
            
            if time_start is None:
                time_start = self.time_stamps[0]
            if time_stop is None:
                time_stop = self.time_stamps[-1]
            if time_step is None:
                time_step = self.time_stamps[1]-self.time_stamps[0]
                
            oModule = self.aedtapp.odesign.GetModule("Optimetrics")
            sweep_str = "LIN " + str(time_start) + "s " + str(time_stop) + "s " + str(time_step) + "s"
            para_sweep_name = "Full_Time_Sweep"
            original_name = para_sweep_name
            all_para_setup_names = oModule.GetSetupNames()
            n=1
            while para_sweep_name in all_para_setup_names:
                para_sweep_name = original_name + str(n)
                n+=1
            oModule = self.aedtapp.odesign.GetModule("Optimetrics")
            oModule.InsertSetup("OptiParametric", 
                [
                    "NAME:"+para_sweep_name,
                    "IsEnabled:="        , True,
                    [
                        "NAME:ProdOptiSetupDataV2",
                        "SaveFields:="        , False
                    ],
                    [
                        "NAME:StartingPoint"
                    ],
                    "Sim. Setups:="        , [setup_name],
                    [
                        "NAME:Sweeps",
                        [
                            "NAME:SweepDefinition",
                            "Variable:="        , self.time_var_name,
                            "Data:="        , sweep_str,
                            "OffsetF1:="        , False,
                            "Synchronize:="        , 0
                        ]
                    ],
                    [
                        "NAME:Sweep Operations"
                    ],
                    [
                        "NAME:Goals"
                    ]
                ])

            return para_sweep_name
        
        
    def assign_color(self,object_names,color=None):
        """
        Assign a  color to an imported object, used for
        the enviroment so all parts of enciroment don't look identical color,
        if color is None, a random color will be assigned
        """

        oEditor = self.aedtapp.odesign.SetActiveEditor("3D Modeler")
        if isinstance(object_names, list):
            for each in object_names:
                oEditor.ChangeProperty(
                    [
                        "NAME:AllTabs",
                        [
                            "NAME:Geometry3DAttributeTab",
                            [
                                "NAME:PropServers",
                                each
                            ],
                            [
                                "NAME:ChangedProps",
                                [
                                    "NAME:Color",
                                    "R:="            , np.random.randint(0,255),
                                    "G:="            , np.random.randint(0,255),
                                    "B:="            , np.random.randint(0,255)
                                ]
                            ]
                        ]
                    ])
        else:
            oEditor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:Geometry3DAttributeTab",
                        [
                            "NAME:PropServers",
                            object_names
                        ],
                        [
                            "NAME:ChangedProps",
                            [
                                "NAME:Color",
                                "R:="            , np.random.randint(0,255),
                                "G:="            , np.random.randint(0,255),
                                "B:="            , np.random.randint(0,255)
                            ]
                        ]
                    ]
                ])
            
    def group(self,group_name,object_to_group):
        """
        creates a group in the 3D modeler based on the
        objects listed. Help organize the modeler tree
        """
        oEditor = self.aedtapp.odesign.SetActiveEditor("3D Modeler")
        #input expects a string, convert list to comma deliminted string
        if isinstance(object_to_group, list):
            objects_string = ','.join(object_to_group )
        assigned_name = oEditor.CreateGroup(
            [
                "NAME:GroupParameter",
                "ParentGroupID:="    , "Model",
                "Parts:="        , "",
                "SubmodelInstances:="    , objects_string,
                "Groups:="        , ""
            ])

        #rename group
        oEditor.ChangeProperty(
            [
                "NAME:AllTabs",
                [
                    "NAME:Attributes",
                    [
                        "NAME:PropServers",
                        assigned_name
                    ],
                    [
                        "NAME:ChangedProps",
                        [
                            "NAME:Name",
                            "Value:="        , group_name
                        ]
                    ]
                ]
            ])
        
    def add_radar_sensor(self,sensor,ref_cs):
        base_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        radar_base_path = f'{base_path}/radar_module/'
        if sensor.type == "file":
            for tx_idx in range(sensor.numTx):
                pos = sensor.tx_pos[tx_idx]
                if sensor.tx_has_ffd:
                    ant_name = self.insert_antenna(f'tx_{tx_idx}',
                                                ffd_file =radar_base_path + sensor.tx_ffd[tx_idx],
                                                cs=ref_cs)
                else:
                    ant_name = self.insert_antenna(f'tx_{tx_idx}',
                                                beamwidth_az = sensor.Tx_hpbwHorizDeg,
                                                beamwidth_el = sensor.Tx_hpbwVertDeg,
                                                cs=ref_cs)
                self.move_3dcomp(ant_name,pos,units='meter')
                
            for rx_idx in range(sensor.numRx):
                pos = sensor.rx_pos[rx_idx]
                if sensor.rx_has_ffd:
                    ant_name = self.insert_antenna(f'rx_{rx_idx}',
                                                ffd_file =radar_base_path + sensor.rx_ffd[rx_idx],
                                                cs=ref_cs)
                else:
                    ant_name = self.insert_antenna(f'rx_{rx_idx}',
                                                beamwidth_az = sensor.Rx_Az_hpbwHorizDeg,
                                                beamwidth_el = sensor.Rx_Az_hpbwVertDeg,
                                                cs=ref_cs)
                self.move_3dcomp(ant_name,pos,units='meter')
        else: #parametric locations (defined by  spacing)

            #only 1 tx supported for parametric location radar module
            ant_name = self.insert_antenna('tx_1',
                                        beamwidth_az = sensor.Tx_hpbwHorizDeg,
                                        beamwidth_el = sensor.Tx_hpbwVertDeg,
                                        cs=ref_cs)
            self.move_3dcomp(ant_name,[0,0,0],units='meter')
                
            for rx_idx in range(sensor.numRx_Az):
                pos =[0, rx_idx*sensor.Rx_Az_spacing_meter,0]

                ant_name = self.insert_antenna(f'rx_az_{rx_idx}',
                                            beamwidth_az = sensor.Rx_Az_hpbwHorizDeg,
                                            beamwidth_el = sensor.Rx_Az_hpbwVertDeg,
                                            cs=ref_cs)
                self.move_3dcomp(ant_name,pos,units='meter')
                
            for rx_idx in range(sensor.numRx_El):
                pos =[0, 0,rx_idx*sensor.Rx_El_spacing_meter]

                ant_name = self.insert_antenna(f'rx_el_{rx_idx}',
                                            beamwidth_az = sensor.Rx_El_hpbwHorizDeg,
                                            beamwidth_el = sensor.Rx_El_hpbwVertDeg,
                                            cs=ref_cs)
                self.move_3dcomp(ant_name,pos,units='meter')

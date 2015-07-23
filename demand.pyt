import arcpy

# Replace a layer/table view name with a path to a dataset (which can be a layer file) or create the layer/table view within the script
# The following inputs are layers or table views: "Structure_Catchment", "Properties_Riparian"
# arcpy.SpatialJoin_analysis(target_features="Structure_Catchment",join_features="Properties_Riparian",out_feature_class="Z:/Water Transactions SNAP/Data/Navarro River/Navarro Model - Mill.gdb/Structures_RiparianFrontage",join_operation="JOIN_ONE_TO_MANY",join_type="KEEP_COMMON",field_mapping="""Structure "Structure" true true false 5 Text 0 0 ,First,#,Structure_Catchment,Structure,-1,-1;SummerGPD "SummerGPD" true true false 2 Short 0 0 ,First,#,Structure_Catchment,SummerGPD,-1,-1;WinterGPD "WinterGPD" true true false 2 Short 0 0 ,First,#,Structure_Catchment,WinterGPD,-1,-1;SummerAF "SummerAF" true true false 8 Double 0 0 ,First,#,Structure_Catchment,SummerAF,-1,-1;WinterAF "WinterAF" true true false 8 Double 0 0 ,First,#,Structure_Catchment,WinterAF,-1,-1;Total_AcFt "Total_AcFt" true true false 8 Double 0 0 ,First,#,Structure_Catchment,Total_AcFt,-1,-1;GRIDCODE "GRIDCODE" true true false 4 Long 0 0 ,First,#,Structure_Catchment,GRIDCODE,-1,-1;FEATUREID "FEATUREID" true true false 4 Long 0 0 ,First,#,Structure_Catchment,FEATUREID,-1,-1;SOURCEFC "SOURCEFC" true true false 20 Text 0 0 ,First,#,Structure_Catchment,SOURCEFC,-1,-1;AreaSqKM "AreaSqKM" true true false 8 Double 0 0 ,First,#,Structure_Catchment,AreaSqKM,-1,-1;PARCEL_ID "PARCEL_ID" true true false 4 Long 0 0 ,First,#,Properties_Riparian,PARCEL_ID,-1,-1;OWNER "OWNER" true true false 50 Text 0 0 ,First,#,Properties_Riparian,OWNER,-1,-1;Acres "Acres" true true false 8 Double 0 0 ,First,#,Properties_Riparian,Acres,-1,-1""",match_option="INTERSECT",search_radius="#",distance_field_name="#")

class Toolbox(object):
    def __init__(self):
        self.label = "Water Demand"
        self.alias = ""

        self.tools = [StructureDemandTool]

class StructureDemandTool(object):
    """
    Required parameters for demand estimates:
    1. Agriculture demand
        a. POD_ID: Identifier for the point of diversion
        b. FEATUREID: Catchment ID for the POD
    2. Structure Demand:
        a. PARCEL_ID: Parcel on which structure sits
        b. STRUCTURE_ID: ID for the structure
        c. SummerAF: Summer use in af/day
        d. WinterAF: Winter use in af/day

    Inputs:
    1. Water right points of diversion
    2. Catchments
    3. Streams
    4. Structures
    5. Property data

    Procedure:
    1. Spatial join PODs to catchments for ag demand.
    2. Create PODs for undeclared riparian rights
        a. Spatial join property data to stream data (riparian frontage)
        b. Filter properties with existing POD whose owner matches the property owner
        c. Assign generated application IDs to remaining properties.
        d. Spatial join all PODs (real & generated) with parcels
        e. Spatial join structure data to parcel data.
        f. Join (d) and (e) on parcel ID.
    """
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Structure Demand"
        self.description = """Estimates structure demand based on existing PODs and undeclared riparian rights for riparian frontage."""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        return [
            arcpy.Parameter(
                displayName = "Points of diversion",
                name = "pods",
                datatype = "GPFeatureLayer",
                parameterType = "Required",
                direction = "Input"
            ),
            arcpy.Parameter(
                displayName = "Catchments",
                name = "catchments",
                datatype = "GPFeatureLayer",
                parameterType = "Required",
                direction = "Input"
            ),
            arcpy.Parameter(
                displayName = "Stream Data",
                name = "streams",
                datatype = "GPFeatureLayer",
                parameterType = "Required",
                direction = "Input"
            ),
            arcpy.Parameter(
                displayName = "Structures",
                name = "structures",
                datatype = "GPFeatureLayer",
                parameterType = "Required",
                direction = "Input"
            ),
            arcpy.Parameter(
                displayName = "Property Data",
                name = "properties",
                datatype = "GPFeatureLayer",
                parameterType = "Required",
                direction = "Input"
            ),
        ]

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        return

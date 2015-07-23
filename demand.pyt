import arcpy

import numpy as np
import string
import os

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
            # Input Parameters
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

            # Output Parameters
            arcpy.Parameter(
                displayName = "Riparian Properties",
                name = "riparian_properties",
                datatype = "GPFeatureLayer",
                parameterType = "Required",
                direction = "Output"
            ),
            arcpy.Parameter(
                displayName = "Undeclared Riparian Rights",
                name = "undeclared_riparian",
                datatype = "GPFeatureLayer",
                parameterType = "Required",
                direction = "Output"
            ),
            arcpy.Parameter(
                displayName = "Synthesized Riparian PODs",
                name = "synthesized_pods",
                datatype = "GPFeatureLayer",
                parameterType = "Required",
                direction = "Output"
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
        pmap = {p.name: p.valueAsText for p in parameters}

        # a. Spatial join property data to stream data (riparian frontage)
        findRiparianProperties(
            pmap['properties'],
            pmap['streams'],
            pmap['riparian_properties'])

        messages.addMessage("%s properties have riparian frontage" % countFeatures(pmap['riparian_properties']))

        # b. Filter properties with existing POD whose owner matches the property owner
        removeRiparianWithPOD(pmap['riparian_properties'], pmap['pods'], pmap['undeclared_riparian'], messages)

        messages.addMessage("%s properties with undeclared riparian rights" % countFeatures(pmap['undeclared_riparian']))

        # c. Assign generated application IDs to remaining properties.
        createSynthesizedPODs(pmap, messages)

        return

def findRiparianProperties(propertyLayer, streamLayer, outputLayer):
    target = propertyLayer
    join = streamLayer
    output = outputLayer
    arcpy.SpatialJoin_analysis(target, join, output,
        "JOIN_ONE_TO_ONE", "KEEP_COMMON")

def removeRiparianWithPOD(riparianProperties, pods, undeclaredRiparian, messages):
    data = "in_memory\\removeRiparianWithPOD"
    # Join riparian properties to PODs
    arcpy.SpatialJoin_analysis(
        riparianProperties,
        pods,
        data,
        "JOIN_ONE_TO_MANY",
        "KEEP_ALL"
    )

    messages.addMessage("%s PODs lie on riparian properties" % countFeatures(data))

    # Add an attribute with a name similarity index
    arcpy.AddField_management(data, "Similarity", "DOUBLE", 7, 6)
    cursor = arcpy.UpdateCursor(data)
    for row in cursor:
        row.setValue("Similarity", float(compare_owner_holder(row)))
        cursor.updateRow(row)

    arcpy.Select_analysis(data, undeclaredRiparian,
        """ Similarity < 0.001 """);

def createSynthesizedPODs(pmap, messages):
    # We want only the ones with structures on them.
    withStructures = 'in_memory\\with_structures'
    arcpy.SpatialJoin_analysis(
        pmap['undeclared_riparian'],
        pmap['structures'],
        withStructures,
        'JOIN_ONE_TO_ONE',
        'KEEP_COMMON'
    )

    messages.addMessage("%s riparian properties with no POD contain structures" % countFeatures(withStructures))

    desc = arcpy.Describe(withStructures)
    source = arcpy.da.SearchCursor(withStructures, ["SHAPE@XY", "OWNER", "TARGET_FID"])
    points = []
    for feature in source:
        points.append(feature)

    arcpy.CreateFeatureclass_management(
        os.path.dirname(pmap['synthesized_pods']),
        os.path.basename(pmap['synthesized_pods']),
        'POINT',
        spatial_reference = desc.spatialReference
    )
    arcpy.AddField_management(pmap['synthesized_pods'], "POD_ID", "STRING")
    arcpy.AddField_management(pmap['synthesized_pods'], "OWNER", "STRING")
    arcpy.AddField_management(pmap['synthesized_pods'], "PARCEL_ID", "STRING")
    out = arcpy.da.InsertCursor(pmap['synthesized_pods'], ["SHAPE@XY", "OWNER", "PARCEL_ID", "POD_ID"])
    count = 0
    for point in points:
        out.insertRow([point[0], point[1], point[2], "SYNTH%03d" % count])
        count = count + 1

def countFeatures(layer):
    result = arcpy.GetCount_management(layer)
    return int(result.getOutput(0))

def compare_owner_holder(row):
    """Assign a similarity index to a property OWNER and a water right HolderName.

    This function builds a term frequency vector from the words in each name
    and computes cosine similarity to determine the similarity between two
    names. Returns a number between 0 and 1, with 0 indicating a complete
    mismatch and 1 indicating a perfect match. Intermediate values increase
    to 1 with increasing probability of a match.
    """
    if row.isNull("OWNER") or row.isNull("HolderName"):
        return 0.0

    ownerValue = str(row.getValue("OWNER"))
    holderValue = str(row.getValue("HolderName"))

    owner = set(ownerValue.lower().translate(None, string.punctuation).split())
    holder = set(holderValue.lower().translate(None, string.punctuation).split())
    terms = owner.union(holder)

    owner_freq = map(lambda t: 1 if t in owner else 0, terms)
    holder_freq = map(lambda t: 1 if t in holder else 0, terms)

    num = np.dot(owner_freq, holder_freq)
    denom = np.linalg.norm(owner_freq) * np.linalg.norm(holder_freq)
    return num/denom

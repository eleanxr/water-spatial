import arcpy
import numpy as np

import numpy as np
import string
import os

def processSynthesizedRiparianPODs(pmap, messages):
    """
    Creates a set of synthesized PODs based on riparian properties with no
    existing water right.
    """
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
    arcpy.AddField_management(pmap['synthesized_pods'], "APPL_ID", "STRING")
    arcpy.AddField_management(pmap['synthesized_pods'], "POD_ID", "STRING")
    arcpy.AddField_management(pmap['synthesized_pods'], "OWNER", "STRING")
    arcpy.AddField_management(pmap['synthesized_pods'], "PARCEL_ID", "STRING")
    out = arcpy.da.InsertCursor(pmap['synthesized_pods'],
        ["SHAPE@XY", "OWNER", "PARCEL_ID", "POD_ID", "APPL_ID"])
    count = 0
    for point in points:
        podid = "SYNTH%03d" % count
        out.insertRow([point[0], point[1], point[2], podid, podid])
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
    return num/denomdef createStructureDemandTable(structures, registered_pods, synthesized_pods,    properties, catchments, structure_demand):    """    Creates a table of demand estimates for structures.        a. Spatial join all PODs (real & generated) with parcels        b. Spatial join structure data to parcel data.        c. Join (d) and (e) on parcel ID.    Resulting dataset will have the following columns:    - APPL_ID : Application ID    - POD_ID : POD ID    - OWNER : OWNER of the right    - PARCEL_ID : Parcel on which the structure lies    - STRUCTURE_ID : Unique identifier for each structure.    - WinterAF : Winter demand in af/day    - SummerAF : Summer demand in af/day    - FEATUREID : Catchment basin in which the structure lies.    """    # Join structures to parcels.    structureParcels = "in_memory\\structure_parcels"    SpatialJoin_analysis(structures, properties, structureParcels,        "JOIN_ONE_TO_MANY", "KEEP_ALL")    # Assign structures to synthesized PODs for undeclared riparian rights    # Assign structures to real PODs for declared rights.    # Merge the two tables
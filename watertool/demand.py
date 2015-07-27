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
    fields = {
        (target, "FID"): ("PARCEL_ID", "LONG"),
        (target, "OWNER"): ("OWNER", "STRING"),
        (target, "Acres"): ("Acres", "DOUBLE")
    }
    fieldMapping = createSimpleFieldMapping(fields)
    arcpy.SpatialJoin_analysis(target, join, output,
        "JOIN_ONE_TO_ONE", "KEEP_COMMON", field_mapping=fieldMapping)

def assignStructurePODs(pods, properties, structures, streams, output, messages):
    # Find the riparian properties
    riparian = "in_memory\\riparian_properties"
    findRiparianProperties(properties, streams, riparian)
    
    # Join PODs and properties.
    podsProperties = "in_memory\\pods_properties"
    podFields = {
        (pods, "APPL_ID"): ("APPL_ID", "STRING"),
        (pods, "POD_ID"): ("POD_ID", "STRING"),
        (riparian, "PARCEL_ID"): ("PARCEL_ID", "LONG"),
        (pods, "FEATUREID"): ("FEATUREID", "LONG"),
        (pods, "HolderName"): ("HolderName", "STRING"),
        (riparian, "OWNER"): ("OWNER", "STRING")
    }
    podFieldMapping = createSimpleFieldMapping(podFields)
    arcpy.SpatialJoin_analysis(pods, riparian, podsProperties,
        "JOIN_ONE_TO_ONE", "KEEP_COMMON", field_mapping=podFieldMapping)
    
    # Add an attribute with a name similarity index
    arcpy.AddField_management(podsProperties, "Similarity", "DOUBLE", 7, 6)
    cursor = arcpy.UpdateCursor(podsProperties)
    for row in cursor:
        row.setValue("Similarity", float(compare_owner_holder(row)))
        cursor.updateRow(row)
        
    # Join structures and properties
    structuresProperties = output
    structFields = {
        (structures, "OBJECTID"): ("STRUCT_ID", "LONG"),
        (riparian, "PARCEL_ID"): ("PARCEL_ID", "LONG"),
        (structures, "WinterAF"): ("WinterAF", "FLOAT"),
        (structures, "SummerAF"): ("SummerAF", "FLOAT"),
        (riparian, "OWNER"): ("OWNER", "STRING"),
        (structures, "FEATUREID"): ("FEATUREID", "LONG"),
    }
    structFieldMapping = createSimpleFieldMapping(structFields)
    arcpy.SpatialJoin_analysis(structures, riparian, structuresProperties,
        "JOIN_ONE_TO_ONE", "KEEP_COMMON", field_mapping=structFieldMapping)
    
    # Create a new table to hold our results.
    columns = [
        ("APPL_ID", "STRING"),
        ("POD_ID", "STRING"),
    ]
    for name, datatype in columns:
        arcpy.AddField_management(structuresProperties, name, datatype)
    update = arcpy.UpdateCursor(structuresProperties)
    temp = "in_memory\\temp_selection"
    synthCount = 0
    for row in update:
        where = """ PARCEL_ID = %d """ % row.PARCEL_ID
        search = arcpy.SearchCursor(podsProperties, where)
        found = {}
        for pod in search:
            if pod.getValue("Similarity") > 0.0:
                for name, datatype in columns:
                    found[name] = pod.getValue(name)
        if found:
            for name, value in found.iteritems():
                row.setValue(name, value)
        else:
            fakeId = "SYNTH%03d" % synthCount
            row.setValue("APPL_ID", fakeId)
            row.setValue("POD_ID", fakeId)
        update.updateRow(row)

def createFeatureclass(location, geomType, spatialReference, columns):
    """Create a new featureclass at location with the specified columns."""
    arcpy.CreateFeatureclass_management(
        os.path.dirname(location),
        os.path.basename(location),
        geomType,
        spatial_reference = spatialReference
    )
    for name, columnType in columns:
        arcpy.AddField_management(location, name, columnType)


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
    arcpy.AddField_management(pmap['synthesized_pods'], "PARCEL_ID", "LONG")
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
    return num/denom

def createStructureDemandTable(structures, properties, structure_demand):
    """
    Join structure data to parcel data.
    
    Resulting dataset will have the following columns:
    - STRUCTURE_ID : Unique identifier for each structure.
    - OWNER : The owner of the structure (derived from parcel ownership)
    - PARCEL_ID : Parcel on which the structure lies
    - WinterAF : Winter demand in af/day
    - SummerAF : Summer demand in af/day
    """
    # Reproject the structures into the property dataset's coordinate system
    fields = {
        (structures, "OBJECTID"): ("STRUCT_ID", "LONG"),
        (properties, "OWNER"): ("OWNER", "STRING"),
        (properties, "FID"): ("PARCEL_ID", "LONG"),
        (structures, "WinterAF"): ("WinterAF", "FLOAT"),
        (structures, "SummerAF"): ("SummerAF", "FLOAT"),
        }
    fieldMapping = createSimpleFieldMapping(fields)
    arcpy.SpatialJoin_analysis(structures, properties, structure_demand,
        "JOIN_ONE_TO_MANY", "KEEP_ALL", field_mapping=fieldMapping)

def createSimpleFieldMapping(d, mappings=None):
    """Create an arcpy FieldMapping given a dictionary.

    Handles the simple case where column values should be taken verbatim from
    input tables and placed into a column with a specified name in the output
    table.
    
    Inputs
    ======
    d : dictionary
        A mapping from (table, column) tuples to the output field name.
    mappings : arcpy.FieldMappings
        An optional FieldMappings object to start with. Will be created if None.
    """
    if not mappings:
        mappings = arcpy.FieldMappings()
    for (table, column), output in d.iteritems():
        fields = arcpy.ListFields(table)
        m = arcpy.FieldMap()
        m.addInputField(table, column)
        outputField = m.outputField
        outputField.name = output[0]
        outputField.aliasName = output[0]
        outputField.type = output[1]
        m.outputField = outputField
        mappings.addFieldMap(m)
    return mappings

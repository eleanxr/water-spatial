import arcpy

import watertool.demand

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
3. Create structure demand table
    a. Spatial join all PODs (real & generated) with parcels
    b. Spatial join structure data to parcel data.
    c. Join (d) and (e) on parcel ID.
"""

class Toolbox(object):
    def __init__(self):
        self.label = "Water Demand"
        self.alias = ""

        self.tools = [
            UndeclaredRiparianTool,
            StructureDemandEstimateTool,
            StructureDemandPodTool,
        ]

class UndeclaredRiparianTool(object):
    """
    Tool to identify likely undeclared riparian users.

    Inputs
    ======
    pods : Points of diversion in the basin with holder information
    catchments : Catchments in the basin
    streams : Streams in the basin
    structures : Structures in the basin
    properties : Property boundaries and ownership in the basin

    Outputs
    =======
    riparian_properties : Polygon feature
        Properties with riparian frontage
    undeclared_riparian : Polygon feature
        Properties with riparian frontage and no associated POD
    synthesized_pods : Point feature
        Synthetic PODs assigned to riparian properties with a water need and no
        associated POD.
    """
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Undeclared Riparian Rights"
        self.description = "Identifies undeclared riparian rights."
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
        reload(watertool.demand)
        pmap = {p.name: p.valueAsText for p in parameters}
        watertool.demand.processSynthesizedRiparianPODs(pmap, messages)

class StructureDemandEstimateTool(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Estimate Structure Demand"
        self.description = "Estaimtes structure demand associated with PODs and catchments."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        return [
            arcpy.Parameter(
                displayName = "Structures",
                name = "structures",
                datatype = "GPFeatureLayer",
                parameterType = "Required",
                direction = "Input"
            ),
            arcpy.Parameter(
                displayName = "Properties",
                name = "properties",
                datatype = "GPFeatureLayer",
                parameterType = "Required",
                direction = "Input"
            ),

            # Outputs
            arcpy.Parameter(
                displayName = "Structure Demand Estimate",
                name = "structure_demand",
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
        reload(watertool.demand)
        pmap = {p.name : p for p in parameters}
        watertool.demand.createStructureDemandTable(
            pmap['structures'].valueAsText,
            pmap['properties'].valueAsText,
            pmap['structure_demand'].valueAsText
        )
        return

class StructureDemandPodTool(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Assign structure demand to PODs."
        self.description = "Estimates structure demand associated with PODs and catchments."
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        return [
            # Inputs
            arcpy.Parameter(
                displayName = "PODs",
                name = "pods",
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
                displayName = "Properties",
                name = "properties",
                datatype = "GPFeatureLayer",
                parameterType = "Required",
                direction = "Input"
            ),
            arcpy.Parameter(
                displayName = "Streams",
                name = "streams",
                datatype = "GPFeatureLayer",
                parameterType = "Required",
                direction = "Input"
            ),

            # Outputs
            arcpy.Parameter(
                displayName = "Structure Demand Estimate with POD",
                name = "structure_demand_pod",
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
        reload(watertool.demand)
        pmap = {p.name : p for p in parameters}
        watertool.demand.assignStructurePODs(
            pmap['pods'].valueAsText,
            pmap['properties'].valueAsText,
            pmap['structures'].valueAsText,
            pmap['streams'].valueAsText,
            pmap['structure_demand_pod'].valueAsText,
            messages
        )
        return
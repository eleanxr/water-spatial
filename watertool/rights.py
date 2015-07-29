import pandas as pd
import numpy as np

import sys
import os
import string
import calendar

path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(os.path.dirname(path), 'connectivity'))

import util

# The columns required for demand output.
DEMAND_COLUMNS = [
    "APPL_ID_pod", # use
    "POD_ID", # use & pod
    "FEATUREID", # pod
    #"OwnEdit", # use
    "Status Date", # ewrims
    "Riparian", # ewrims
    "Pre 1914", # ewrims
    #"FACEAMT_use", # use
    #"wr_type_use", # use
    #"parcID", # use
    #"vineyard", # use
    "Vine_Water", # use
    #"orchard", # use
    "Orch_Water" # use
]

# Use profile for vineyards assumes the irrigation season runs from
# mid-July through mid-October.
VINEYARD_USE_PROFILE = [
    None,
    0.0, #Jan
    0.0, #Feb
    0.0, #Mar
    0.0, #Apr
    0.0, #May
    0.0, #Jun
    1.0/6, #Jul
    1.0/3, #Aug
    1.0/3, #Sep
    1.0/6, #Oct
    0.0, #Nov
    0.0, #Dec
    ]

VINEYARD_USE_PROFILE_STORAGE = [
    None,
    1.0/3, #Jan
    1.0/3, #Feb
    0.0, #Mar
    0.0, #Apr
    0.0, #May
    0.0, #Jun
    0.0, #Jul
    0.0, #Aug
    0.0, #Sep
    0.0, #Oct
    0.0, #Nov
    1.0/3, #Dec
    ]

# Use profile for orchards assumes the irrigation season runs from
# mid-May through mid-October.
ORCHARD_USE_PROFILE = [
    None,
    0.0, #Jan
    0.0, #Feb
    0.0, #Mar
    0.0, #Apr
    1.0/10, #May
    1.0/5, #Jun
    1.0/5, #Jul
    1.0/5, #Aug
    1.0/5, #Sep
    1.0/10, #Oct
    0.0, #Nov
    0.0, #Dec
    ]

SUMMER_DOMESTIC_USE = [
    None,
    0.0, #Jan
    0.0, #Feb
    0.0, #Mar
    1.0/6.0, #Apr
    1.0/6.0, #May
    1.0/6.0, #Jun
    1.0/6.0, #Jul
    1.0/6.0, #Aug
    1.0/6.0, #Sep
    0.0, #Oct
    0.0, #Nov
    0.0, #Dec
    ]

WINTER_DOMESTIC_USE = [
    None,
    1.0/6.0, #Jan
    1.0/6.0, #Feb
    1.0/6.0, #Mar
    0.0, #Apr
    0.0, #May
    0.0, #Jun
    0.0, #Jul
    0.0, #Aug
    0.0, #Sep
    1.0/6.0, #Oct
    1.0/6.0, #Nov
    1.0/6.0, #Dec
    ]

def left_join(use, pod, use_id, pod_id, suffixes=("_x", "_y")):
    """Perform a left join of two datasets."""
    return pd.merge(use, pod, left_on=use_id, right_on=pod_id,
                    how='left', suffixes=suffixes)

def convert_ewrims_columns(data):
    data["Riparian"] = data["Riparian"].map({"Y": True}).fillna(False)
    data["Pre 1914"] = data["Pre 1914"].map({"Y": True}).fillna(False)
    # Convert the status date column to an actual date.
    data["Status Date"] = pd.DatetimeIndex(pd.to_datetime(data["Status Date"], coerce=True)).normalize()
    data = data.sort("Status Date")
    return data


def get_rights_data(ewrims_file):
    """Read the rights data from a file downloaded from the eWRIMS database.

    Rights data may be obtained from the CA Water Board rights database in
    an Excel file. The file contains multiple worksheets:
    - Water Rights : Details the right, its status date, its face value and its
      diversion rate.
    - Application Info : Details the right application info, including whether or not
        the right is riparian or pre-1914.
    - Points of Diversion : The location of points of diversion.
    - Beneficial Uses : use of the water.
    This function joins the Water Rights and Application Info worksheets into a single
    table, combining all information about the priority and status of the right.
    """
    water_rights = pd.read_excel(ewrims_file, sheetname="Water Rights")
    application_info = pd.read_excel(ewrims_file, sheetname="Application Info")

    return left_join(water_rights, application_info, "Application Number", "Application ID",
                     suffixes=("_right", "_info"))

def get_demand(ag_use, structure_use, declared_pod, ewrims,
               vineyard_profile=VINEYARD_USE_PROFILE, undeclared_pod=None):
    ag_demand = get_ag_demand(ag_use, declared_pod, ewrims)
    structure_demand = get_structure_demand(declared_pod, structure_use)
    if (undeclared_pod):
        undeclared_demand = get_structure_demand(undeclared_pod, structure_use)
        structure_demand = structure_demand.concat(undeclared_demand)
    ag_structure = merge_ag_structure(ag_demand, structure_demand)
    rights = add_rights_info(ag_structure, ewrims)
    return disaggregate_monthly(rights, vineyard_profile)

def get_ag_demand(use_file, pod_file):
    """Get a single table with agricultural demand estimates.

    The use file is expected to contain the following columns:
    - POD_ID : A unique identifier for the point of diversion.
    - APPL_ID : The water right application ID
    - Vine_Water : The water used for the vineyard acreage
    - Orch_Water : The water used for the orchard acreage

    The POD file is expected to contain the following columns:
    - POD_ID : A unique identifier for the point of diversion
    - FEATUREID : The catchment feature ID (from the NHD+V2 dataset) in which the POD lies.

    Parameters
    ----------
    use_file : string
        The name of the file with all of the use information.
    pod_file : string
        The name of the file with the POD locations joined to their catchment.
    """
    use_data = pd.read_csv(use_file)

    pod_data = util.read_dbf(pod_file)

    pod_use = pd.merge(pod_data, use_data, left_on='POD_ID', right_on='POD_ID',
                       suffixes=('_pod', '_use'), how='left')
    pod_use['APPL_ID_pod'] = pod_use['APPL_ID_pod'].map(lambda x: x[:-1] if x.endswith('R') else x)
    columns = [
        'APPL_ID_pod',
        'FEATUREID',
        'Vine_Water',
        'Orch_Water',
        ]
    first = lambda x: x.iloc[0]
    return pod_use[columns].groupby('APPL_ID_pod').agg(first)

def get_structure_demand(pods, structures):
    """Get a single table with structure demand estimates.

    The structures file is expected to have the following fields:
    - PARCEL_ID : The parcel ID on which the structure lies.
    - STRUCTURE_ID : A unique identifier for each structure.
    - SummerAF: The water demand in the summer (AF)
    - WinterAF: The water demand in the winter (AF)

    The POD file is expected to have the following fields:
    PARCEL_ID : The parcel ID on which the POD lies.
    FEATUREID : The NHD+V2 catchment ID in which the POD lies.
    APPL_ID : The water right application ID.
    """
    pod_data = util.read_dbf(pods)
    structure_data = util.read_dbf(structures)
    join = pd.merge(structure_data, pod_data,
                    left_on='PARCEL_ID', right_on='PARCEL_ID',
                    how='inner', suffixes=('_pod', '_structure'))
    join['APPL_ID'] = join['APPL_ID'].map(lambda x: x[:-1] if x.endswith('R') else x)
    columns = [
        'APPL_ID',
        'STRUCT_ID',
        'SummerAF',
        'WinterAF',
        ]
    return join[columns].groupby('STRUCT_ID').agg({
        'APPL_ID': lambda x: x.iloc[0],
        'SummerAF': lambda x: x.iloc[0],
        'WinterAF': lambda x: x.iloc[0]
        }).groupby('APPL_ID').agg({
            'SummerAF': np.sum,
            'WinterAF': np.sum
            })

def get_structure_demand_prepared(database):
    """Read already prepared POD-Structure demand table."""
    data = util.read_dbf(database)
    
    columns = [
        'APPL_ID',
        'STRUCT_ID',
        'SummerAF',
        'WinterAF',
        'FEATUREID',
    ]
    
    return data[columns].groupby('APPL_ID').agg({
        'SummerAF': np.sum,
        'WinterAF': np.sum,
        'FEATUREID': lambda x: x.iloc[0],
    })

def merge_ag_structure(ag_demand, structure_demand):
    """Merge agricultural and structure use data on Application ID

    Both datasets are expected to be indexed by Application ID.
    """
    join = pd.merge(ag_demand, structure_demand,
                    left_index=True, right_index=True,
                    how='outer', suffixes=('_ag', '_struct'))
    
    # Reconcile ag/struct featureids by favoring ag.
    def choose_featureid(row):
        if not pd.isnull(row['FEATUREID_ag']):
            return row['FEATUREID_ag']
        elif not pd.isnull(row['FEATUREID_struct']):
            return row['FEATUREID_struct']
        else:
            return None
    join['FEATUREID'] = join.apply(choose_featureid, axis=1)
    
    return join

def add_rights_info(demand, ewrims_file):
    """Add water right information from the eWRIMS database.

    Parameters
    ----------
    demand : Series
        The demand indexed by application ID.
    ewrims_file : string
        An excel file downloaded from eWRIMS with water right information.
    """
    ewrims_data = get_rights_data(ewrims_file)[[
        "Application ID",
        "Riparian",
        "Pre 1914",
        "Status Date"
        ]]
    join = pd.merge(demand, ewrims_data, left_index=True, right_on="Application ID",
                    how='left')
    return convert_ewrims_columns(join).set_index("Application ID")

def disaggregate_monthly(demand, vineyard_profile=VINEYARD_USE_PROFILE):
    """Disaggregate the demand estimate by month.

    Estimates are used for the following fields:
    - Vine_Water : Water use for vineyards
    - Orch_Water : Water use for orchards
    - WinterAF : Structure use in the winter.
    - SummerAF : Structure use in the summer.
    """
    result = demand.copy()

    for column in ['Vine_Water', 'Orch_Water', 'SummerAF', 'WinterAF']:
        result[column].fillna(0.0, inplace=True)

    # Apply the use profiles.
    for i in range(1, 13):
        result[calendar.month_abbr[i]] = \
          vineyard_profile[i] * result["Vine_Water"] + \
          ORCHARD_USE_PROFILE[i] * result["Orch_Water"] + \
          WINTER_DOMESTIC_USE[i] * result["WinterAF"] + \
          SUMMER_DOMESTIC_USE[i] * result["SummerAF"]
    return result

def split_appropriative_riparian(demand):
    """Split appropriative and riparian demand into two datasets"""
    appropriative = demand[demand["Riparian"] == False]
    riparian = demand[demand["Riparian"] == True]
    return appropriative, riparian

def write_input_spreadsheet(demand, filename):
    app, rip = split_appropriative_riparian(demand)
    pre = app[app["Pre 1914"] == True]
    post = app[app["Pre 1914"] == False]

    writer = pd.ExcelWriter(filename)
    rip.to_excel(writer, "Riparian")
    pre.to_excel(writer, "AppPre1914")
    post.to_excel(writer, "AppPost1914")
    writer.save()

def create_use_reports(pod_file, ewrims_file):
    """Create use report stubs for hand entry.

    This function does not apply any automatic demand estimates.
    """
    ewrims_data = get_rights_data(ewrims_file)
    pod_data = util.read_dbf(pod_file)

    pod_right = pd.merge(pod_data, ewrims_data, left_on='APPL_ID',
                         right_on='Application Number', how='left')

    columns = [
        "APPL_ID",
        "FEATUREID",
        "Status Date",
        "Riparian",
        "Pre 1914",
        "FACEAMT",
        ]

    first = lambda x: x.iloc[0]
    agg = {
        "FEATUREID": first,
        "Status Date": first,
        "Riparian": first,
        "Pre 1914": first,
        "FACEAMT": np.sum
        }

    result = convert_ewrims_columns(pod_right[columns]).groupby("APPL_ID").agg(agg).sort("Status Date")

    result['Demand Year'] = pd.Series()
    for i in range(1, 13):
        result[calendar.month_abbr[i]] = pd.Series()

    return split_appropriative_riparian(result)


def compare_owner_holder(row):
    """Assign a similarity index to a property OWNER and a water right HolderName.

    This function builds a term frequency vector from the words in each name
    and computes cosine similarity to determine the similarity between two
    names. Returns a number between 0 and 1, with 0 indicating a complete
    mismatch and 1 indicating a perfect match. Intermediate values increase
    to 1 with increasing probability of a match.
    """
    owner = set(row['OWNER'].lower().translate(None, string.punctuation).split())
    holder = set(row['HolderName'].lower().translate(None, string.punctuation).split())
    terms = owner.union(holder)

    owner_freq = map(lambda t: 1 if t in owner else 0, terms)
    holder_freq = map(lambda t: 1 if t in holder else 0, terms)

    num = np.dot(owner_freq, holder_freq)
    denom = np.linalg.norm(owner_freq) * np.linalg.norm(holder_freq)
    return num/denom

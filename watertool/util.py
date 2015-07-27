import pandas as pd

from dbfread import DBF

def read_dbf(filename, columns = None):
    """
    Read a dBASE file with attributes into a pandas DataFrame.
    """
    """
    dbf = ps.open(filename)

    if not columns:
        columns = dbf.header
    data = {col: dbf.by_col(col) for col in columns}
    return pd.DataFrame(data)
    """
    dbf = DBF(filename, load = True)
    if not columns:
        columns = dbf.field_names
    records = {}
    for record in dbf.records:
        for key in record.keys():
            if not records.has_key(key):
                records[key] = [record[key]]
            else:
                records[key].append(record[key])
    return pd.DataFrame(records)

import pandas as pd
from jsonschema import validate


def convert_df_to_json(df:pd.DataFrame)->dict:

    document = {}
    documentfile_id = df['documentfile_id'].values[0]
    if 'sheet_name' in df.columns:
        sheet_title = df['sheet_name'].values[0]
        document['sheet_title'] = sheet_title

    document['documentfile_id'] = int(documentfile_id)
    persons = [] # of {'person': {}, 'incomes':{} }

    for row in df.itertuples():
        row = row._asdict()

        person = {
            "name_raw": row.get('name', ''),
            "role": row.get('position', ''),
            "department": row.get('department', ''),
        }

        salary = row.get('size', 0)
        salary_check = lambda x: 0 if not x or not str(x).split() else int(x)  
        salary = salary_check(salary)

        income = [
            {
            "size":salary ,
            "size_raw":row.get("size_raw", '')
             }
        ]

        persons.append({
            "person":person,
            "incomes":income,
            "vehicles": [],
            "real_estates":[]

        })

    results = {"persons":persons,"document": document}

    schema = {
        "$ref": "https://declarator.org/static/api/import-schema.json"
    }

    validate(results, schema)
    return results



import pandas as pd
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common import get_db

db = get_db()
collection_keywords = db["keywords_temp"]

df = pd.read_excel("keywords.xlsx")

records = df.to_dict(orient="records")

collection_keywords.insert_many(records)

print("Uploaded!")
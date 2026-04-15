import pandas as pd
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common import get_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

db = get_db()
blog_items = db["Blog_Items"]
# cursor = collection.find(
#     {
#         "date": {"$regex": "^2026-03-24"}
#     }
# )
# Keychal_States = list(cursor)

# free_pricing = 
# df = pd.DataFrame(Keychal_States)

# df.to_excel(os.path.join(BASE_DIR, "..",  "output", "keychal_output.xlsx"), index=False)



df = pd.read_excel("keywords.xlsx")
# df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

input_data = df.to_dict(orient="records")

blog_items.insert_many(input_data)

# collection_keywords.delete_many({"date": {"$exists": True}})

# collection_keywords.insert_many(records)


# for r in records:
#     collection_keywords.update_one(
#         {
#         "keyword": r["keyword"],
#         "influencer": {"$exists": False}
#     },
#     {
#         "$set": {"influencer": r["influencer"]}
#     }
# )
    

print("Upload 완료!")
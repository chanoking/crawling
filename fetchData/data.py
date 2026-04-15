import pandas as pd
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from common import get_db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

db = get_db()

blog_items = list(db["Blog_Items"].find({}))

# db["Blog_States"].update_many({}, {
#     "$rename": {"item": "itemId"}
# })

# print(blog_items)

for item in blog_items:
    db["Blog_States"].update_many({"itemId": item["item"]},{
        "$set": {"itemId": item["_id"]}
    })


# blog_keywords = list(db["Blog_Keywords"].aggregate([
#     {
#         "$lookup":{
#             "from": "Blog_Items",
#             "localField": "item",
#             "foreignField": "item",
#             "as": "Item_Info"
#         }
#     },
#     {
#         "$unwind": "$Item_Info"
#     },
#     {
#         "$project":{
#             "_id": 0,
#             "keyword":1,
#             "itemId": "$Item_Info._id"
#         }
#     }
# ]))

# db["Blog_Keywords"].delete_many({})

# db["Blog_Keywords"].insert_many(blog_keywords)

print("success!")
import os
from dotenv import load_dotenv
from pymongo import MongoClient
import sys
import pandas as pd
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common import get_db
from common import forward
from common import get_keyword_volume

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

db = get_db()
collection_keyword = db["foodcare_input_for_keyword"]
keywords = list(collection_keyword.find({}))

results = []

def main():
    for doc in keywords:
        kw = doc["keyword"]
        data = get_keyword_volume(kw)
        time.sleep(0.2)
        for row in data.get("keywordList", []):
            if row["relKeyword"] == kw:
                results.append({
                    "keyword": kw,
                    "pc": row["monthlyPcQcCnt"],
                    "mobile": row["monthlyMobileQcCnt"],
                    "competition": row["compIdx"]
                })
                print(f"{kw}: {row['monthlyMobileQcCnt']}")
                break
    
    df = pd.DataFrame(results)
    df.to_excel(os.path.join(BASE_DIR, "..", "output", "keyword_volume.xlsx"), index=False)

if __name__ == "__main__":
    main()
    forward("keyword_volume.xlsx")



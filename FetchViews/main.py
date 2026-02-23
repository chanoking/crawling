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
collection_keyword = db["keywords_temp"]
keywords = list(collection_keyword.find({}))

def main():
    results = []
    for doc in keywords:
        kw = (
            doc["keyword"]
            .replace("\xa0", "")
            .replace("\ufeff", "")
            .replace("\n", "")
            .replace("\r", "")
            .strip()
        )
        try:
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
        except:
            results.append({
                "keyword": kw,
                "pc": 0,
                "mobile": 0,
                "competition": "확인불가"
                print("Error Occurred")
            })
        
    
    df = pd.DataFrame(results)
    df.to_excel(os.path.join(BASE_DIR, "..", "output", "keyword_volume.xlsx"), index=False)

if __name__ == "__main__":
    main()
    forward("keyword_volume.xlsx", "키워드 볼륨 결과파일")



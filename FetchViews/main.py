import os
import sys
import time
import re
import pandas as pd
from dotenv import load_dotenv
from pymongo import MongoClient
from playwright.sync_api import sync_playwright

# 공통 모듈 import
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from common import get_db, forward, get_keyword_volume

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# DB 연결
db = get_db()
collection_keyword = db["keywords_temp"]
db_keywords = list(collection_keyword.find({}))


def clean_keyword(text):
    """키워드 문자열 정리"""
    return re.sub(r"[\xa0\ufeff\n\r]", "", text).strip()


def make_autocomplete_keyword(page, keyword):
    """네이버 자동완성 키워드 추출"""

    page.goto("https://m.naver.com")
    page.click("#MM_SEARCH_FAKE")
    page.wait_for_selector("#query:visible")

    # 기존 입력값 초기화 후 입력
    page.fill("#query", keyword)

    try:
        page.wait_for_selector("#sb-ac-recomm-wrap li.u_atcp_l")
        page.wait_for_timeout(500)

        suggested_keywords = page.locator(
            "#sb-ac-recomm-wrap li.u_atcp_l"
        ).evaluate_all(
            "els => els.map(el => el.getAttribute('data-query'))"
        )

        if not suggested_keywords:
            return keyword

        match = [
            x for x in suggested_keywords
            if x and x.replace(" ", "") == keyword
        ]
    except:
        return keyword

    return match[0] if match else keyword


def main():
    df = pd.DataFrame(db_keywords)
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/16.0 Mobile/15E148 Safari/604.1"
            )
        )
        page = context.new_page()

        for idx, row in df.iterrows():
            # keyword = clean_keyword(row["keyword"])
            keyword = row["keyword"]

            try:
                autocomplete_keyword = make_autocomplete_keyword(page, keyword)

                data = get_keyword_volume(keyword)
                time.sleep(0.2)

                found = False

                for r in data.get("keywordList", []):
                    if r["relKeyword"] == keyword:
                        results.append({
                            "keyword": keyword,
                            "autocompleteKeyword": autocomplete_keyword,
                            "pc": r.get("monthlyPcQcCnt", 0),
                            "mobile": r.get("monthlyMobileQcCnt", 0),
                        })

                        print(f"{keyword}: {r.get('monthlyMobileQcCnt', 0)} / autocomplete: {autocomplete_keyword}")
                        found = True
                        break

                if not found:
                    results.append({
                        "keyword": keyword,
                        "autocompleteKeyword": autocomplete_keyword,
                        "pc": 0,
                        "mobile": 0,
                    })

            except Exception as e:
                print(f"Error on keyword '{keyword}': {e}")

                results.append({
                    "keyword": keyword,
                    "autocompleteKeyword": "확인불가",
                    "pc": 0,
                    "mobile": 0,
                })

    # 결과 저장
    output_path = os.path.join(BASE_DIR, "..", "output", "keyword_volume.xlsx")
    pd.DataFrame(results).to_excel(output_path, index=False)

    print("엑셀 저장 완료")


if __name__ == "__main__":
    main()
    forward("keyword_volume.xlsx", "푸드케어 검색 결과파일")
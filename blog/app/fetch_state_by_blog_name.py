import pandas as pd
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse
import os, datetime
from datetime import date
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from common import get_db, get_keyword_volume, upload

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

blog_names = ["황둥강둥 다섯가족의 현실육아", "오리진그리드", "산엔들", "데일리 건강 기록", 
              "국제 임상영양 연구 전문 분석 블로그", "PHYTONUTRI", "푸드케어 클레", "건강한 삶을 위한 영양백과"]

db = get_db()
collection_keywords = db["Blog_Keywords"]
cursor_keywords = collection_keywords.find({})

keywords = list(cursor_keywords)

paths = []

# ============================
# 개별 블로그 아이템 추출
# ============================
def get_value(item):
    blog_name_sel = item.locator('[data-heatmap-target="articleSourceJSX_title"] span.sds-comps-text')
    if blog_name_sel.count() > 0:
        blog_name = blog_name_sel.first.inner_text()
        if blog_name in blog_names:
            return 1

    return 0

# ============================
# 블록 셀렉터 정의
# ============================
BLOCK_SELECTORS = [
    '[data-block-id="review/prs_template_v2_review_ugc_single_intention_mo.ts"]',
    '[data-block-id="ugc/prs_template_v2_ugc_default_mo.ts"]',
    '[data-block-id="ugc/prs_template_v2_ugc_popular_article_mo.ts"]',
    '[data-block-id="ugc/prs_template_v2_ugc_snippet_paragraph_mo.ts"]',
    '[data-block-id="review/prs_template_v2_review_blog_rra_mo.ts"]',
]


# ============================
# 현재 페이지 블록 상태 판단
# ============================
def get_env_state(page):
    valid_blocks = []

    for sel in BLOCK_SELECTORS:
        if page.locator(sel).count() > 0:
            valid_blocks.append(sel)

    if not valid_blocks:
        return "블로그 블록 없음", []

    env = "구분없음"

    if BLOCK_SELECTORS[0] in valid_blocks:
        block_locator = page.locator(BLOCK_SELECTORS[0])
        header_locator = block_locator.locator('[data-template-id="header"] h2.sds-comps-text')
        if header_locator.count() > 0:
            header = header_locator.first.inner_text()
            if "브랜드" not in header: 
               env = "단일스블"
    elif any(sel in valid_blocks for sel in BLOCK_SELECTORS[1:4]):
        env = "다중스블"

    return env, valid_blocks


# ============================
# 블로그 템플릿 파싱
# ============================
def get_env_value(page, keyword):
    page.goto(
        f"https://m.search.naver.com/search.naver?query={keyword}",
        wait_until="domcontentloaded"
    )

    page.wait_for_selector(
        "div[data-block-id]",
        timeout=5000
    )

    env, valid_blocks = get_env_state(page)

    if not valid_blocks:
        return 0, "블로그 블록 없음"

    cnt = 0
    for sel in valid_blocks:
        blocks = page.locator(sel)

        for i in range(blocks.count()):
            block_locator = blocks.nth(i)
            items_locator = block_locator.locator('[data-template-id="ugcItem"]')
            for j in range(items_locator.count()):
                item = items_locator.nth(j)
                cnt += get_value(item)
            
    return cnt, env

def get_key_vol(keyword):
    try:
        data = get_keyword_volume(keyword)
        for row in data.get("keywordList", []):
            if row["relKeyword"] == keyword:
                return row["monthlyPcQcCnt"], row["monthlyMobileQcCnt"], row["compIdx"]
    except Exception as e:
        print(f"[ERROR get_key_vol] {e}")
    # 항상 튜플 반환
    return 10, 10, "알수없음"

# ============================
# 메인 실행부
# ============================
def main():
    start_time = datetime.datetime.now()
    df = pd.DataFrame(keywords)

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

        for idx, row in enumerate(df.itertuples()):
            keyword = row.keyword
            itemId = row.itemId
            try:
                cnt, env = get_env_value(page, keyword)
                pc, mobile, competition = get_key_vol(keyword)
            except Exception as e:
                print("[ERROR]", e)
                cnt, env = 0, "블로그 블록 없음"
                pc, mobile, competition = 0, 0, "알수없음"

            new_state = {
                "date": datetime.datetime.combine(datetime.date.today(), datetime.time.min),
                "keyword": keyword,
                "itemId": itemId,
                "mobile": mobile,
                "pc": pc,
                "competition": competition,
                "cnt": cnt,
                "env": env
            }

            upload(new_state, "Blog_States")

            progress = round(((idx + 1) / len(df)) * 100, 2)
            print(f"{progress}% {datetime.datetime.now() - start_time} {keyword} → cnt={cnt}, env={env}, mobile={mobile}")

        browser.close()

    elapsed = datetime.datetime.now() - start_time
    print(f"Completed! 실행시간: {elapsed}")

if __name__ == "__main__":
    main()
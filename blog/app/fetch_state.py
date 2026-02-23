import pandas as pd
from playwright.sync_api import sync_playwright
import datetime, os
import sys
from dotenv import load_dotenv
from urllib.parse import urlparse

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from common import get_db
from common import forward

blog_names = ["푸드케어 클레"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

db = get_db()

collection_keyword = db["foodcare_input_for_keyword"]
collection_url = db["foodcare_input_for_url"]

cursor_key = collection_keyword.find({})
cursor_url = collection_url.find({})

data_list_url = list(cursor_url)

paths = []

for doc in data_list_url:
    url = doc.get("url")
    if not url:
        continue

    p = urlparse(url).path.strip("/")
    paths.append(p)


# ----------------------------
# 블록 셀렉터
# ----------------------------
BLOCK_SELECTORS = [
    '[data-block-id="review/prs_template_v2_review_ugc_single_intention_mo.ts"]',
    '[data-block-id="ugc/prs_template_v2_ugc_default_mo.ts"]',
    '[data-block-id="ugc/prs_template_v2_ugc_popular_article_mo.ts"]',
    '[data-block-id="ugc/prs_template_v2_ugc_snippet_paragraph_mo.ts"]',
    '[data-block-id="review/prs_template_v2_review_blog_rra_mo.ts"]'
]

def detect_blocks(page, selectors):
    candidates = []

    for sel in selectors:
        locator = page.locator(sel)
        count = locator.count()

        if count > 0:
            candidates.append(sel)
    
    return candidates

def get_value(item):
    cnt = 0
    blog_name_sel = item.locator('[data-heatmap-target="articleSourceJSX_title"] span.sds-comps-text')
    if blog_name_sel.count() > 0:
        blog_name = blog_name_sel.first.inner_text()
        if blog_name in blog_names:
            cnt += 1

    selectors = [
        'a[data-heatmap-target=".tit"]',
        'a[data-heatmap-target=".link"]',
        'a[data-heatmap-target=".imgtitlelink"]',
    ]

    for sel in selectors:
        link_el = item.locator(sel)
        if link_el.count() > 0:
            url = link_el.first.get_attribute("href") or ""
            p = urlparse(url).path.strip("/")
            if p in paths:
                cnt += 1
                return cnt

    return cnt

# ----------------------------
# 블로그 템플릿 파싱
# ----------------------------
def parse_blog_template_get_value(page, keyword):
    page.goto(
        f"https://search.naver.com/search.naver?query={keyword}",
        wait_until="domcontentloaded"
    )
    page.wait_for_timeout(2000)

    validBlocks = detect_blocks(page, BLOCK_SELECTORS)

    if len(validBlocks) == 0:
        return 0, "블로그 블록 없음"

    # 단일 블록인지 체크
    if BLOCK_SELECTORS[0] in validBlocks:
        env = "단일스블"
        block = page.locator(BLOCK_SELECTORS[0])
        headerSel = block.locator('[data-template-id="header"] h2.sds-comps-text')
        if headerSel.count() > 0:
            header = headerSel.first.inner_text()
            if "브랜드" not in header: 
               env = "단일스블"

    # 여러 블록인지 체크
    elif any(sel in validBlocks for sel in BLOCK_SELECTORS[1:4]):
        env = "다중스블"

    else:
        env = "구분없음"


    cnt = 0

    for sel in validBlocks:
        blocks = page.locator(sel)

        for i in range(blocks.count()):
            block = blocks.nth(i)
            items = block.locator('[data-template-id="ugcItem"]')

            for j in range(items.count()):
                item = items.nth(j)
                cnt += get_value(item)

        return cnt, env


# ----------------------------
# 메인
# ----------------------------
def main():
    start_time = datetime.datetime.now()
    data_list_key = list(cursor_key)
    df = pd.DataFrame(data_list_key)

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
            keyword = row["keyword"]
            cnt, env = parse_blog_template_get_value(page, keyword)

            df.at[idx, "cnt"] = cnt
            df.at[idx, "env"] = env

            print(f"{keyword} → cnt={cnt}, env={env}")

        browser.close()
    
    end_time = datetime.datetime.now()
    elapsed = end_time - start_time
    df.to_excel(os.path.join(BASE_DIR, "..", "..", "output", "foodcare_output.xlsx"), index=False)
    print("완료!")
    print(f"실행시간: {elapsed}")


if __name__ == "__main__":
    main()
    forward("foodcare_output.xlsx", "푸드케어 결과파일")
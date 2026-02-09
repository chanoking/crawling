import pandas as pd
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse
import datetime, os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from common import get_db
from common import forward

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

blog_names = ["황둥강둥 다섯가족의 현실육아", "오리진그리드", "산엔들", "데일리 건강 기록", 
              "국제 임상영양 연구 전문 분석 블로그", "PHYTONUTRI", "푸드케어 클레"]

db = get_db()
collection_input_item_keyword = db["blog_input"]
collection_input_url = db["blog_input_url"]
cursor_input = collection_input_item_keyword.find({})
cursor_input_url = collection_input_url.find({})

data_list_input = list(cursor_input)
data_list_input_url = list(cursor_input_url)

paths = []

for doc in data_list_input_url:
    url = doc.get("url")
    if not url:
        continue

    p = urlparse(url).path.strip("/")
    paths.append(p)

# ============================
# 개별 블로그 아이템 추출
# ============================
def get_value(item):
    blog_name_sel = item.locator('[data-heatmap-target="articleSourceJSX_title"] span.sds-comps-text')
    if blog_name_sel.count() > 0:
        blog_name = blog_name_sel.first.inner_text()
        if blog_name in blog_names:
            return 1

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
        block = page.locator(BLOCK_SELECTORS[0])
        headerSel = block.locator('[data-template-id="header"] h2.sds-comps-text')
        if headerSel.count() > 0:
            header = headerSel.first.inner_text()
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
    page.wait_for_timeout(2000)

    env, valid_blocks = get_env_state(page)

    if not valid_blocks:
        return 0, "블로그 블록 없음"

    for sel in valid_blocks:
        blocks = page.locator(sel)

        for i in range(blocks.count()):
            block = blocks.nth(i)
            items = block.locator('[data-template-id="ugcItem"]')

            for j in range(items.count()):
                item = items.nth(j)
                val = get_value(item)
                if val:
                    return 1, env
    return 0, env

# def get_view_for_keyword(page, keyword):
#     page.goto(
#         f"https://surffing.net/keyword/{keyword}",
#         wait_until="domcontentloaded"
#     )

#     viewSel = page.locator('#keywordResults td.num-total')

#     view = 10
#     try:
#         if viewSel.count() > 0:
#             raw = viewSel.first.inner_text().strip()
#             view = int(raw.replace(",", ""))
#     except:
#         return view

#     return view    

# ============================
# 메인 실행부
# ============================
def main():
    start_time = datetime.datetime.now()
    df = pd.DataFrame(data_list_input)

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
            try:
                exposure, env = get_env_value(page, keyword)
                # view = get_view_for_keyword(page, keyword)
            except Exception as e:
                print("[ERROR]", e)
                exposure, env = 0, "블로그 블록 없음"
                # view = 10

            # df.at[idx, "view"] = view
            df.at[idx, "exposure"] = exposure
            df.at[idx, "env"] = env

            progress = round(((idx + 1) / len(df)) * 100, 2)
            print(f"{progress}% {datetime.datetime.now() - start_time} {keyword} → exposure={exposure}, env={env}")


        browser.close()

    df.to_excel(os.path.join(BASE_DIR, "..", "..", "output", "blog_output.xlsx"), index=False)

    elapsed = datetime.datetime.now() - start_time
    print(f"Completed! 실행시간: {elapsed}")

if __name__ == "__main__":
    main()
    forward("blog_output.xlsx")
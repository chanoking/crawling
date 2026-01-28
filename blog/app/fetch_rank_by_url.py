import time
import pandas as pd
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse
import datetime, os

# ============================
# 기본 경로 설정
# ============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================
# 개별 블로그 아이템 추출
# ============================
def extract_item(item):
    selectors = [
        'a[data-heatmap-target=".tit"]',
        'a[data-heatmap-target=".link"]',
        'a[data-heatmap-target=".imgtitlelink"]',
    ]

    for sel in selectors:
        link_el = item.locator(sel)
        if link_el.count() > 0:
            return {
                "url": link_el.first.get_attribute("href") or ""
            }

    return None


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
        return None, []

    if BLOCK_SELECTORS[0] in valid_blocks:
        env = "단일스블"
    elif any(sel in valid_blocks for sel in BLOCK_SELECTORS[1:4]):
        env = "다중스블"
    else:
        env = "구분없음"

    return env, valid_blocks


# ============================
# 블로그 템플릿 파싱
# ============================
def parse_blog_template(page):
    posts = []

    env, valid_blocks = get_env_state(page)
    if not valid_blocks:
        return posts, env

    for sel in valid_blocks:
        blocks = page.locator(sel)

        for i in range(blocks.count()):
            block = blocks.nth(i)
            items = block.locator('[data-template-id="ugcItem"]')

            for j in range(items.count()):
                item = items.nth(j)
                data = extract_item(item)
                if data:
                    posts.append(data)

    return posts, env


# ============================
# 동일 블로그 판단
# ============================
def is_same_blog(url1, url2):
    if not url1 or not url2:
        return False

    try:
        p1 = urlparse(url1).path.strip("/").split("/")
        p2 = urlparse(url2).path.strip("/").split("/")
        return p1[0] == p2[0] and p1[1] == p2[1]
    except IndexError:
        return False


# ============================
# 키워드별 노출 여부 판단
# ============================
def get_rank_for_keyword(page, keyword, target_url=None):
    page.goto(
        f"https://search.naver.com/search.naver?query={keyword}",
        wait_until="domcontentloaded"
    )
    page.wait_for_timeout(2000)

    posts, env = parse_blog_template(page)

    if not posts:
        return 0, "블로그 블록 없음"

    for post in posts:
        if is_same_blog(target_url, post["url"]):
            return 1, env

    return 0, env


# ============================
# Summary 시트 작성
# ============================
def write_summary(records: dict):
    rows = []

    for keyword, data in records.items():
        rows.append({
            "키워드": keyword,
            "노출횟수": data["cnt"],
            "환경": data["env"]
        })

    df_summary = pd.DataFrame(rows)

    with pd.ExcelWriter(
        os.path.join(BASE_DIR, "..", "output_rank.xlsx"),
        engine="openpyxl",
        mode="a",
        if_sheet_exists="replace"
    ) as writer:
        df_summary.to_excel(writer, sheet_name="Summary", index=False)


# ============================
# 메인 실행부
# ============================
def main():
    start_time = datetime.datetime.now()

    df = pd.read_excel(os.path.join(BASE_DIR, "..", "input.xlsx"))
    records = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/16.0 Mobile/15E148 Safari/604.1"
            )
        )
        page = context.new_page()

        for idx, row in df.iterrows():
            keyword_raw = row["keyword"]
            target_url = row.get("url")

            exposure, env = get_rank_for_keyword(page, keyword_raw, target_url)

            keyword = keyword_raw.replace(" ", "").upper()

            if keyword not in records:
                records[keyword] = {
                    "cnt": 1 if exposure else 0,
                    "env": env
                }
            else:
                if exposure:
                    records[keyword]["cnt"] += 1

            df.at[idx, "exposure"] = exposure
            df.at[idx, "env"] = env

            print(f"{keyword} → exposure={exposure}, env={env}")
            time.sleep(2)

        browser.close()

    df.to_excel(os.path.join(BASE_DIR, "..", "output_rank.xlsx"), index=False)
    write_summary(records)

    elapsed = datetime.datetime.now() - start_time
    print(f"Completed! 실행시간: {elapsed}")


if __name__ == "__main__":
    main()

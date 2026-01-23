import time
import pandas as pd
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse


# ----------------------------
# 개별 아이템 추출
# ----------------------------
def extract_item(item, rank, env):
    title = ""
    href = ""

    selectors = [
        ('a[data-heatmap-target=".tit"] span.sds-comps-text', 'a[data-heatmap-target=".tit"]'),
        ('a[data-heatmap-target=".link"] span.sds-comps-text', 'a[data-heatmap-target=".link"]'),
        ('a[data-heatmap-target=".imgtitlelink"] span.sds-comps-text', 'a[data-heatmap-target=".imgtitlelink"]'),
    ]

    for title_sel, link_sel in selectors:
        title_el = item.locator(title_sel)
        if title_el.count() > 0:
            title = title_el.first.inner_text().strip()
            link_el = item.locator(link_sel)
            if link_el.count() > 0:
                href = link_el.first.get_attribute("href") or ""

            return {
                "rank": rank,
                "title": title,
                "url": href,
                "env": env
            }

    return None


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


# ----------------------------
# 블록 타입 판별
# ----------------------------
def determine_block_type(page):
    for idx, selector in enumerate(BLOCK_SELECTORS):
        if page.locator(selector).count() > 0:
            return idx
    return None


# ----------------------------
# 블로그 템플릿 파싱
# ----------------------------
def parse_blog_template(page):
    kind = determine_block_type(page)
    if kind is None:
        return None

    if kind == 0:
        env = "Sole Block"
    elif kind in [1, 2, 3]:
        env = "Several Blocks"
    elif kind == 4:
        env = "주제판 없음"
    else:
        env = "블로그 블록 없음"

    selector = BLOCK_SELECTORS[kind]
    blocks = page.locator(selector)

    results = []

    for i in range(blocks.count()):
        block = blocks.nth(i)
        items = block.locator('[data-template-id="ugcItem"]')

        for j in range(items.count()):
            item = items.nth(j)
            data = extract_item(item, rank=len(results) + 1, env=env)
            if data:
                results.append(data)

    return results


# ----------------------------
# 동일 블로그 판단
# ----------------------------
def is_same_blog(url1, url2):
    if not url1 or not url2:
        return False

    try:
        p1 = urlparse(url1).path.strip("/").split("/")
        p2 = urlparse(url2).path.strip("/").split("/")
        return p1[0] == p2[0] and p1[1] == p2[1]
    except IndexError:
        return False


# ----------------------------
# 키워드별 순위 계산
# ----------------------------
def get_rank_for_keyword(page, keyword, target_url=None, target_title=None):
    page.goto(
        f"https://search.naver.com/search.naver?query={keyword}",
        wait_until="domcontentloaded"
    )
    page.wait_for_timeout(2000)

    items = parse_blog_template(page)
    if not items:
        return 0, "블로그 블록 없음"

    for item in items:
        if is_same_blog(target_url, item["url"]) or (
            target_title and target_title.strip() == item["title"]
        ):
            return item["rank"], item["env"]

    return 0, items[0]["env"]


# ----------------------------
# Summary 시트 작성
# ----------------------------
def write_summary(items: dict):
    rows = []

    for keyword, data in items.items():
        rows.append({
            "키워드": keyword,
            "노출횟수": data["cnt"],
            "환경": data["env"]
        })

    df_summary = pd.DataFrame(rows)

    with pd.ExcelWriter(
        "Output_rankB.xlsx",
        engine="openpyxl",
        mode="a",
        if_sheet_exists="replace"
    ) as writer:
        df_summary.to_excel(writer, sheet_name="Summary", index=False)


# ----------------------------
# 메인
# ----------------------------
def main():
    df = pd.read_excel("inputB.xlsx")
    items = {}  # 키워드별 누적 dict

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
            target_title = row.get("title")

            rank, env = get_rank_for_keyword(
                page, keyword_raw, target_url, target_title
            )

            keyword = keyword_raw.replace(" ", "").upper()

            if keyword not in items:
                items[keyword] = {
                    "cnt": 1 if rank > 0 else 0,
                    "env": env
                }
            else:
                if rank > 0:
                    items[keyword]["cnt"] += 1

            df.at[idx, "rank"] = rank
            df.at[idx, "env"] = env

            print(f"{keyword} → rank={rank}, env={env}")
            time.sleep(2)

        browser.close()

    df.to_excel("Output_rankB.xlsx", index=False)
    write_summary(items)
    print("완료!")


if __name__ == "__main__":
    main()

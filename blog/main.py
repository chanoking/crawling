import time
import pandas as pd
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse


target_blog_name = "푸드케어 클레"

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


# ----------------------------
# 블로그 템플릿 파싱
# ----------------------------
def parse_blog_template(page):
    validBlocks = detect_blocks(page, BLOCK_SELECTORS)

    if len(validBlocks) == 0:
        return None

    # 단일 블록인지 체크
    if BLOCK_SELECTORS[0] in validBlocks:
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
                blog_name_el = item.locator(
                    'a[data-heatmap-target="articleSourceJSX_title"] span.sds-comps-text'
                )

                if blog_name_el.count() > 0:
                    blog_name = blog_name_el.first.inner_text().strip()
                    if blog_name == target_blog_name:
                        cnt += 1

        return {"cnt": cnt, "env": env}


# ----------------------------
# 키워드별 순위 계산
# ----------------------------
def get_rank_for_keyword(page, keyword):
    page.goto(
        f"https://search.naver.com/search.naver?query={keyword}",
        wait_until="domcontentloaded"
    )
    page.wait_for_timeout(2000)

    items = parse_blog_template(page)

    if not items:
        return 0, "블로그 블록 없음"

    return items["cnt"], items["env"]


# ----------------------------
# 메인
# ----------------------------
def main():
    df = pd.read_excel("input.xlsx")

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
            keyword = row["keyword"]
            cnt, env = get_rank_for_keyword(page, keyword)

            df.at[idx, "cnt"] = cnt
            df.at[idx, "env"] = env

            print(f"{keyword} → cnt={cnt}, env={env}")
            time.sleep(2)

        browser.close()

    df.to_excel("output_rank.xlsx", index=False)
    print("완료!")


if __name__ == "__main__":
    main()

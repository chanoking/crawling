import time
import pandas as pd
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse

# -----------------------------
# 1. 인플루언서 템플릿 판별
# -----------------------------
def detect_influencer_template(page):
    if page.locator(
        '[data-block-id="ugc/prs_template_ugc_influencer_collection_mo.ts"]'
    ).count() > 0:
        return "collection"
    if page.locator(
        '[data-block-id="ugc/prs_template_ugc_influencer_participation_mo.ts"]'
    ).count() > 0:
        return "participation"
    return None

blog_names = [
                "모모둥이", "아쿵아쿵", "셀럽주부", "안탈리아", "민들레", "v봉봉댁v", 
                "소신있는라이프", "푸들ol", "류애", "수미지", "갬성언니", 
]

# -----------------------------
# 2. 실제 글 URL 추출
# -----------------------------
def extract_item(item, i):
    title = ""
    blog_title_el = item.locator(".sds-comps-text")
    if blog_title_el.count() > 0:
        blog_title = title_el.first.inner_text().strip()

    if blog_title in blog_names:
        return i

    return 0

def parse_template_get_result(page, version):
    templates = 
                [
                    '[data-block-id="ugc/prs_template_ugc_influencer_collection_mo.ts"]', 
                    '[data-block-id="ugc/prs_template_ugc_influencer_participation_mo.ts"]'
                ]
    block = page.locator(templates[version])
    items = block.locator('[data-template-id="ugcItemMo"]')
    for i in range(items.count()):
        item = items.nth(i)
        rank = extract_item(item, i+1)
        if rank > 0:
            return rank
    
    return 0

# -----------------------------
# 5. URL 핵심 비교 함수
# -----------------------------
def is_same_blog(url1, url2):
    if not url1 or not url2:
        return False
    parts1 = urlparse(url1).path.split("/")
    parts2 = urlparse(url2).path.split("/")
    try:
        blog1, log1 = parts1[1], parts1[4]
        blog2, log2 = parts2[1], parts2[4]
        return blog1 == blog2 and log1 == log2
    except IndexError:
        return False

# -----------------------------
# 6. 키워드 하나 처리 (순위 반환 + 디버그 출력)
# -----------------------------
def get_rank_for_keyword(page, keyword, target_url=None, target_title=None):
    url = f"https://search.naver.com/search.naver?query={keyword}"
    page.goto(url)
    time.sleep(2)

    template = detect_influencer_template(page)
    if not template:
        print("템플릿 없음")
        return "블록미존재"

    rank = parse_template(page, 0) if template == "collection" else parse_template(page, 1)

    return rank

# -----------------------------
# 7. 메인 실행
# -----------------------------
def main():
    df = pd.read_excel("input.xlsx")  # keyword, target_url, target_title 필수

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )

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
                rank = get_rank_for_keyword(page, keyword)
            except Exception as e:
                print("[ERROR]", e)
                rank = 0

            df.at[idx, "rank"] = rank
            print(f"순위: {rank}")
            time.sleep(2)

        browser.close()

    df.to_excel("output_rank.xlsx", index=False)
    print("완료! output_rank_debug.xlsx 저장됨")

if __name__ == "__main__":
    main()

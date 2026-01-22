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

# -----------------------------
# 2. 실제 글 URL 추출
# -----------------------------
def extract_item(item, rank):
    title = ""
    title_el = item.locator(".fds-comps-text")
    if title_el.count() > 0:
        title = title_el.first.inner_text().strip()

    href = ""
    all_links = item.locator("a").all()
    for l in all_links:
        h = l.get_attribute("href") or ""
        if "/contents/internal/" in h:
            href = h
            break

    return {"rank": rank, "title": title, "url": href}

# -----------------------------
# 3. collection 파서
# -----------------------------
def parse_collection(page):
    block = page.locator(
        '[data-block-id="ugc/prs_template_ugc_influencer_collection_mo.ts"]'
    )
    items = block.locator('[data-template-id="ugcItemMo"]')
    results = []
    for i in range(items.count()):
        item = items.nth(i)
        results.append(extract_item(item, rank=i + 1))
    return results

# -----------------------------
# 4. participation 파서
# -----------------------------
def parse_participation(page):
    block = page.locator(
        '[data-block-id="ugc/prs_template_ugc_influencer_participation_mo.ts"]'
    )
    items = block.locator('[data-template-id="ugcItemMo"]')
    results = []
    for i in range(items.count()):
        item = items.nth(i)
        results.append(extract_item(item, rank=i + 1))
    return results

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
        return 0

    items = parse_collection(page) if template == "collection" else parse_participation(page)

    rank = 0
    print(f"=== 디버그: 키워드 '{keyword}' 상위 글 비교 ===")
    for item in items:
        is_match_url = is_same_blog(target_url, item["url"])
        is_match_title = not is_match_url and target_title and target_title.strip() == item["title"]

        print(f"[DEBUG] 입력 URL: {target_url}")
        print(f"[DEBUG] 상위 글 URL: {item['url']} -> URL 일치? {is_match_url}")
        print(f"[DEBUG] 입력 Title: {target_title}")
        print(f"[DEBUG] 상위 글 Title: {item['title']} -> Title 일치? {is_match_title}")
        print(f"[DEBUG] 예상 순위: {item['rank']}")
        print("----------------------------")

        if is_match_url or is_match_title:
            rank = item["rank"]
            break

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
            target_url = row.get("target_url")
            target_title = row.get("target_title")

            try:
                rank = get_rank_for_keyword(page, keyword, target_url, target_title)
            except Exception as e:
                print("[ERROR]", e)
                rank = 0

            df.at[idx, "rank"] = rank
            print(f"최종 순위: {rank}")
            time.sleep(2)

        browser.close()

    df.to_excel("output_rank_debug.xlsx", index=False)
    print("완료! output_rank_debug.xlsx 저장됨")

if __name__ == "__main__":
    main()

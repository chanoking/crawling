import time
import pandas as pd
from playwright.sync_api import sync_playwright

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
# 2. 공통 아이템 추출 (실제 글 URL 가져오기)
# -----------------------------
def extract_item(item, rank, template=None):
    # 1. 제목 추출
    title = ""
    title_el = item.locator(".fds-comps-text")
    if title_el.count() > 0:
        title = title_el.first.inner_text().strip()

    # 2. 실제 글 URL 찾기
    href = ""
    all_links = item.locator("a").all()
    for l in all_links:
        h = l.get_attribute("href") or ""
        if "/contents/internal/" in h:  # 실제 글 URL 패턴
            href = h
            break

    return {
        "rank": rank,
        "title": title,
        "url": href
    }

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
        results.append(extract_item(item, rank=i + 1, template="collection"))

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
        results.append(extract_item(item, rank=i + 1, template="participation")) 

    return results

# -----------------------------
# 5. 키워드 하나 처리
# -----------------------------
def check_keyword(page, keyword):
    url = f"https://search.naver.com/search.naver?query={keyword}"
    page.goto(url)

    print("접속 URL:", page.url)  # 디버깅용
    template = detect_influencer_template(page)
    print("감지된 템플릿:", template)

    if template == "collection":
        return parse_collection(page)
    elif template == "participation":
        return parse_participation(page)

    return []

# -----------------------------
# 6. 메인 실행
# -----------------------------
def main():
    df = pd.read_excel("input.xlsx")  # keyword 컬럼 필수

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
            print("\n==============================")
            print("키워드:", keyword)

            try:
                results = check_keyword(page, keyword)
            except Exception as e:
                print("[ERROR]", e)
                results = []

            # 최대 3개만 기록
            for i in range(3):
                if i < len(results):
                    df.at[idx, f"top{i+1}_title"] = results[i]["title"]
                    df.at[idx, f"top{i+1}_url"] = results[i]["url"]
                else:
                    df.at[idx, f"top{i+1}_title"] = ""
                    df.at[idx, f"top{i+1}_url"] = ""

            print("결과:", results)
            time.sleep(3)

        browser.close()

    df.to_excel("output_debug.xlsx", index=False)

if __name__ == "__main__":
    main()

import time
import pandas as pd
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse


# ----------------------------
# 개별 아이템 추출
# ----------------------------
def extract_item(item, rank):
    title = ""
    href = ""

    # 제목 (제목 전용 셀렉터)
    title_el = item.locator(
        'a[data-heatmap-target=".tit"] span.sds-comps-text'
    )
    title_elB = item.locator(
        'a[data-heatmap-target=".link"] span.sds-comps-text'
    )
    if title_el.count() > 0:
        title = title_el.first.inner_text().strip()
        # URL (제목 링크만)
        link_el = item.locator('a[data-heatmap-target=".tit"]')
        if link_el.count() > 0:
            href = link_el.first.get_attribute("href") or ""

        return {
            "rank": rank,
            "title": title,
            "url": href
        }
    if title_elB.count() > 0:
        title = title_elB.first.inner_text().strip()
        # URL (제목 링크만)
        link_el = item.locator('a[data-heatmap-target=".link"]')
        if link_el.count() > 0:
            href = link_el.first.get_attribute("href") or ""

        return {
            "rank": rank,
            "title": title,
            "url": href
        }
    
    



# ----------------------------
# 블로그 템플릿 파싱
# ----------------------------
def parse_blog_template(page):
    selector = '[data-block-id="review/prs_template_v2_review_ugc_single_intention_mo.ts"]'

    if page.locator(selector).count() == 0:
        return None

    block = page.locator(selector)
    items = block.locator('[data-template-id="ugcItem"]')

    results = []
    count = items.count()
    for i in range(count):
        item = items.nth(i)
        results.append(extract_item(item, rank=i + 1))

    return results


# ----------------------------
# 동일 블로그 글 여부 판단
# ----------------------------
def is_same_blog(url1, url2):
    if not url1 or not url2:
        return False

    p1 = urlparse(url1)
    p2 = urlparse(url2)

    parts1 = p1.path.strip("/").split("/")
    parts2 = p2.path.strip("/").split("/")

    try:
        blog1, log1 = parts1[0], parts1[1]
        blog2, log2 = parts2[0], parts2[1]

        print(f"[DEBUG] blog1={blog1}, log1={log1}")
        print(f"[DEBUG] blog2={blog2}, log2={log2}")

        return blog1 == blog2 and log1 == log2
    except IndexError:
        return False



# ----------------------------
# 키워드별 순위 계산
# ----------------------------
def get_rank_for_keyword(page, keyword, target_url=None, target_title=None):
    url = f"https://search.naver.com/search.naver?query={keyword}"
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    items = parse_blog_template(page)

    if items is None:
        return "단일 스불 아님"

    for item in items:
        is_match_url = is_same_blog(target_url, item["url"])
        is_match_title = (
            (not is_match_url)
            and (target_title is not None)
            and (target_title.strip() == item["title"])
        )

        print(f"keyword: {keyword}")
        print(f"[DEBUG] 입력 URL: {target_url}")
        print(f"[DEBUG] 상위 글 URL: {item['url']} -> URL 일치? {is_match_url}")
        print(f"[DEBUG] 입력 Title: {target_title}")
        print(f"[DEBUG] 상위 글 Title: {item['title']} -> Title 일치? {is_match_title}")
        print(f"[DEBUG] 예상 순위: {item['rank']}")
        print("-" * 30)

        if is_match_url or is_match_title:
            return item["rank"]

    return 0


# ----------------------------
# 메인 실행
# ----------------------------
def main():
    df = pd.read_excel("inputB.xlsx")

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
            target_url = row.get("url")
            target_title = row.get("title")

            try:
                rank = get_rank_for_keyword(
                    page,
                    keyword,
                    target_url,
                    target_title
                )
            except Exception as e:
                print("[ERROR]", e)
                rank = 0

            df.at[idx, "rank"] = rank
            print(f"최종 순위: {rank}")
            time.sleep(2)

        browser.close()

    df.to_excel("Output_rankB.xlsx", index=False)
    print("Successfully downloaded a new file")


if __name__ == "__main__":
    main()

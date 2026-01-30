import time
import pandas as pd
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse
import datetime, os
from dotenv import load_dotenv
import yagmail

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, "..", "..", ".env")

load_dotenv(ENV_PATH)

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
    href = ""
    all_links = item.locator("a").all()
    for l in all_links:
        h = l.get_attribute("href") or ""
        if "/contents/internal/" in h:
            href = h
            break

    return {"rank": rank, "url": href}


def parse_template(page, version):
    selectors = ['[data-block-id="ugc/prs_template_ugc_influencer_collection_mo.ts"]',
                '[data-block-id="ugc/prs_template_ugc_influencer_participation_mo.ts"]']
    block = page.locator(selectors[version])
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
def get_rank_for_keyword(page, keyword, target_url=None):
    url = f"https://search.naver.com/search.naver?query={keyword}"
    page.goto(url)
    time.sleep(2)

    template = detect_influencer_template(page)
    if not template:
        print("템플릿 없음")
        return 0

    items = parse_template(page, 0) if template == "collection" else parse_template(page, 1)

    rank = 0
    for item in items:
        is_match_url = is_same_blog(target_url, item["url"])

        if is_match_url:
            rank = item["rank"]
            break

    return rank

# -----------------------------
# 7. 메인 실행
# -----------------------------
def main():
    start_time = datetime.datetime.now()
    df = pd.read_excel(os.path.join(BASE_DIR, "..", "keychal_input.xlsx")) 
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
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

            try:
                rank = get_rank_for_keyword(page, keyword, target_url)
            except Exception as e:
                print("[ERROR]", e)
                rank = 0

            df.at[idx, "rank"] = rank
            print(f"keyword: {keyword}  순위: {rank}")

        browser.close()
    
    end_time = datetime.datetime.now()
    df.to_excel(os.path.join(BASE_DIR, "..", "keychal_output_rank.xlsx"), index=False)
    print("완료! keychal_output_rank.xlsx 저장됨")
    elapsed = end_time - start_time
    print(f"elapsed_time: {elapsed}")

sender_email = "chanhojin94@gmail.com"
app_password = os.getenv("APP_PASSWORD")
yag = yagmail.SMTP(sender_email, app_password)

receiver_email = "chano94@lifenbio.com"
subject = "Ranking Fetch Output"
contents = "Uploaed the output file"

if __name__ == "__main__":
    main()

attachment = os.path.join(BASE_DIR, "..", "keychal_output_rank.xlsx")
yag.send(to=receiver_email, subject=subject, contents=contents, attachments=attachment)
print("Completed forwoarding the file to wanted place")
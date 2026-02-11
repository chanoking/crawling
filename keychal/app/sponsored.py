import time
import pandas as pd
from playwright.sync_api import sync_playwright
import datetime, os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from common import get_db
from common import forward_to_other

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

db = get_db()

collection_input = db["sponsored_input"]
cursor = collection_input.find({})
data_list_input = list(cursor)

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

def extract_item(item, i, blog_name):
    blog_title_el = item.locator(".sds-comps-text")
    if blog_title_el.count() > 0:
        blog_title = blog_title_el.first.inner_text().strip()
        if blog_title == blog_name:
            return i

    return 0

def parse_template_get_result(page, version, blog_name):
    templates = [
                    '[data-block-id="ugc/prs_template_ugc_influencer_collection_mo.ts"]', 
                    '[data-block-id="ugc/prs_template_ugc_influencer_participation_mo.ts"]'
                ]
    block = page.locator(templates[version])
    items = block.locator('[data-template-id="ugcItemMo"]')
    for i in range(items.count()):
        item = items.nth(i)
        rank = extract_item(item, i+1, blog_name)
        if rank > 0:
            return rank
    
    return 0

def get_rank_for_keyword(page, keyword, blog_name):
    url = f"https://search.naver.com/search.naver?query={keyword}"
    page.goto(url)
    time.sleep(2)

    template = detect_influencer_template(page)
    if not template:
        print("템플릿 없음")
        return "블록미존재"

    rank = parse_template_get_result(page, 0, blog_name) if template == "collection" else parse_template_get_result(page, 1, blog_name)

    return rank

def main():
    start_time = datetime.datetime.now()
    df = pd.DataFrame(data_list_input)

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
            blog_name = row["blog_name"]

            try:
                rank = get_rank_for_keyword(page, keyword, blog_name)
            except Exception as e:
                print("[ERROR]", e)
                rank = 0

            df.at[idx, "rank"] = rank
            print(f"키워드: {keyword}  인플루언서: {blog_name}  순위: {rank}" )

        browser.close()

    end_time = datetime.datetime.now()
    df.to_excel(os.path.join(BASE_DIR, "..", "..", "output", "sponsor_output.xlsx"), index=False)
    print("완료! sponsor_output.xlsx 저장됨")
    elapsed = end_time - start_time
    print(f"실행시간: {elapsed}")

if __name__ == "__main__":
    main()
    forward_to_other("sponsor_output.xlsx")

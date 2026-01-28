import time
import pandas as pd
from playwright.sync_api import sync_playwright
import datetime, os
import yagmail
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, "..", "..", ".env") 

load_dotenv(ENV_PATH)

with open("scheduler.log", "a", encoding="utf-8") as f:
    f.write(f"{datetime.datetime.now()} 실행됨, cwd={os.getcwd()}\n")


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
    elif blog_name == "모모둥이":
        blog_name = "아쿵아쿵"
        if blog_name == blog_title:
            return i
    elif blog_name == "셀럽주부":
        blog_name = "안탈리아"
        if blog_name == blog_title:
            return i
    elif blog_name == "봉봉댁":
        blog_name = "v봉봉댁v"
        if blog_name == blog_title:
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
    df = pd.read_excel(os.path.join(BASE_DIR, "..", "input.xlsx"))

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
            time.sleep(2)

        browser.close()

    end_time = datetime.datetime.now()
    df.to_excel(os.path.join(BASE_DIR, "..", "output_rank.xlsx"), index=False)
    print("완료! output_rank.xlsx 저장됨")
    elapsed = end_time - start_time
    print(f"실행시간: {elapsed}")


sender_email = "chanhojin94@gmail.com"
app_password = os.getenv("APP_PASSWORD")

receiver_email = "chano94@lifenbio.com"
subject = "Ranking Fetch Output"
contents = "Uploaded the output file"

attachment = os.path.join(BASE_DIR, "..", "output_rank.xlsx")

yag = yagmail.SMTP(sender_email, app_password)

if __name__ == "__main__":
    main()

yag.send(to=receiver_email, subject=subject, contents=contents, attachments=attachment)
print("Completed forwarding to designated place")
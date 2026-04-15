from playwright.sync_api import sync_playwright, TimeoutError
import pandas as pd
import os
import time
import random
from urllib.parse import quote_plus

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

template_map = {
    "collection": '[data-block-id="ugc/prs_template_ugc_influencer_collection_mo.ts"]',
    "participation": '[data-block-id="ugc/prs_template_ugc_influencer_participation_mo.ts"]'
}

def get_y(page, keyword):
    url = f"https://search.naver.com/search.naver?query={quote_plus(keyword)}"
    try:
        page.goto(url, timeout=15000)
        page.wait_for_load_state("domcontentloaded")

        collection = page.locator(template_map["collection"]).first
        participation = page.locator(template_map["participation"]).first

        page.wait_for_selector(
            f'{template_map["collection"]}, {template_map["participation"]}',
             timeout=3000
        )

        try:
            collection.wait_for(state="visible", timeout=1000)
            box = collection.bounding_box()
            return box["y"] if box else "알수없음"
        except Exception as e:
            print("collection error:", e)
            pass

        try:
            participation.wait_for(state="visible", timeout=1000)
            box = participation.bounding_box()
            return box["y"] if box else "알수없음"
        except Exception as e:
            print("participation error:", e)
            pass
        
        return "알수없음"

    except TimeoutError:
        print("timeout error 발생")
        return "알수없음"

def main():
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

        df = pd.read_excel("keywords_test.xlsx")

        for row in df.itertuples():
            keyword = row.keyword

            try:
                time.sleep(random.uniform(1.0, 2.0))
                y = get_y(page, keyword)
                df.at[row.Index, "y"] = y

            except Exception as e:
                print("[ERROR]", e)
                y = "확인불가"
                df.at[row.Index, "y"] = y
            
            print(f"{row.Index + 1} of {len(df)} - {keyword}: {y}")

        df.to_excel(os.path.join(BASE_DIR, "..", "output", "keychal_y.xlsx"), index=False)

        print("감사합니다:)")

if __name__ == "__main__":
    main()



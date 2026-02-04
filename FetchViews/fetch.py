import pandas as pd
from playwright.sync_api import sync_playwright
import datetime, os
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_view_for_keyword(page, keyword):
    page.goto(
        f"https://surffing.net/keyword/{keyword}",
        wait_until="domcontentloaded"
    )
    time.sleep(2)

    viewSel = page.locator('#keywordResults td.num-total')

    view = 10

    if viewSel.count() > 0:
        raw = viewSel.first.inner_text().strip()
        view = int(raw.replace(",", ""))

    return view


def main():
    start_time = datetime.datetime.now()
    df = pd.read_excel(os.path.join(BASE_DIR, "input.xlsx"))

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
            view = get_view_for_keyword(page, keyword)

            df.at[idx, "view"] = view
            print(f"{keyword} -> view = {view}")

        browser.close()

    end_time = datetime.datetime.now()
    elapsed = end_time - start_time

    df.to_excel(os.path.join(BASE_DIR, "output_rank.xlsx"), index=False)

    print("Completed!")
    print(f"실행시간: {elapsed}")


if __name__ == "__main__":
    main()
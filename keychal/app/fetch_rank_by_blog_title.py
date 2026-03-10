import time
import datetime
import os
import sys
from playwright.sync_api import sync_playwright, TimeoutError
from bson import ObjectId

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from common import get_db, get_keyword_volume, upload

db = get_db()

# -------------------------------
# 키워드 → 인플루언서 매핑
# -------------------------------
input_keychal = {}

keywords = list(
    db["Keychal_Keywords"].find({}, {"_id": 0, "keyword": 1, "influencer_id": 1})
)

for doc in keywords:
    infl = db["Keychal_Influencers"].find_one(
        {"_id": ObjectId(doc["influencer_id"])},
        {"_id": 0, "influencer": 1}
    )
    if infl:
        input_keychal[doc["keyword"]] = infl["influencer"]

# -------------------------------
# 템플릿 감지
# -------------------------------
def detect_influencer_template(page):
    if page.locator('[data-block-id="ugc/prs_template_ugc_influencer_collection_mo.ts"]').first.is_visible():
        return "collection"

    if page.locator('[data-block-id="ugc/prs_template_ugc_influencer_participation_mo.ts"]').first.is_visible():
        return "participation"

    return None


# -------------------------------
# 블로그 문구 검사 (새 탭 사용)
# -------------------------------
def check_phrase(context, href):
    page2 = context.new_page()
    try:
        page2.goto(href, timeout=10000)
        page2.wait_for_load_state("networkidle")

        paragraphs = page2.locator(".se-text-paragraph")

        # print(f"parapraphs: {paragraphs}")
        count = paragraphs.count()

        for i in range(count):
            text = paragraphs.nth(i).inner_text()
            # print(f"text: {text}")
            if "포스팅은 논문 자료조사 활동의 일환으로" in text:
                page2.close()
                return True

    except Exception:
        pass

    page2.close()
    return False


# -------------------------------
# 개별 아이템에서 순위 찾기
# -------------------------------
def extract_item(item, rank_index, blog_name, context):
    title_el = item.locator(".sds-comps-text").first
    if not title_el:
        return 0

    blog_title = title_el.inner_text().strip()
    # print(f"blog_title: {blog_title}")

    # 블로그명 예외 매핑
    alias_map = {
        "모모둥이": "아쿵아쿵",
        "셀럽주부": "안탈리아",
        "봉봉댁": "v봉봉댁v",
        "갬성주부": "갬성언니"
    }

    valid_names = [blog_name]
    if blog_name in alias_map:
        valid_names.append(alias_map[blog_name])

    if blog_title in valid_names:
        all_links = item.locator("a").all()
        for l in all_links:
            h = l.get_attribute("href") or ""
            if "/contents/internal" in h:
                if check_phrase(context, h):
                    return rank_index
        
    return 0


# -------------------------------
# 템플릿 파싱
# -------------------------------
def parse_template(page, context, template_type, blog_name):

    template_map = {
        "collection": '[data-block-id="ugc/prs_template_ugc_influencer_collection_mo.ts"]',
        "participation": '[data-block-id="ugc/prs_template_ugc_influencer_participation_mo.ts"]'
    }

    block = page.locator(template_map[template_type])
    y = block.bounding_box()["y"]

    items = block.locator('[data-template-id="ugcItemMo"]')
    count = items.count()

    for i in range(count):
        item = items.nth(i)
        rank = extract_item(item, i + 1, blog_name, context)
        if rank > 0:
            return rank, y

    return 0, y


# -------------------------------
# 키워드 검색
# -------------------------------
def get_rank_for_keyword(page, context, keyword, blog_name):

    url = f"https://search.naver.com/search.naver?query={keyword}"

    try:
        page.goto(url, timeout=15000)
        page.wait_for_load_state("networkidle")
    except TimeoutError:
        return "접속실패", "알수없음"

    template = detect_influencer_template(page)
    if not template:
        return "블록미존재", "알수없음"

    return parse_template(page, context, template, blog_name)


# -------------------------------
# 검색량 가져오기
# -------------------------------
def get_key_vol(keyword):
    try:
        data = get_keyword_volume(keyword)
        for row in data.get("keywordList", []):
            if row["relKeyword"] == keyword:
                return row["monthlyPcQcCnt"], row["monthlyMobileQcCnt"], row["compIdx"]
    except Exception:
        pass

    return 10, 10, "알수없음"


# -------------------------------
# MAIN
# -------------------------------
def main():
    start_time = datetime.datetime.now()

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

        for keyword, blog_name in input_keychal.items():

            try:
                rank, y = get_rank_for_keyword(page, context, keyword, blog_name)
                pc, mobile, competition = get_key_vol(keyword)

            except Exception as e:
                print("[ERROR]", e)
                rank = 0
                y = "확인불가"
                pc = mobile = competition = "확인불가"

            state = {
                "keyword": keyword,
                "influencer": blog_name,
                "date": datetime.date.today().isoformat(),
                "mobile": mobile,
                "pc": pc,
                "y": y,
                "competition": competition,
                "rank": rank,
            }

            upload(state, "Keychal_States")

            print(f"[{keyword}] {blog_name} | rank: {rank} | y: {y} | mobile: {mobile}")

        browser.close()

    elapsed = datetime.datetime.now() - start_time
    print("완료!")
    print("실행시간:", elapsed)


if __name__ == "__main__":
    main()
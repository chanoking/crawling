from pymongo import MongoClient
import os
from dotenv import load_dotenv
import yagmail
import time
import hmac
import hashlib
import base64
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_PATH)

MONGO_URI = os.getenv("MONGO_URI")
API_KEY = os.getenv("NAVER_API_KEY")
SECRET_KEY = os.getenv("NAVER_SECRET_KEY")
CUSTOMER_ID = os.getenv("NAVER_CUSTOMER_ID")

BASE_URL = "https://api.searchad.naver.com"
URI = "/keywordstool"
METHOD = "GET"

client = MongoClient(MONGO_URI)
db = client["LifeNBio"]

def get_db():
    return db

# ---------------------------------------------------------

sender_email = "chanhojin94@gmail.com"
app_password = os.getenv("APP_PASSWORD")

receiver_email = "chano94@lifenbio.com"
subject = "결과파일"
contents = ""

receiver_emails = ["chano94@lifenbio.com", "jk022z@lifenbio.com"]
yag = yagmail.SMTP(sender_email, app_password)

# ----------------------------------------------------------

def forward(file_name, subject):
    attachment = os.path.join(BASE_DIR, "output", file_name)
    yag.send(to=receiver_email, subject=subject, contents=contents, attachments=attachment)
    print("Completed forwarding to designated place")

# ----------------------------------------------------------
def forward_to_other(file_name, subject):
    attachment = os.path.join(BASE_DIR, "output", file_name)
    yag.send(to=receiver_emails, subject=subject, contents=contents, attachments=attachment)
    print("Completed forwarding to designated places")
#------------------------------------------------------------ 
def make_signature(timestamp, method, uri, secret_key):
    message = f"{timestamp}.{method}.{uri}"
    hash = hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).digest()
    return base64.b64encode(hash).decode()

#------------------------------------------------------------
def get_keyword_volume(keyword):
    timestamp = str(int(time.time() * 1000))
    signature = make_signature(timestamp, METHOD, URI, SECRET_KEY)

    headers = {
        "X-Timestamp": timestamp,
        "X-API-KEY": API_KEY,
        "X-Customer": CUSTOMER_ID,
        "X-Signature": signature
    }

    params = {
        "hintKeywords": keyword,
        "showDetail": 1
    }

    res = requests.get(
        BASE_URL + URI,
        headers=headers,
        params=params
    )
    res.raise_for_status()
    return res.json()

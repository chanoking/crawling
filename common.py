from pymongo import MongoClient
import os
from dotenv import load_dotenv
import yagmail

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_PATH)

MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["LifeNBio"]

def get_db():
    return db

sender_email = "chanhojin94@gmail.com"
app_password = os.getenv("APP_PASSWORD")

receiver_email = "chano94@lifenbio.com"
subject = "Ranking Fetch Output"
contents = "Uploaded the output file"

yag = yagmail.SMTP(sender_email, app_password)

def forward(file_name):
    attachment = os.path.join(BASE_DIR, "output", file_name)
    yag.send(to=receiver_email, subject=subject, contents=contents, attachments=attachment)
    print("Completed forwarding to designated place")
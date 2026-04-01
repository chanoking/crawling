from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import pandas as pd
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from common import get_db

app = FastAPI()
db = get_db()

collection = db["sponsored_input"]
collection_foodcare = db["foodcare_input_for_url"]
collection_free = db["Free"]
collection_sponsored = db["sponsored_monthly_fee"]

@app.post("/sponsored_upload")
async def upload_keycahl_excel(
    file: UploadFile = File(...),
    replace: bool = Form(True)
):
    try:
        # 엑셀 읽기
        df = pd.read_excel(file.file)

        # 필수 컬럼 체크
        if not {"keyword", "blog_name"}.issubset(df.columns):
            return JSONResponse(status_code=400, content={"error": "keyword, blog_name 컬럼 필요"})

        data = df.to_dict(orient="records")

        # 기존 데이터 삭제 후 교체
        if replace:
            collection.delete_many({})

        collection.insert_many(data)

        return {"status": "ok", "count": len(data), "replace": replace}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/foodcare_upload")
async def upload_foodcare_excel(
    file: UploadFile = File(...),
    replace: bool = Form(True)
):
    try:
        # 엑셀 읽기
        df = pd.read_excel(file.file)

        # 필수 컬럼 체크
        if not {"url"}.issubset(df.columns):
            return JSONResponse(status_code=400, content={"error": "url 컬럼 필요"})

        data = df.to_dict(orient="records")

        # 기존 데이터 삭제 후 교체
        if replace:
            collection_foodcare.delete_many({})

        # 데이터 삽입
        collection_foodcare.insert_many(data)

        return {"status": "ok", "count": len(data), "replace": replace}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/free_upload")
async def upload_free(
    file: UploadFile = File(...),
    replace: bool = Form(True)
):
    try:
        df = pd.read_excel(file.file)

        if not {"키워드"}.issubset(df.columns):
            return JSONResponse(status_code=400, content={"error": "keyword 컬럼 필요"})

        data = df.to_dict(orient="records")

        if replace:
            collection_free.delete_many({})

        collection_free.insert_many(data)

        return {"status": "ok", "count": len(data), "replace": replace}
    
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/monthly_sponsored_fee")
async def upload_sponsored_monthly_fee(
    file: UploadFile = File(...),
    replace: bool = Form(True)
):
    try:
        df = pd.read_excel(file.file)

        if len(df.columns) < 11:
            raise HTTPException(
                status_code=400,
                detail="첫 번째 행(A1~K1)이 모두 채워져야 합니다."
            )

        for i, col in enumerate(df.columns[:11]):
            if col is None or str(col).strip() == "":
                raise HTTPException(
                    status_code=400,
                    detail=f"{chr(65+i)}1 셀이 비어 있습니다."
                )

        data = df.to_dict(orient="records")

        if replace:
            collection_sponsored.delete_many({})

        collection_sponsored.insert_many(data)

        return {"status": "ok", "count": len(data), "replace": replace}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


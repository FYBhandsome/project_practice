from fastapi import APIRouter, HTTPException
from .sparkAPI import async_main
router = APIRouter()
@router.post("/communicate", summary='AI_大模型平台助手')
async def communicate(text: str):
    try:
        response = await async_main(text)
        return {"code": 200, "data": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

"""
FastAPI 메인 라우터
"""
from fastapi import APIRouter

from .parsing import router as parsing_router
from .documents import router as documents_router
from .system import router as system_router

# 메인 API 라우터 생성
api_router = APIRouter()

# 각 모듈의 라우터 포함
api_router.include_router(parsing_router)
api_router.include_router(documents_router)
api_router.include_router(system_router)

# 루트 엔드포인트
@api_router.get("/")
async def root():
    """
    API 루트 엔드포인트
    """
    return {
        "message": "LangGraph 기반 보험약관 PDF 파싱 시스템 API",
        "version": "0.1.0",
        "docs": "/docs",
        "endpoints": {
            "parsing": "/parse",
            "documents": "/docs",
            "system": "/system"
        }
    }


@api_router.get("/ping")
async def ping():
    """
    API 서버 응답 확인
    """
    return {"status": "ok", "message": "pong"}
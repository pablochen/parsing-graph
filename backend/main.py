"""
FastAPI 메인 애플리케이션
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from .config import settings
from .api.main import api_router

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format=settings.LOG_FORMAT,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log", encoding="utf-8")
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 생명주기 관리
    """
    # 시작 시 초기화
    logger.info("애플리케이션 시작 중...")
    
    try:
        # 디렉토리 생성
        import os
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
        logger.info(f"디렉토리 초기화 완료: {settings.UPLOAD_DIR}, {settings.OUTPUT_DIR}")
        
        # OpenRouter 모델 검증
        from .clients.openrouter_client import validate_model
        if not validate_model(settings.OPENROUTER_MODEL):
            raise ValueError(f"허용되지 않은 모델: {settings.OPENROUTER_MODEL}")
        logger.info(f"OpenRouter 모델 검증 완료: {settings.OPENROUTER_MODEL}")
        
        # LangGraph 파이프라인 초기화
        from .langgraph.graph import default_manager
        graph_status = default_manager.get_status()
        logger.info(f"LangGraph 파이프라인 초기화 완료: {graph_status}")
        
        logger.info("애플리케이션 시작 완료")
        
    except Exception as e:
        logger.error(f"애플리케이션 시작 중 오류: {e}")
        raise
    
    yield
    
    # 종료 시 정리
    logger.info("애플리케이션 종료 중...")
    logger.info("애플리케이션 종료 완료")


# FastAPI 애플리케이션 생성
app = FastAPI(
    title="보험약관 PDF 파싱 시스템",
    description="LangGraph 기반 AI 자동화 PDF 파싱 시스템",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trusted Host 미들웨어 설정
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )


# 전역 예외 핸들러
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP 예외 핸들러"""
    logger.error(f"HTTP 예외: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": exc.status_code,
            "message": exc.detail,
            "timestamp": str(datetime.utcnow())
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """일반 예외 핸들러"""
    logger.error(f"예상치 못한 오류: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": 500,
            "message": "내부 서버 오류가 발생했습니다.",
            "timestamp": str(datetime.utcnow())
        }
    )


# API 라우터 등록
app.include_router(api_router, prefix=settings.API_V1_STR)


# 루트 엔드포인트
@app.get("/")
async def root():
    """
    애플리케이션 루트 엔드포인트
    """
    return {
        "name": "보험약관 PDF 파싱 시스템",
        "version": "0.1.0",
        "description": "LangGraph 기반 AI 자동화 PDF 파싱 시스템",
        "docs": "/docs",
        "api": settings.API_V1_STR,
        "status": "running",
        "environment": settings.ENVIRONMENT,
        "features": [
            "GPT-5 전용 AI 파싱",
            "LangGraph 워크플로우",
            "PyMuPDF 스팬 레벨 처리",
            "자동 page_end 계산",
            "범위 기반 본문 추출",
            "MCP 도구 연동",
            "실시간 진행 상태 스트리밍"
        ]
    }


@app.get("/health")
async def health():
    """
    간단한 헬스체크 엔드포인트
    """
    return {"status": "healthy", "timestamp": str(datetime.utcnow())}


# 미들웨어: 요청 로깅
@app.middleware("http")
async def log_requests(request, call_next):
    """요청 로깅 미들웨어"""
    from datetime import datetime
    import time
    
    start_time = time.time()
    
    # 요청 정보 로깅
    logger.info(f"요청 시작: {request.method} {request.url}")
    
    # 요청 처리
    response = await call_next(request)
    
    # 처리 시간 계산
    process_time = time.time() - start_time
    
    # 응답 정보 로깅
    logger.info(
        f"요청 완료: {request.method} {request.url} - "
        f"상태코드: {response.status_code} - "
        f"처리시간: {process_time:.4f}초"
    )
    
    # 처리 시간을 헤더에 추가
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


if __name__ == "__main__":
    # 개발 서버 실행
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )
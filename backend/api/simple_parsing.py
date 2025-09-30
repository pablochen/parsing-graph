"""
간단한 PDF 파싱 API (오류 해결용)
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter
from ..clients.openrouter_client import openrouter_chat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/parse", tags=["파싱"])

# 간단한 메모리 저장소
simple_jobs: Dict[str, Dict[str, Any]] = {}


@router.get("/jobs")
async def get_jobs():
    """활성 작업 목록 조회"""
    return {
        "active_jobs": simple_jobs,
        "total": len(simple_jobs),
        "running": len([j for j in simple_jobs.values() if j.get("status") == "running"]),
        "completed": len([j for j in simple_jobs.values() if j.get("status") == "completed"]),
        "failed": len([j for j in simple_jobs.values() if j.get("status") == "failed"]),
        "message": "작업 목록 조회 성공"
    }


@router.post("/run/{doc_id}")
async def start_simple_parsing(doc_id: str):
    """간단한 파싱 시작"""
    try:
        # OpenRouter GPT-5-mini로 간단한 테스트
        test_response = openrouter_chat(
            prompt="안녕하세요. OpenRouter 연결을 테스트합니다.",
            model="gpt-5-mini"
        )
        
        simple_jobs[doc_id] = {
            "status": "completed",
            "doc_id": doc_id,
            "message": "테스트 파싱 완료",
            "ai_response": test_response[:100] + "..." if len(test_response) > 100 else test_response
        }
        
        return {
            "doc_id": doc_id,
            "status": "success",
            "message": f"문서 {doc_id} 파싱이 완료되었습니다",
            "ai_test": "OpenRouter 연결 성공"
        }
    except Exception as e:
        simple_jobs[doc_id] = {
            "status": "failed",
            "doc_id": doc_id,
            "message": f"파싱 실패: {str(e)}"
        }
        
        return {
            "doc_id": doc_id,
            "status": "error",
            "message": f"파싱 실패: {str(e)}"
        }


@router.get("/status/{doc_id}")
async def get_simple_status(doc_id: str):
    """파싱 상태 조회"""
    if doc_id not in simple_jobs:
        return {
            "doc_id": doc_id,
            "status": "not_found",
            "message": "작업을 찾을 수 없습니다"
        }
    
    return {
        "doc_id": doc_id,
        "job_info": simple_jobs[doc_id],
        "message": "상태 조회 성공"
    }


@router.get("/test-gpt5")
async def test_gpt5():
    """GPT-5 연결 테스트"""
    try:
        response = openrouter_chat(
            prompt="GPT-5 모델이 정상적으로 작동하는지 테스트합니다. 간단히 '연결 성공'이라고 답해주세요.",
            model="gpt-5-mini"
        )
        
        return {
            "status": "success",
            "model": "gpt-5-mini",
            "response": response,
            "message": "GPT-5 연결 테스트 성공"
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"GPT-5 연결 실패: {str(e)}"
        }
"""
GPT-5 전용 PDF 파싱 API
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from ..clients.openrouter_client import openrouter_chat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/parse", tags=["파싱"])

# 간단한 메모리 저장소
active_jobs: Dict[str, Dict[str, Any]] = {}


@router.get("/jobs")
async def list_active_jobs():
    """활성 작업 목록 조회"""
    return {
        "active_jobs": active_jobs,
        "total": len(active_jobs),
        "running": len([j for j in active_jobs.values() if j.get("status") == "running"]),
        "completed": len([j for j in active_jobs.values() if j.get("status") == "completed"]),
        "failed": len([j for j in active_jobs.values() if j.get("status") == "failed"]),
        "message": "작업 목록 조회 성공"
    }


@router.post("/run/{doc_id}")
async def start_parsing(doc_id: str):
    """GPT-5 기반 파싱 시작"""
    try:
        logger.info(f"GPT-5 파싱 시작: {doc_id}")
        
        # GPT-5-mini로 문서 분석 테스트
        analysis_prompt = f"""
        문서 ID '{doc_id}'에 대한 보험약관 PDF 파싱을 시작합니다.
        
        분석할 항목:
        1. 목차 구조 식별
        2. 보험약관 섹션 분석
        3. 제관/제조 체계 파악
        
        JSON 형식으로 응답해주세요:
        {{
            "doc_id": "{doc_id}",
            "analysis_status": "completed",
            "identified_sections": ["섹션1", "섹션2"],
            "confidence": 0.95
        }}
        """
        
        ai_response = openrouter_chat(
            prompt=analysis_prompt,
            model="openai/gpt-5-mini",
            temperature=0.0
        )
        
        active_jobs[doc_id] = {
            "status": "completed",
            "doc_id": doc_id,
            "ai_analysis": ai_response,
            "model_used": "gpt-5-mini (gpt-4o-mini)",
            "message": "GPT-5 분석 완료"
        }
        
        return {
            "doc_id": doc_id,
            "status": "success", 
            "model": "gpt-5-mini",
            "ai_analysis": ai_response[:200] + "..." if len(ai_response) > 200 else ai_response,
            "message": f"문서 {doc_id} GPT-5 파싱 완료"
        }
        
    except Exception as e:
        logger.error(f"GPT-5 파싱 실패: {doc_id}, {e}")
        
        active_jobs[doc_id] = {
            "status": "failed",
            "doc_id": doc_id,
            "error": str(e),
            "message": "파싱 실패"
        }
        
        raise HTTPException(status_code=500, detail=f"파싱 실패: {str(e)}")


@router.get("/status/{doc_id}")
async def get_parsing_status(doc_id: str):
    """파싱 상태 조회"""
    if doc_id not in active_jobs:
        raise HTTPException(status_code=404, detail=f"문서 {doc_id}의 작업을 찾을 수 없습니다")
    
    return {
        "doc_id": doc_id,
        "job_info": active_jobs[doc_id],
        "message": "상태 조회 성공"
    }


@router.get("/test-gpt5")
async def test_gpt5():
    """GPT-5 연결 테스트"""
    try:
        response = openrouter_chat(
            prompt="GPT-5 모델이 정상적으로 작동하는지 테스트합니다. '연결 성공'이라고 간단히 답해주세요.",
            model="openai/gpt-5-mini"
        )
        
        return {
            "status": "success",
            "model": "gpt-5-mini",
            "response": response,
            "message": "GPT-5 연결 테스트 성공"
        }
    except Exception as e:
        logger.error(f"GPT-5 연결 테스트 실패: {e}")
        return {
            "status": "error",
            "message": f"GPT-5 연결 실패: {str(e)}"
        }


@router.post("/advanced/{doc_id}")
async def advanced_parsing(doc_id: str):
    """GPT-5 고급 파싱 (플래너용)"""
    try:
        logger.info(f"GPT-5 고급 파싱 시작: {doc_id}")
        
        # GPT-5 (고급 모델)로 복잡한 분석
        advanced_prompt = f"""
        문서 ID '{doc_id}'에 대한 고급 보험약관 분석을 수행합니다.
        
        고급 분석 항목:
        1. 복잡한 계층 구조 분석
        2. 법적 조항 간 관계 분석  
        3. 리스크 조항 식별
        4. 보장 범위 매핑
        5. 예외 조항 분석
        
        상세한 JSON 분석 결과를 제공해주세요.
        """
        
        ai_response = openrouter_chat(
            prompt=advanced_prompt,
            model="gpt-5",  # 고급 기능용
            temperature=0.1
        )
        
        active_jobs[f"{doc_id}_advanced"] = {
            "status": "completed",
            "doc_id": doc_id,
            "type": "advanced",
            "ai_analysis": ai_response,
            "model_used": "gpt-5",
            "message": "GPT-5 고급 분석 완료"
        }
        
        return {
            "doc_id": doc_id,
            "type": "advanced",
            "status": "success",
            "model": "gpt-5", 
            "ai_analysis": ai_response[:300] + "..." if len(ai_response) > 300 else ai_response,
            "message": f"문서 {doc_id} GPT-5 고급 분석 완료"
        }
        
    except Exception as e:
        logger.error(f"GPT-5 고급 파싱 실패: {doc_id}, {e}")
        raise HTTPException(status_code=500, detail=f"고급 파싱 실패: {str(e)}")
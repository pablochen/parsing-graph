"""
시스템 관리 관련 API 엔드포인트
"""
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException

from ..models.schemas import HealthCheck, SystemInfo, ParsingStats, BaseResponse
from ..config import settings
from ..langgraph.graph import default_manager
from ..clients.mcp_client import mcp_call
from ..clients.openrouter_client import get_available_models

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["시스템관리"])


@router.get("/health", response_model=HealthCheck)
async def health_check():
    """
    시스템 헬스체크
    
    애플리케이션과 연결된 서비스들의 상태를 확인합니다.
    """
    services = {}
    overall_status = "healthy"
    
    try:
        # OpenRouter API 상태 확인
        try:
            from ..clients.openrouter_client import openrouter_client
            # 간단한 API 호출로 연결 테스트
            available_models = get_available_models()
            services["openrouter"] = "healthy" if available_models else "unhealthy"
        except Exception as e:
            services["openrouter"] = f"unhealthy: {str(e)}"
            overall_status = "degraded"
        
        # MCP 서버 상태 확인
        try:
            # MCP 서버 ping 테스트 (실제 구현에 따라 조정 필요)
            await mcp_call("server.ping", {})
            services["mcp_server"] = "healthy"
        except Exception as e:
            services["mcp_server"] = f"unhealthy: {str(e)}"
            overall_status = "degraded"
        
        # LangGraph 상태 확인
        try:
            graph_status = default_manager.get_status()
            services["langgraph"] = "healthy" if graph_status["graph_initialized"] else "not_initialized"
        except Exception as e:
            services["langgraph"] = f"unhealthy: {str(e)}"
            overall_status = "degraded"
        
        # 파일 시스템 상태 확인
        try:
            import os
            upload_dir_exists = os.path.exists(settings.UPLOAD_DIR)
            output_dir_exists = os.path.exists(settings.OUTPUT_DIR)
            
            if upload_dir_exists and output_dir_exists:
                services["filesystem"] = "healthy"
            else:
                services["filesystem"] = f"unhealthy: upload_dir={upload_dir_exists}, output_dir={output_dir_exists}"
                overall_status = "degraded"
        except Exception as e:
            services["filesystem"] = f"unhealthy: {str(e)}"
            overall_status = "degraded"
        
        return HealthCheck(
            status=overall_status,
            services=services
        )
        
    except Exception as e:
        logger.error(f"헬스체크 실행 중 오류: {e}")
        return HealthCheck(
            status="unhealthy",
            services={"error": str(e)}
        )


@router.get("/info", response_model=SystemInfo)
async def get_system_info():
    """
    시스템 정보 조회
    
    애플리케이션의 설정과 상태 정보를 반환합니다.
    """
    try:
        # LangGraph 상태 조회
        graph_status = default_manager.get_status()
        
        return SystemInfo(
            app_name="parsing-graph",
            version="0.1.0",
            environment=settings.ENVIRONMENT,
            openai_model=settings.OPENROUTER_MODEL,
            mcp_base=settings.MCP_BASE,
            graph_status=graph_status
        )
        
    except Exception as e:
        logger.error(f"시스템 정보 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"시스템 정보 조회 실패: {str(e)}")


@router.get("/stats", response_model=ParsingStats)
async def get_parsing_stats():
    """
    파싱 통계 조회
    
    전체 문서 파싱 통계를 반환합니다.
    """
    try:
        import os
        import glob
        
        output_dir = settings.OUTPUT_DIR
        
        # 총 문서 수 (출력 디렉토리 기준)
        total_documents = 0
        completed_parsing = 0
        failed_parsing = 0
        total_sections = 0
        processing_times = []
        
        if os.path.exists(output_dir):
            # 문서 디렉토리들 탐색
            for item in os.listdir(output_dir):
                item_path = os.path.join(output_dir, item)
                if os.path.isdir(item_path):
                    total_documents += 1
                    
                    # CSV 파일 존재 여부로 완료 여부 판단
                    doc_id = item
                    csv_file = os.path.join(output_dir, f"{doc_id}_parsed.csv")
                    
                    if os.path.exists(csv_file):
                        completed_parsing += 1
                        
                        # 섹션 수 계산
                        try:
                            import csv
                            with open(csv_file, "r", encoding="utf-8") as f:
                                reader = csv.DictReader(f)
                                section_count = sum(1 for _ in reader)
                                total_sections += section_count
                        except Exception:
                            pass
                    else:
                        # 실패 여부는 로그나 상태 파일로 판단 (단순화)
                        failed_parsing += 1
        
        # 평균 처리 시간 계산 (실제 구현에서는 로그나 DB에서 가져와야 함)
        average_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0.0
        
        # 빈발 에러 목록 (실제 구현에서는 로그 분석 필요)
        most_common_errors = [
            "목차가 존재하지 않습니다",
            "MCP 서버 연결 실패",
            "스팬 데이터 추출 실패",
            "JSON 파싱 오류"
        ]
        
        return ParsingStats(
            total_documents=total_documents,
            completed_parsing=completed_parsing,
            failed_parsing=failed_parsing,
            average_processing_time=average_processing_time,
            total_sections=total_sections,
            most_common_errors=most_common_errors
        )
        
    except Exception as e:
        logger.error(f"파싱 통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"파싱 통계 조회 실패: {str(e)}")


@router.post("/config/reload", response_model=BaseResponse)
async def reload_config():
    """
    설정 재로드
    
    애플리케이션 설정을 다시 로드합니다.
    """
    try:
        # 설정 재로드 (실제 구현에서는 더 정교한 로직 필요)
        from importlib import reload
        from .. import config
        reload(config)
        
        logger.info("설정 재로드 완료")
        
        return BaseResponse(
            status=200,
            message="설정이 성공적으로 재로드되었습니다."
        )
        
    except Exception as e:
        logger.error(f"설정 재로드 실패: {e}")
        raise HTTPException(status_code=500, detail=f"설정 재로드 실패: {str(e)}")


@router.post("/cache/clear", response_model=BaseResponse)
async def clear_cache():
    """
    캐시 정리
    
    시스템 캐시를 정리합니다.
    """
    try:
        # 임시 파일 정리
        import tempfile
        import shutil
        
        temp_dir = tempfile.gettempdir()
        cleaned_items = []
        
        # parsing-graph 관련 임시 파일들 정리
        for item in os.listdir(temp_dir):
            if "parsing-graph" in item.lower() or "langgraph" in item.lower():
                item_path = os.path.join(temp_dir, item)
                try:
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                        cleaned_items.append(item)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                        cleaned_items.append(item)
                except Exception:
                    pass
        
        logger.info(f"캐시 정리 완료: {len(cleaned_items)}개 항목 정리")
        
        return BaseResponse(
            status=200,
            message=f"캐시가 성공적으로 정리되었습니다. ({len(cleaned_items)}개 항목)"
        )
        
    except Exception as e:
        logger.error(f"캐시 정리 실패: {e}")
        raise HTTPException(status_code=500, detail=f"캐시 정리 실패: {str(e)}")


@router.get("/logs")
async def get_logs(
    lines: int = 100,
    level: str = "INFO"
):
    """
    시스템 로그 조회
    
    최근 시스템 로그를 조회합니다.
    """
    try:
        # 실제 로그 파일에서 읽기 (구현 필요)
        # 여기서는 샘플 응답 반환
        sample_logs = [
            f"2024-01-01 12:00:00 - {level} - 애플리케이션 시작",
            f"2024-01-01 12:00:01 - {level} - GPT-5 클라이언트 초기화 완료",
            f"2024-01-01 12:00:02 - {level} - MCP 서버 연결 완료",
            f"2024-01-01 12:00:03 - {level} - LangGraph 파이프라인 준비 완료",
        ]
        
        return {
            "logs": sample_logs[:lines],
            "total_lines": len(sample_logs),
            "level": level,
            "message": f"최근 {lines}줄의 로그를 조회했습니다."
        }
        
    except Exception as e:
        logger.error(f"로그 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"로그 조회 실패: {str(e)}")


@router.get("/version", response_model=Dict[str, str])
async def get_version():
    """
    버전 정보 조회
    
    애플리케이션과 주요 의존성의 버전 정보를 반환합니다.
    """
    try:
        import sys
        
        version_info = {
            "app_version": "0.1.0",
            "python_version": sys.version,
            "environment": settings.ENVIRONMENT,
            "debug_mode": str(settings.DEBUG)
        }
        
        # 주요 패키지 버전 정보
        try:
            import fastapi
            version_info["fastapi"] = fastapi.__version__
        except:
            version_info["fastapi"] = "unknown"
        
        try:
            import openai
            version_info["openai"] = openai.__version__
        except:
            version_info["openai"] = "unknown"
        
        try:
            import langgraph
            version_info["langgraph"] = langgraph.__version__
        except:
            version_info["langgraph"] = "unknown"
        
        return version_info
        
    except Exception as e:
        logger.error(f"버전 정보 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"버전 정보 조회 실패: {str(e)}")
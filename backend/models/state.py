"""
LangGraph 상태 정의
"""
from typing import TypedDict, List, Dict, Optional, Any


class ParserState(TypedDict, total=False):
    """
    LangGraph 파이프라인 전역 상태
    
    보험약관 PDF 파싱 워크플로우의 모든 단계에서 공유되는 상태 정보
    """
    # 입력/메타 정보
    doc_id: str                   # 문서 ID
    total_pages: int              # 전체 페이지 수
    window_size: int              # 목차 탐지 윈도우 크기 (기본 5페이지)
    window_start: int             # 현재 윈도우 시작 인덱스 (0-based)

    # 탐지/파싱 산출물
    toc_pages: List[int]          # AI가 식별한 목차 페이지 리스트 (0-based)
    spans: List[Dict[str, Any]]   # PyMuPDF 스팬 레벨 파싱 결과
    toc_parsed: Dict[str, Any]    # LLM 목차 파싱 결과 (JSON)
    sections: List[Dict[str, Any]]# page_end 계산 및 본문 추출 메타 포함 최종 섹션

    # 산출 파일
    csv_path: Optional[str]       # 생성된 CSV 파일 경로

    # 로깅/상태 관리
    job_status: str               # 작업 상태: idle | running | detected | parsed | extracted | completed | failed
    logs: List[str]               # 처리 로그 목록
    error: Optional[str]          # 에러 메시지 (실패 시)

    # 추가 메타데이터
    created_at: Optional[str]     # 작업 시작 시간
    updated_at: Optional[str]     # 마지막 업데이트 시간
    processing_time: Optional[float]  # 총 처리 시간 (초)


# 작업 상태 열거형
class JobStatus:
    """작업 상태 상수"""
    IDLE = "idle"                 # 대기 중
    RUNNING = "running"           # 실행 중
    DETECTING = "detecting"       # 목차 탐지 중
    DETECTED = "detected"         # 목차 탐지 완료
    PARSING = "parsing"           # 목차 파싱 중
    PARSED = "parsed"             # 목차 파싱 완료
    EXTRACTING = "extracting"     # 본문 추출 중
    EXTRACTED = "extracted"       # 본문 추출 완료
    SAVING = "saving"            # 파일 저장 중
    COMPLETED = "completed"       # 완료
    FAILED = "failed"            # 실패


def create_initial_state(doc_id: str, window_size: int = 5) -> ParserState:
    """
    초기 상태 생성
    
    Args:
        doc_id: 문서 ID
        window_size: 윈도우 크기
        
    Returns:
        초기화된 ParserState
    """
    from datetime import datetime
    
    return ParserState(
        doc_id=doc_id,
        window_size=window_size,
        window_start=0,
        toc_pages=[],
        logs=[],
        job_status=JobStatus.IDLE,
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
    )


def update_state_status(state: ParserState, status: str, log_message: str = "") -> ParserState:
    """
    상태 업데이트 헬퍼 함수
    
    Args:
        state: 현재 상태
        status: 새로운 상태
        log_message: 로그 메시지
        
    Returns:
        업데이트된 상태
    """
    from datetime import datetime
    
    state["job_status"] = status
    state["updated_at"] = datetime.utcnow().isoformat()
    
    if log_message:
        state.setdefault("logs", []).append(f"[{status}] {log_message}")
    
    return state


def add_log(state: ParserState, message: str, level: str = "INFO") -> ParserState:
    """
    로그 추가
    
    Args:
        state: 현재 상태
        message: 로그 메시지  
        level: 로그 레벨
        
    Returns:
        로그가 추가된 상태
    """
    from datetime import datetime
    
    timestamp = datetime.utcnow().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {level}: {message}"
    
    state.setdefault("logs", []).append(log_entry)
    state["updated_at"] = datetime.utcnow().isoformat()
    
    return state


def set_error(state: ParserState, error_message: str) -> ParserState:
    """
    에러 설정
    
    Args:
        state: 현재 상태
        error_message: 에러 메시지
        
    Returns:
        에러가 설정된 상태
    """
    state["error"] = error_message
    state["job_status"] = JobStatus.FAILED
    
    return add_log(state, f"ERROR: {error_message}", "ERROR")
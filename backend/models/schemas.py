"""
API 요청/응답 스키마 정의
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# 기본 응답 스키마
class BaseResponse(BaseModel):
    """기본 API 응답"""
    status: int = Field(..., description="HTTP 상태 코드")
    message: str = Field(..., description="응답 메시지")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="응답 시간")


class ErrorResponse(BaseResponse):
    """에러 응답"""
    error: str = Field(..., description="에러 상세 정보")
    status: int = Field(default=500)


# 파싱 관련 스키마
class ParseRequest(BaseModel):
    """파싱 요청"""
    doc_id: str = Field(..., description="문서 ID", min_length=1)
    window_size: Optional[int] = Field(default=5, description="목차 탐지 윈도우 크기", ge=1, le=20)
    use_checkpointer: Optional[bool] = Field(default=False, description="SQLite 체크포인터 사용 여부")


class SectionInfo(BaseModel):
    """섹션 정보"""
    section_id: int = Field(..., description="섹션 ID")
    level_1: Optional[str] = Field(None, description="1단계 제목")
    level_2: Optional[str] = Field(None, description="2단계 제목") 
    level_3: Optional[str] = Field(None, description="3단계 제목")
    kwan: Optional[str] = Field(None, description="관 정보")
    jo: Optional[str] = Field(None, description="조 정보")
    page_start: int = Field(..., description="시작 페이지", ge=0)
    page_end: int = Field(..., description="종료 페이지", ge=0)
    title: str = Field(..., description="섹션 제목")
    para_count: int = Field(default=0, description="문단 수", ge=0)
    char_count: int = Field(default=0, description="문자 수", ge=0)
    has_table: bool = Field(default=False, description="표 포함 여부")
    has_figure: bool = Field(default=False, description="그림 포함 여부")
    extract_path: Optional[str] = Field(None, description="텍스트 파일 경로")
    json_path: Optional[str] = Field(None, description="JSON 파일 경로")


class ParseProgress(BaseModel):
    """파싱 진행 상태"""
    doc_id: str = Field(..., description="문서 ID")
    job_status: str = Field(..., description="작업 상태")
    progress_percent: float = Field(default=0.0, description="진행률 (%)", ge=0.0, le=100.0)
    current_step: str = Field(default="", description="현재 단계")
    logs: List[str] = Field(default_factory=list, description="처리 로그")
    error: Optional[str] = Field(None, description="에러 메시지")
    created_at: Optional[datetime] = Field(None, description="시작 시간")
    updated_at: Optional[datetime] = Field(None, description="업데이트 시간")


class ParseResult(BaseResponse):
    """파싱 결과"""
    doc_id: str = Field(..., description="문서 ID")
    total_pages: int = Field(..., description="총 페이지 수", ge=0)
    toc_pages: List[int] = Field(default_factory=list, description="목차 페이지 목록")
    section_count: int = Field(default=0, description="섹션 수", ge=0)
    csv_path: Optional[str] = Field(None, description="생성된 CSV 파일 경로")
    processing_time: Optional[float] = Field(None, description="처리 시간 (초)")
    sections: List[SectionInfo] = Field(default_factory=list, description="섹션 목록")
    status: int = Field(default=200)
    message: str = Field(default="파싱 완료")


class ParseFailure(BaseResponse):
    """파싱 실패"""
    doc_id: str = Field(..., description="문서 ID") 
    reason: str = Field(..., description="실패 사유")
    logs: List[str] = Field(default_factory=list, description="처리 로그")
    status: int = Field(default=500)
    message: str = Field(default="파싱 실패")


# 문서 관리 스키마
class DocumentInfo(BaseModel):
    """문서 정보"""
    doc_id: str = Field(..., description="문서 ID")
    filename: Optional[str] = Field(None, description="파일명")
    page_count: int = Field(..., description="페이지 수", ge=0)
    file_size: Optional[int] = Field(None, description="파일 크기 (bytes)")
    upload_date: Optional[datetime] = Field(None, description="업로드 날짜")
    status: str = Field(default="uploaded", description="문서 상태")


class DocumentList(BaseResponse):
    """문서 목록"""
    documents: List[DocumentInfo] = Field(default_factory=list, description="문서 목록")
    total: int = Field(default=0, description="총 문서 수", ge=0)
    status: int = Field(default=200)
    message: str = Field(default="문서 목록 조회 성공")


class SectionDetail(BaseModel):
    """섹션 상세 정보"""
    section_info: SectionInfo = Field(..., description="섹션 기본 정보")
    content: str = Field(default="", description="섹션 본문")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="추가 메타데이터")


class SectionsList(BaseResponse):
    """섹션 목록"""
    doc_id: str = Field(..., description="문서 ID")
    sections: List[SectionInfo] = Field(default_factory=list, description="섹션 목록")
    total: int = Field(default=0, description="총 섹션 수", ge=0)
    status: int = Field(default=200)
    message: str = Field(default="섹션 목록 조회 성공")


# 시스템 관리 스키마
class HealthCheck(BaseModel):
    """헬스체크"""
    status: str = Field(default="healthy", description="시스템 상태")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="체크 시간")
    services: Dict[str, str] = Field(default_factory=dict, description="서비스 상태")
    version: str = Field(default="0.1.0", description="애플리케이션 버전")


class SystemInfo(BaseModel):
    """시스템 정보"""
    app_name: str = Field(default="parsing-graph", description="애플리케이션 이름")
    version: str = Field(default="0.1.0", description="버전")
    environment: str = Field(default="development", description="환경")
    openai_model: str = Field(..., description="사용 중인 OpenAI 모델")
    mcp_base: str = Field(..., description="MCP 서버 주소")
    graph_status: Dict[str, Any] = Field(default_factory=dict, description="그래프 상태")


class JobStatusUpdate(BaseModel):
    """작업 상태 업데이트"""
    doc_id: str = Field(..., description="문서 ID")
    status: str = Field(..., description="새로운 상태")
    message: Optional[str] = Field(None, description="상태 메시지")
    logs: Optional[List[str]] = Field(None, description="로그 추가")


# 검색 및 필터 스키마
class SearchQuery(BaseModel):
    """검색 쿼리"""
    query: str = Field(..., description="검색어", min_length=1)
    doc_id: Optional[str] = Field(None, description="특정 문서 ID로 제한")
    section_type: Optional[str] = Field(None, description="섹션 타입 필터")
    page_range: Optional[List[int]] = Field(None, description="페이지 범위 [start, end]")


class SearchResult(BaseModel):
    """검색 결과"""
    doc_id: str = Field(..., description="문서 ID")
    section_id: int = Field(..., description="섹션 ID")
    title: str = Field(..., description="섹션 제목")
    snippet: str = Field(..., description="검색 결과 스니펫")
    page_start: int = Field(..., description="시작 페이지")
    relevance_score: float = Field(..., description="관련도 점수", ge=0.0, le=1.0)


class SearchResponse(BaseResponse):
    """검색 응답"""
    query: str = Field(..., description="검색어")
    results: List[SearchResult] = Field(default_factory=list, description="검색 결과")
    total: int = Field(default=0, description="총 결과 수", ge=0)
    status: int = Field(default=200)
    message: str = Field(default="검색 완료")


# 통계 스키마
class ParsingStats(BaseModel):
    """파싱 통계"""
    total_documents: int = Field(default=0, description="총 문서 수")
    completed_parsing: int = Field(default=0, description="파싱 완료 문서 수")
    failed_parsing: int = Field(default=0, description="파싱 실패 문서 수")
    average_processing_time: float = Field(default=0.0, description="평균 처리 시간 (초)")
    total_sections: int = Field(default=0, description="총 섹션 수")
    most_common_errors: List[str] = Field(default_factory=list, description="빈발 에러 목록")


# 파일 업로드 스키마
class UploadResponse(BaseResponse):
    """파일 업로드 응답"""
    doc_id: str = Field(..., description="생성된 문서 ID")
    filename: str = Field(..., description="업로드된 파일명")
    file_size: int = Field(..., description="파일 크기 (bytes)")
    page_count: Optional[int] = Field(None, description="페이지 수")
    status: int = Field(default=201)
    message: str = Field(default="파일 업로드 성공")
"""
LangGraph 기반 PDF 파싱 그래프 구성
"""
import logging
from typing import Dict, Any, AsyncGenerator
from langgraph.graph import StateGraph

# 선택적 체크포인터 import
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
    CHECKPOINT_AVAILABLE = True
except ImportError:
    SqliteSaver = None
    CHECKPOINT_AVAILABLE = False

from ..models.state import ParserState, JobStatus, create_initial_state
from .nodes import (
    node_doc_info,
    node_detect_toc_window,
    node_extract_spans,
    node_llm_parse_toc,
    node_calc_page_end,
    node_extract_ranges,
    node_write_csv,
    node_fail
)

logger = logging.getLogger(__name__)


def cond_after_detect(state: ParserState) -> str:
    """
    목차 탐지 후 조건부 분기
    
    Args:
        state: 현재 상태
        
    Returns:
        다음 노드명 ("continue" | "next" | "no_toc")
    """
    total_pages = state.get("total_pages", 0)
    current_cursor = state.get("window_start", 0)
    
    # 아직 더 탐지할 페이지가 있는가?
    if current_cursor < total_pages:
        return "continue"  # 목차 탐지 루프 계속
    
    # 탐지 완료 - 목차 페이지가 발견되었는가?
    toc_pages = state.get("toc_pages", [])
    if toc_pages:
        return "next"      # 스팬 추출로 진행
    else:
        return "no_toc"    # 목차 없음 - 실패 처리


def cond_after_parse(state: ParserState) -> str:
    """
    목차 파싱 후 조건부 분기
    
    Args:
        state: 현재 상태
        
    Returns:
        다음 노드명 ("success" | "fail")
    """
    toc_parsed = state.get("toc_parsed", {})
    status = toc_parsed.get("status", 500)
    parsed_items = toc_parsed.get("parsed", [])
    
    if status == 200 and parsed_items:
        return "success"   # page_end 계산으로 진행
    else:
        return "fail"      # 파싱 실패


def create_parser_graph(use_checkpointer: bool = False) -> StateGraph:
    """
    PDF 파싱 그래프 생성
    
    Args:
        use_checkpointer: SQLite 체크포인터 사용 여부
        
    Returns:
        컴파일된 LangGraph
    """
    logger.info("PDF 파싱 그래프 생성 시작")
    
    # StateGraph 초기화
    graph = StateGraph(ParserState)
    
    # 노드 추가
    graph.add_node("doc_info", node_doc_info)
    graph.add_node("detect_toc", node_detect_toc_window)
    graph.add_node("extract_spans", node_extract_spans)
    graph.add_node("llm_toc", node_llm_parse_toc)
    graph.add_node("calc_end", node_calc_page_end)
    graph.add_node("extract_ranges", node_extract_ranges)
    graph.add_node("write_csv", node_write_csv)
    graph.add_node("fail", node_fail)
    
    # 시작점 설정
    graph.set_entry_point("doc_info")
    
    # 엣지 연결
    graph.add_edge("doc_info", "detect_toc")
    
    # 조건부 분기: 목차 탐지 루프
    graph.add_conditional_edges("detect_toc", cond_after_detect, {
        "continue": "detect_toc",      # 다음 윈도우 계속 탐지
        "next": "extract_spans",       # 탐지 완료 → 스팬 추출
        "no_toc": "fail",             # 목차 없음 → 실패
    })
    
    # 스팬 추출 후 목차 파싱
    graph.add_edge("extract_spans", "llm_toc")
    
    # 조건부 분기: 목차 파싱 결과
    graph.add_conditional_edges("llm_toc", cond_after_parse, {
        "success": "calc_end",         # 파싱 성공 → page_end 계산
        "fail": "fail",               # 파싱 실패
    })
    
    # 직선 흐름: page_end 계산 → 범위 추출 → CSV 저장
    graph.add_edge("calc_end", "extract_ranges")
    graph.add_edge("extract_ranges", "write_csv")
    
    # 종료 노드들
    graph.add_edge("write_csv", "__end__")
    graph.add_edge("fail", "__end__")
    
    # 체크포인터 설정 (선택사항)
    checkpointer = None
    if use_checkpointer and CHECKPOINT_AVAILABLE:
        try:
            # SQLite 체크포인터로 중간 상태 저장
            checkpointer = SqliteSaver.from_conn_string("checkpoints.db")
            logger.info("SQLite 체크포인터 활성화")
        except Exception as e:
            logger.warning(f"체크포인터 설정 실패 (무시): {e}")
    elif use_checkpointer and not CHECKPOINT_AVAILABLE:
        logger.warning("체크포인터를 요청했지만 langgraph.checkpoint.sqlite를 사용할 수 없습니다")
    
    # 그래프 컴파일
    app = graph.compile(checkpointer=checkpointer)
    
    logger.info("PDF 파싱 그래프 생성 완료")
    return app


async def run_parsing_flow(doc_id: str, **kwargs) -> ParserState:
    """
    PDF 파싱 플로우 실행
    
    Args:
        doc_id: 문서 ID
        **kwargs: 추가 설정 (window_size, use_checkpointer 등)
        
    Returns:
        최종 상태
    """
    try:
        logger.info(f"PDF 파싱 플로우 시작: {doc_id}")
        
        # 초기 상태 생성
        window_size = kwargs.get("window_size", 5)
        initial_state = create_initial_state(doc_id, window_size)
        
        # 그래프 생성
        use_checkpointer = kwargs.get("use_checkpointer", False)
        app = create_parser_graph(use_checkpointer)
        
        # 플로우 실행
        final_state = await app.ainvoke(initial_state)
        
        # 실행 시간 계산
        if "created_at" in final_state and "updated_at" in final_state:
            from datetime import datetime
            try:
                start = datetime.fromisoformat(final_state["created_at"])
                end = datetime.fromisoformat(final_state["updated_at"])
                processing_time = (end - start).total_seconds()
                final_state["processing_time"] = processing_time
            except Exception:
                pass
        
        logger.info(f"PDF 파싱 플로우 완료: {doc_id}, 상태={final_state.get('job_status')}")
        return final_state
        
    except Exception as e:
        logger.error(f"PDF 파싱 플로우 실패: {doc_id}, {e}")
        # 실패 상태 반환
        error_state = create_initial_state(doc_id)
        error_state["job_status"] = JobStatus.FAILED
        error_state["error"] = str(e)
        return error_state


async def run_parsing_flow_with_stream(doc_id: str, **kwargs) -> AsyncGenerator[ParserState, None]:
    """
    스트리밍 방식으로 PDF 파싱 플로우 실행
    
    Args:
        doc_id: 문서 ID
        **kwargs: 추가 설정
        
    Yields:
        중간 상태들
    """
    try:
        logger.info(f"스트리밍 PDF 파싱 플로우 시작: {doc_id}")
        
        # 초기 상태 생성
        window_size = kwargs.get("window_size", 5)
        initial_state = create_initial_state(doc_id, window_size)
        
        # 그래프 생성
        use_checkpointer = kwargs.get("use_checkpointer", False)
        app = create_parser_graph(use_checkpointer)
        
        # 스트리밍 실행
        async for state in app.astream(initial_state):
            yield state
            
    except Exception as e:
        logger.error(f"스트리밍 파싱 플로우 실패: {doc_id}, {e}")
        # 실패 상태 반환
        error_state = create_initial_state(doc_id)
        error_state["job_status"] = JobStatus.FAILED
        error_state["error"] = str(e)
        yield error_state


def get_graph_visualization() -> str:
    """
    그래프 시각화 정보 반환
    
    Returns:
        그래프 구조 설명
    """
    return """
    PDF 파싱 파이프라인 그래프:
    
    START → doc_info → detect_toc ⟲ (윈도우 탐지 루프)
                              ↓
                      extract_spans → llm_toc → calc_end → extract_ranges → write_csv → END
                              ↓                    ↓
                            fail ←──────────── fail
                              ↓
                            END
    
    조건부 분기:
    1. detect_toc 후: continue(루프) | next(진행) | no_toc(실패)
    2. llm_toc 후: success(진행) | fail(실패)
    """


class ParsingGraphManager:
    """PDF 파싱 그래프 매니저"""
    
    def __init__(self, use_checkpointer: bool = False):
        self.use_checkpointer = use_checkpointer
        self._graph = None
    
    @property
    def graph(self):
        """그래프 lazy 초기화"""
        if self._graph is None:
            self._graph = create_parser_graph(self.use_checkpointer)
        return self._graph
    
    async def parse_document(self, doc_id: str, **kwargs) -> ParserState:
        """문서 파싱 실행"""
        return await run_parsing_flow(doc_id, **kwargs)
    
    async def parse_document_stream(self, doc_id: str, **kwargs):
        """스트리밍 문서 파싱 실행"""
        async for state in run_parsing_flow_with_stream(doc_id, **kwargs):
            yield state
    
    def get_status(self) -> Dict[str, Any]:
        """매니저 상태 반환"""
        return {
            "checkpointer_enabled": self.use_checkpointer,
            "graph_initialized": self._graph is not None,
            "graph_visualization": get_graph_visualization()
        }


# 전역 매니저 인스턴스
default_manager = ParsingGraphManager()
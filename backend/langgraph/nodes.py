"""
LangGraph 노드 구현
"""
import json
import os
import csv
import logging
from typing import Dict, Any, List
from datetime import datetime

from ..models.state import ParserState, JobStatus, update_state_status, add_log, set_error
from ..clients.mcp_client import pdf_get_info, pdf_parse_layout_spans, pdf_read
from ..clients.openrouter_client import openrouter_chat as gpt5_chat
from ..prompts.insurance_prompts import (
    get_toc_detect_prompt,
    get_toc_parsing_prompt,
    SYSTEM_PROMPT
)
from ..config import settings

logger = logging.getLogger(__name__)


async def node_doc_info(state: ParserState) -> ParserState:
    """
    문서 정보 조회 노드
    
    MCP를 통해 PDF 문서의 기본 정보(총 페이지 수 등)를 조회합니다.
    """
    try:
        doc_id = state["doc_id"]
        logger.info(f"문서 정보 조회 시작: {doc_id}")
        
        # MCP로 문서 정보 조회
        info = await pdf_get_info(doc_id)
        total_pages = int(info.get("page_count", 0))
        
        if total_pages <= 0:
            return set_error(state, f"유효하지 않은 문서: 페이지 수 {total_pages}")
        
        # 상태 업데이트
        state["total_pages"] = total_pages
        state = update_state_status(state, JobStatus.RUNNING, f"문서 정보 조회 완료: {total_pages}페이지")
        
        logger.info(f"문서 정보 조회 성공: {doc_id}, {total_pages}페이지")
        return state
        
    except Exception as e:
        logger.error(f"문서 정보 조회 실패: {e}")
        return set_error(state, f"문서 정보 조회 실패: {str(e)}")


async def node_detect_toc_window(state: ParserState) -> ParserState:
    """
    5페이지 윈도우 기반 목차 탐지 노드
    
    현재 윈도우의 페이지들을 분석하여 목차 페이지를 탐지합니다.
    """
    try:
        ws = state.get("window_size", settings.WINDOW_SIZE)
        start = state.get("window_start", 0)
        total = state["total_pages"]
        end = min(start + ws, total)
        pages = list(range(start, end))
        
        logger.info(f"목차 탐지 시작: 윈도우 {start}-{end-1} ({len(pages)}페이지)")
        
        # 프롬프트 생성
        doc_info = {"doc_id": state["doc_id"]}
        prompt = get_toc_detect_prompt(doc_info, pages)
        
        # GPT-5로 목차 탐지
        result_str = gpt5_chat(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.0
        )
        
        # JSON 파싱
        try:
            result = json.loads(result_str)
        except json.JSONDecodeError as e:
            logger.error(f"목차 탐지 JSON 파싱 실패: {e}")
            return set_error(state, f"목차 탐지 응답 파싱 실패: {str(e)}")
        
        # 탐지된 목차 페이지 병합
        detected_pages = result.get("toc_pages", []) or []
        confidence = result.get("confidence", 0.0)
        reason = result.get("reason", "")
        
        # 기존 목차 페이지와 병합
        existing_pages = state.get("toc_pages", [])
        all_toc_pages = sorted(list(set(existing_pages + detected_pages)))
        state["toc_pages"] = all_toc_pages
        
        # 다음 윈도우로 이동
        state["window_start"] = end
        
        # 로그 기록
        log_msg = f"윈도우 {start}-{end-1} 탐지 완료: 발견={detected_pages}, 신뢰도={confidence:.2f}"
        state = add_log(state, log_msg)
        
        if detected_pages:
            state = add_log(state, f"탐지 근거: {reason}")
        
        logger.info(f"목차 탐지 완료: 총 {len(all_toc_pages)}페이지 발견")
        return state
        
    except Exception as e:
        logger.error(f"목차 탐지 실패: {e}")
        return set_error(state, f"목차 탐지 실패: {str(e)}")


async def node_extract_spans(state: ParserState) -> ParserState:
    """
    스팬 추출 노드
    
    AI가 선택한 목차 페이지에서 PyMuPDF 스팬 레벨 데이터를 추출합니다.
    """
    try:
        doc_id = state["doc_id"]
        pages = state.get("toc_pages", [])
        
        if not pages:
            return set_error(state, "목차 페이지가 발견되지 않음")
        
        logger.info(f"스팬 추출 시작: {len(pages)}페이지")
        
        # MCP로 스팬 데이터 추출
        result = await pdf_parse_layout_spans(doc_id, pages)
        spans = result.get("spans", [])
        
        if not spans:
            return set_error(state, "스팬 데이터 추출 실패")
        
        # 상태 업데이트
        state["spans"] = spans
        state = update_state_status(
            state, 
            JobStatus.DETECTED, 
            f"스팬 추출 완료: {len(spans)}개 스팬, 페이지 {pages}"
        )
        
        logger.info(f"스팬 추출 성공: {len(spans)}개 스팬")
        return state
        
    except Exception as e:
        logger.error(f"스팬 추출 실패: {e}")
        return set_error(state, f"스팬 추출 실패: {str(e)}")


async def node_llm_parse_toc(state: ParserState) -> ParserState:
    """
    LLM 목차 파싱 노드
    
    추출된 스팬 데이터를 LLM으로 파싱하여 구조화된 목차를 생성합니다.
    """
    try:
        spans = state.get("spans", [])
        
        if not spans:
            return set_error(state, "파싱할 스팬 데이터가 없음")
        
        logger.info(f"목차 파싱 시작: {len(spans)}개 스팬")
        
        # 스팬 데이터 정렬 및 정제
        spans_sorted = sorted(spans, key=lambda s: (
            s.get("page", 0), 
            s.get("line_id", 0), 
            s.get("span_id", 0)
        ))
        
        # 스팬을 텍스트 블록으로 변환
        blocks = []
        for span in spans_sorted:
            text = (span.get("text") or "").strip()
            if not text or len(text) < 2:
                continue
                
            font_name = span.get("font_name", "Unknown")
            font_size = span.get("font_size", 0)
            bold = span.get("bold", False)
            page = span.get("page", 0)
            line_id = span.get("line_id", 0)
            
            block = f"페이지 {page+1}, 라인 {line_id+1}: {text} [{font_name}, {font_size}pt{'_Bold' if bold else ''}]"
            blocks.append(block)
        
        if not blocks:
            return set_error(state, "유효한 텍스트 블록이 없음")
        
        # 목차 파싱 프롬프트 생성
        prompt = get_toc_parsing_prompt(blocks)
        
        # GPT-5로 목차 파싱
        result_str = gpt5_chat(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.0
        )
        
        # JSON 파싱
        try:
            result = json.loads(result_str)
        except json.JSONDecodeError as e:
            logger.error(f"목차 파싱 JSON 파싱 실패: {e}")
            return set_error(state, f"목차 파싱 응답 파싱 실패: {str(e)}")
        
        # 파싱 결과 검증
        status = result.get("status", 500)
        parsed_items = result.get("parsed", [])
        
        if status != 200 or not parsed_items:
            error_msg = result.get("message", "목차 파싱 실패")
            return set_error(state, error_msg)
        
        # 상태 업데이트
        state["toc_parsed"] = result
        state = update_state_status(
            state, 
            JobStatus.PARSED, 
            f"목차 파싱 완료: {len(parsed_items)}개 항목"
        )
        
        logger.info(f"목차 파싱 성공: {len(parsed_items)}개 항목")
        return state
        
    except Exception as e:
        logger.error(f"목차 파싱 실패: {e}")
        return set_error(state, f"목차 파싱 실패: {str(e)}")


async def node_calc_page_end(state: ParserState) -> ParserState:
    """
    page_end 자동 계산 노드
    
    LLM이 0으로 설정한 page_end를 다음 섹션의 page_start-1로 자동 계산합니다.
    """
    try:
        toc_data = state.get("toc_parsed", {})
        items = toc_data.get("parsed", [])
        
        if not items:
            return set_error(state, "계산할 목차 데이터가 없음")
        
        logger.info(f"page_end 계산 시작: {len(items)}개 항목")
        
        # page_start 기준으로 정렬
        items_sorted = sorted(items, key=lambda x: int(x.get("page_start", 0)))
        
        total_pages = state.get("total_pages", 0)
        
        # page_end 계산
        for i in range(len(items_sorted)):
            if i + 1 < len(items_sorted):
                # 다음 항목의 page_start - 1
                next_start = int(items_sorted[i + 1].get("page_start", 0))
                items_sorted[i]["page_end"] = max(0, next_start - 1)
            else:
                # 마지막 항목은 문서 끝까지
                items_sorted[i]["page_end"] = max(0, total_pages - 1)
        
        # 결과 업데이트
        toc_data["parsed"] = items_sorted
        state["toc_parsed"] = toc_data
        
        state = add_log(state, "page_end 자동 계산 완료")
        
        logger.info(f"page_end 계산 완료")
        return state
        
    except Exception as e:
        logger.error(f"page_end 계산 실패: {e}")
        return set_error(state, f"page_end 계산 실패: {str(e)}")


async def node_extract_ranges(state: ParserState) -> ParserState:
    """
    범위 기반 본문 추출 노드
    
    계산된 page_start~page_end 범위에서 본문을 추출하고 메타데이터를 생성합니다.
    """
    try:
        doc_id = state["doc_id"]
        parsed_items = state.get("toc_parsed", {}).get("parsed", [])
        
        if not parsed_items:
            return set_error(state, "추출할 섹션 데이터가 없음")
        
        logger.info(f"범위 추출 시작: {len(parsed_items)}개 섹션")
        
        sections = []
        
        for i, item in enumerate(parsed_items, 1):
            try:
                start_page = int(item.get("page_start", 0))
                end_page = int(item.get("page_end", start_page))
                pages = list(range(start_page, end_page + 1)) if end_page >= start_page else [start_page]
                
                # MCP로 본문 추출
                content_result = await pdf_read(doc_id, pages, mode="plain")
                full_content = content_result.get("plain", "")
                
                # 제목 우선순위: jo > kwan > level_3 > level_2 > level_1
                title = (
                    item.get("jo") or 
                    item.get("kwan") or 
                    item.get("level_3") or 
                    item.get("level_2") or 
                    item.get("level_1") or 
                    f"섹션 {i}"
                )
                
                # 제목 이후 본문 추출
                pure_content = extract_content_after_title(full_content, title)
                
                # 메타데이터 생성
                meta = {
                    "text": pure_content,
                    "para_count": pure_content.count("\n\n") + 1 if pure_content.strip() else 0,
                    "char_count": len(pure_content.strip()),
                    "has_table": ("표" in pure_content) or ("Table" in pure_content),
                    "has_figure": ("그림" in pure_content) or ("Figure" in pure_content) or ("도" in pure_content),
                    "pages": pages,
                    "title": title,
                    "section_id": i
                }
                
                # 원본 데이터와 메타데이터 병합
                section = {**item, **meta}
                sections.append(section)
                
                logger.debug(f"섹션 {i} 추출 완료: {len(pure_content)}자")
                
            except Exception as e:
                logger.error(f"섹션 {i} 추출 실패: {e}")
                # 실패한 섹션도 기본 정보로 추가
                sections.append({
                    **item,
                    "text": "",
                    "title": f"섹션 {i} (추출 실패)",
                    "error": str(e)
                })
        
        # 상태 업데이트
        state["sections"] = sections
        state = update_state_status(
            state, 
            JobStatus.EXTRACTED, 
            f"본문 추출 완료: {len(sections)}개 섹션"
        )
        
        logger.info(f"범위 추출 성공: {len(sections)}개 섹션")
        return state
        
    except Exception as e:
        logger.error(f"범위 추출 실패: {e}")
        return set_error(state, f"범위 추출 실패: {str(e)}")


async def node_write_csv(state: ParserState) -> ParserState:
    """
    CSV 저장 노드
    
    추출된 섹션 데이터를 CSV 파일로 저장하고 개별 텍스트/JSON 파일도 생성합니다.
    """
    try:
        doc_id = state["doc_id"]
        sections = state.get("sections", [])
        
        if not sections:
            return set_error(state, "저장할 섹션 데이터가 없음")
        
        logger.info(f"CSV 저장 시작: {len(sections)}개 섹션")
        
        # 출력 디렉토리 생성
        base_dir = os.path.join(settings.OUTPUT_DIR, doc_id)
        os.makedirs(base_dir, exist_ok=True)
        
        # CSV 헤더
        headers = [
            "doc_id", "section_id", "level_1", "level_2", "level_3", "kwan", "jo",
            "page_start", "page_end", "title", "para_count", "char_count",
            "has_table", "has_figure", "extract_path", "json_path"
        ]
        
        rows = []
        
        # 각 섹션 처리
        for section in sections:
            section_id = section.get("section_id", 0)
            
            # 텍스트 및 JSON 파일 경로
            extract_path = os.path.join(base_dir, f"section_{section_id}.txt")
            json_path = os.path.join(base_dir, f"section_{section_id}.json")
            
            # 텍스트 파일 저장
            with open(extract_path, "w", encoding="utf-8") as f:
                f.write(section.get("text", ""))
            
            # JSON 파일 저장 (메타데이터 포함)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(section, f, ensure_ascii=False, indent=2)
            
            # CSV 행 데이터
            rows.append([
                doc_id,
                section_id,
                section.get("level_1", ""),
                section.get("level_2", ""),
                section.get("level_3", ""),
                section.get("kwan", ""),
                section.get("jo", ""),
                int(section.get("page_start", 0)),
                int(section.get("page_end", 0)),
                section.get("title", ""),
                int(section.get("para_count", 0)),
                int(section.get("char_count", 0)),
                bool(section.get("has_table", False)),
                bool(section.get("has_figure", False)),
                os.path.relpath(extract_path, settings.OUTPUT_DIR),
                os.path.relpath(json_path, settings.OUTPUT_DIR)
            ])
        
        # CSV 파일 저장
        csv_path = os.path.join(settings.OUTPUT_DIR, f"{doc_id}_parsed.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
        
        # 상태 업데이트
        state["csv_path"] = csv_path
        state = update_state_status(
            state, 
            JobStatus.COMPLETED, 
            f"CSV 저장 완료: {csv_path}"
        )
        
        logger.info(f"CSV 저장 성공: {csv_path}")
        return state
        
    except Exception as e:
        logger.error(f"CSV 저장 실패: {e}")
        return set_error(state, f"CSV 저장 실패: {str(e)}")


async def node_fail(state: ParserState) -> ParserState:
    """
    실패 처리 노드
    
    파이프라인 실패 시 최종 상태를 설정합니다.
    """
    error_msg = state.get("error", "알 수 없는 오류")
    state = update_state_status(state, JobStatus.FAILED, f"파이프라인 실패: {error_msg}")
    
    logger.error(f"파이프라인 실패: {error_msg}")
    return state


def extract_content_after_title(full_content: str, title: str) -> str:
    """
    제목 이후의 본문 내용 추출
    
    Args:
        full_content: 전체 텍스트
        title: 섹션 제목
        
    Returns:
        제목 이후의 본문
    """
    if not title or not full_content:
        return full_content
    
    # 정확한 매칭 시도
    pos = full_content.find(title)
    if pos != -1:
        return full_content[pos + len(title):].strip()
    
    # fuzzy 매칭 fallback
    try:
        import difflib
        matcher = difflib.SequenceMatcher(None, title.lower(), full_content.lower())
        match = matcher.find_longest_match(0, len(title), 0, len(full_content))
        
        if match.size > max(3, int(len(title) * 0.8)):
            start_pos = match.b + match.size
            return full_content[start_pos:].strip()
    except Exception:
        pass
    
    return full_content
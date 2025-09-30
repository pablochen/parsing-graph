"""
문서 관리 관련 API 엔드포인트
"""
import logging
import os
import json
from typing import List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse

from ..models.schemas import (
    DocumentList, DocumentInfo, SectionsList, SectionDetail, 
    UploadResponse, BaseResponse
)
from ..clients.mcp_client import pdf_get_info
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/docs", tags=["문서관리"])


@router.get("/", response_model=DocumentList)
async def list_documents(
    skip: int = Query(0, ge=0, description="건너뛸 문서 수"),
    limit: int = Query(100, ge=1, le=1000, description="반환할 최대 문서 수")
):
    """
    문서 목록 조회
    
    업로드된 모든 문서의 목록을 페이징하여 반환합니다.
    """
    try:
        # 출력 디렉토리에서 문서 검색
        output_dir = settings.OUTPUT_DIR
        documents = []
        
        if os.path.exists(output_dir):
            for item in os.listdir(output_dir):
                item_path = os.path.join(output_dir, item)
                if os.path.isdir(item_path):
                    # 문서 ID 디렉토리 발견
                    doc_id = item
                    
                    # CSV 파일 존재 여부로 파싱 완료 확인
                    csv_file = os.path.join(output_dir, f"{doc_id}_parsed.csv")
                    status = "parsed" if os.path.exists(csv_file) else "uploaded"
                    
                    try:
                        # MCP로 문서 정보 조회
                        doc_info = await pdf_get_info(doc_id)
                        page_count = doc_info.get("page_count", 0)
                        file_size = doc_info.get("file_size")
                    except Exception:
                        # MCP 조회 실패 시 기본값
                        page_count = 0
                        file_size = None
                    
                    documents.append(DocumentInfo(
                        doc_id=doc_id,
                        filename=f"{doc_id}.pdf",
                        page_count=page_count,
                        file_size=file_size,
                        upload_date=None,  # TODO: 실제 업로드 날짜 추가
                        status=status
                    ))
        
        # 페이징 적용
        total = len(documents)
        paginated_docs = documents[skip:skip + limit]
        
        return DocumentList(
            documents=paginated_docs,
            total=total
        )
        
    except Exception as e:
        logger.error(f"문서 목록 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"문서 목록 조회 실패: {str(e)}")


@router.get("/{doc_id}", response_model=DocumentInfo)
async def get_document_info(doc_id: str):
    """
    특정 문서 정보 조회
    
    문서 ID로 해당 문서의 상세 정보를 조회합니다.
    """
    try:
        # MCP로 문서 정보 조회
        doc_info = await pdf_get_info(doc_id)
        
        # 파싱 상태 확인
        csv_file = os.path.join(settings.OUTPUT_DIR, f"{doc_id}_parsed.csv")
        status = "parsed" if os.path.exists(csv_file) else "uploaded"
        
        return DocumentInfo(
            doc_id=doc_id,
            filename=f"{doc_id}.pdf",
            page_count=doc_info.get("page_count", 0),
            file_size=doc_info.get("file_size"),
            upload_date=None,
            status=status
        )
        
    except Exception as e:
        logger.error(f"문서 정보 조회 실패: {doc_id}, {e}")
        raise HTTPException(status_code=404, detail=f"문서를 찾을 수 없습니다: {doc_id}")


@router.get("/{doc_id}/sections", response_model=SectionsList)
async def get_document_sections(doc_id: str):
    """
    문서 섹션 목록 조회
    
    파싱 완료된 문서의 모든 섹션 목록을 반환합니다.
    """
    try:
        # CSV 파일 확인
        csv_file = os.path.join(settings.OUTPUT_DIR, f"{doc_id}_parsed.csv")
        if not os.path.exists(csv_file):
            raise HTTPException(
                status_code=404, 
                detail=f"문서 {doc_id}는 아직 파싱되지 않았습니다."
            )
        
        # CSV 파일에서 섹션 정보 읽기
        import csv
        sections = []
        
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sections.append({
                    "section_id": int(row.get("section_id", 0)),
                    "level_1": row.get("level_1", ""),
                    "level_2": row.get("level_2", ""),
                    "level_3": row.get("level_3", ""),
                    "kwan": row.get("kwan", ""),
                    "jo": row.get("jo", ""),
                    "page_start": int(row.get("page_start", 0)),
                    "page_end": int(row.get("page_end", 0)),
                    "title": row.get("title", ""),
                    "para_count": int(row.get("para_count", 0)),
                    "char_count": int(row.get("char_count", 0)),
                    "has_table": row.get("has_table", "").lower() == "true",
                    "has_figure": row.get("has_figure", "").lower() == "true",
                    "extract_path": row.get("extract_path"),
                    "json_path": row.get("json_path")
                })
        
        return SectionsList(
            doc_id=doc_id,
            sections=sections,
            total=len(sections)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"섹션 목록 조회 실패: {doc_id}, {e}")
        raise HTTPException(status_code=500, detail=f"섹션 목록 조회 실패: {str(e)}")


@router.get("/{doc_id}/sections/{section_id}", response_model=SectionDetail)
async def get_section_detail(doc_id: str, section_id: int):
    """
    특정 섹션 상세 정보 조회
    
    문서의 특정 섹션의 본문과 메타데이터를 반환합니다.
    """
    try:
        # 섹션 JSON 파일 경로
        section_dir = os.path.join(settings.OUTPUT_DIR, doc_id)
        json_file = os.path.join(section_dir, f"section_{section_id}.json")
        text_file = os.path.join(section_dir, f"section_{section_id}.txt")
        
        if not os.path.exists(json_file):
            raise HTTPException(
                status_code=404,
                detail=f"섹션 {section_id}를 찾을 수 없습니다."
            )
        
        # JSON 메타데이터 읽기
        with open(json_file, "r", encoding="utf-8") as f:
            section_data = json.load(f)
        
        # 텍스트 본문 읽기
        content = ""
        if os.path.exists(text_file):
            with open(text_file, "r", encoding="utf-8") as f:
                content = f.read()
        
        # 섹션 기본 정보 구성
        section_info = {
            "section_id": section_data.get("section_id", section_id),
            "level_1": section_data.get("level_1", ""),
            "level_2": section_data.get("level_2", ""),
            "level_3": section_data.get("level_3", ""),
            "kwan": section_data.get("kwan", ""),
            "jo": section_data.get("jo", ""),
            "page_start": section_data.get("page_start", 0),
            "page_end": section_data.get("page_end", 0),
            "title": section_data.get("title", ""),
            "para_count": section_data.get("para_count", 0),
            "char_count": section_data.get("char_count", 0),
            "has_table": section_data.get("has_table", False),
            "has_figure": section_data.get("has_figure", False),
            "extract_path": os.path.relpath(text_file, settings.OUTPUT_DIR),
            "json_path": os.path.relpath(json_file, settings.OUTPUT_DIR)
        }
        
        # 추가 메타데이터 (JSON 파일의 나머지 정보)
        metadata = {k: v for k, v in section_data.items() 
                   if k not in section_info}
        
        return SectionDetail(
            section_info=section_info,
            content=content,
            metadata=metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"섹션 상세 조회 실패: {doc_id}/{section_id}, {e}")
        raise HTTPException(status_code=500, detail=f"섹션 상세 조회 실패: {str(e)}")


@router.get("/{doc_id}/download/csv")
async def download_csv(doc_id: str):
    """
    파싱 결과 CSV 파일 다운로드
    
    문서의 파싱 결과를 CSV 파일로 다운로드합니다.
    """
    csv_file = os.path.join(settings.OUTPUT_DIR, f"{doc_id}_parsed.csv")
    
    if not os.path.exists(csv_file):
        raise HTTPException(
            status_code=404,
            detail=f"문서 {doc_id}의 CSV 파일을 찾을 수 없습니다."
        )
    
    return FileResponse(
        path=csv_file,
        filename=f"{doc_id}_parsed.csv",
        media_type="text/csv"
    )


@router.get("/{doc_id}/sections/{section_id}/download/text")
async def download_section_text(doc_id: str, section_id: int):
    """
    섹션 텍스트 파일 다운로드
    
    특정 섹션의 본문을 텍스트 파일로 다운로드합니다.
    """
    text_file = os.path.join(settings.OUTPUT_DIR, doc_id, f"section_{section_id}.txt")
    
    if not os.path.exists(text_file):
        raise HTTPException(
            status_code=404,
            detail=f"섹션 {section_id}의 텍스트 파일을 찾을 수 없습니다."
        )
    
    return FileResponse(
        path=text_file,
        filename=f"{doc_id}_section_{section_id}.txt",
        media_type="text/plain"
    )


@router.delete("/{doc_id}", response_model=BaseResponse)
async def delete_document(doc_id: str):
    """
    문서 삭제
    
    문서와 관련된 모든 파싱 결과를 삭제합니다.
    """
    try:
        import shutil
        
        # 문서 디렉토리 경로
        doc_dir = os.path.join(settings.OUTPUT_DIR, doc_id)
        csv_file = os.path.join(settings.OUTPUT_DIR, f"{doc_id}_parsed.csv")
        
        deleted_items = []
        
        # 문서 디렉토리 삭제
        if os.path.exists(doc_dir):
            shutil.rmtree(doc_dir)
            deleted_items.append(f"디렉토리: {doc_dir}")
        
        # CSV 파일 삭제
        if os.path.exists(csv_file):
            os.remove(csv_file)
            deleted_items.append(f"CSV 파일: {csv_file}")
        
        if not deleted_items:
            raise HTTPException(
                status_code=404,
                detail=f"문서 {doc_id}를 찾을 수 없습니다."
            )
        
        logger.info(f"문서 삭제 완료: {doc_id}, 삭제된 항목: {deleted_items}")
        
        return BaseResponse(
            status=200,
            message=f"문서 {doc_id}가 성공적으로 삭제되었습니다."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"문서 삭제 실패: {doc_id}, {e}")
        raise HTTPException(status_code=500, detail=f"문서 삭제 실패: {str(e)}")


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    PDF 파일 업로드
    
    새로운 PDF 문서를 업로드합니다.
    """
    try:
        # 파일 확장자 검증
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="PDF 파일만 업로드 가능합니다."
            )
        
        # 파일 크기 검증
        content = await file.read()
        if len(content) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"파일 크기가 너무 큽니다. 최대 {settings.MAX_FILE_SIZE // (1024*1024)}MB까지 가능합니다."
            )
        
        # 파일명에서 doc_id 생성 (확장자 제거)
        doc_id = os.path.splitext(file.filename)[0]
        
        # 업로드 디렉토리에 저장
        upload_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}.pdf")
        
        with open(upload_path, "wb") as f:
            f.write(content)
        
        # MCP로 문서 정보 확인 (페이지 수 등)
        try:
            doc_info = await pdf_get_info(doc_id)
            page_count = doc_info.get("page_count", 0)
        except Exception:
            page_count = None
        
        logger.info(f"파일 업로드 성공: {doc_id}, 크기: {len(content)}bytes")
        
        return UploadResponse(
            doc_id=doc_id,
            filename=file.filename,
            file_size=len(content),
            page_count=page_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 업로드 실패: {e}")
        raise HTTPException(status_code=500, detail=f"파일 업로드 실패: {str(e)}")
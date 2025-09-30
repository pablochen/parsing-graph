"""
보험약관 전용 AI 프롬프트 템플릿
"""
from typing import Dict, Any, List


# 목차 페이지 탐지 프롬프트 (5페이지 윈도우)
TOC_DETECT_PROMPT = """
다음 5페이지 내용을 분석하여 보험약관의 목차(Table of Contents)가 포함된 페이지들을 찾아주세요.

판단 기준:
1) 보험약관 구조 (가이드북, 주계약약관, 특별약관 등)
2) 계층적 제목 나열 (제X관, 제X조 등)
3) 페이지 번호가 함께 표시
4) 목차라는 명시적 표시 또는 차례, Contents 등의 표현
5) 들여쓰기된 계층 구조

반드시 아래 JSON 형식으로만 출력하세요:
{
    "toc_pages": [0기준_페이지_인덱스_정수_배열], 
    "confidence": 0.0~1.0_신뢰도,
    "reason": "판단근거_설명"
}

예시:
{
    "toc_pages": [2, 3], 
    "confidence": 0.95,
    "reason": "페이지 3-4에서 '제1관 보험계약의 성립', '제2관 보험금의 지급' 등 전형적인 보험약관 목차 구조와 페이지 번호 확인"
}
"""


# 보험약관 전용 목차 파싱 프롬프트  
INSURANCE_TOC_PARSING_PROMPT = """
### 역할
당신은 보험약관 PDF의 목차를 파싱하는 전문 어시스턴트입니다. 
입력된 스팬 텍스트 블록을 기반으로 목차 구조를 JSON으로 정리하세요.
추가 설명 없이 JSON만 출력합니다.

### 파싱 규칙 (핵심 요약)
1. **계층 구조**: level_1(최상위), level_2(중간), level_3(하위) 구분
2. **보험약관 구조**: kwan(제X관 전체문구), jo(제X조 전체문구) 추출
3. **페이지 정보**: 오른쪽 숫자는 page_start로 기록, page_end는 반드시 0으로 고정
4. **텍스트 정제**: 같은 줄의 다중 스팬은 병합하여 완전한 문장 복원
5. **레벨 판별**: 폰트 크기, 볼드 여부로 상위 레벨 판별 (볼드 우선)
6. **필수 조건**: 페이지 번호가 없는 항목은 제외
7. **최소 조건**: 1레벨만 있어도 페이지 정보가 있으면 기록

### 출력 형식 (성공)
{
  "status": 200,
  "message": "목차가 확인되었습니다.",
  "length": <항목수>,
  "parsed": [
    {
      "level_1": "상위레벨_제목",
      "level_2": "중간레벨_제목", 
      "level_3": "하위레벨_제목",
      "kwan": "제X관_전체문구",
      "jo": "제X조_전체문구",
      "page_start": <정수>,
      "page_end": 0
    }
  ]
}

### 출력 형식 (실패)
{"status": 404, "message": "목차가 존재하지 않습니다.", "length": 0, "parsed": []}
{"status": 500, "message": "목차 파싱에 실패했습니다.", "length": 0, "parsed": []}

### 스팬 입력 형식 이해
각 라인은 다음 형식입니다:
페이지 N, 라인 M: 텍스트내용 [폰트명, 크기pt_Bold여부]

예시 입력:
페이지 3, 라인 5: 제1관 보험계약의 성립과 유지 [Arial, 14pt_Bold]
페이지 3, 라인 6: 제1조 보험계약의 성립 [Arial, 12pt]
페이지 3, 라인 6: ........................... 15 [Arial, 12pt]

위 예시의 올바른 파싱:
{
  "status": 200,
  "message": "목차가 확인되었습니다.", 
  "length": 1,
  "parsed": [
    {
      "level_1": "제1관 보험계약의 성립과 유지",
      "level_2": "제1조 보험계약의 성립",
      "level_3": "",
      "kwan": "제1관 보험계약의 성립과 유지",
      "jo": "제1조 보험계약의 성립", 
      "page_start": 15,
      "page_end": 0
    }
  ]
}
"""


def get_toc_detect_prompt(doc_info: Dict[str, Any], window_pages: List[int]) -> str:
    """
    목차 탐지 프롬프트 생성
    
    Args:
        doc_info: 문서 정보 (doc_id, 메타데이터 등)
        window_pages: 현재 윈도우의 페이지 번호들
        
    Returns:
        완성된 프롬프트
    """
    context = f"""
문서 정보:
- 문서 ID: {doc_info.get('doc_id', 'Unknown')}
- 분석 페이지: {window_pages}
- 윈도우 크기: {len(window_pages)}페이지

{TOC_DETECT_PROMPT}
"""
    return context.strip()


def get_toc_parsing_prompt(spans_data: List[str]) -> str:
    """
    목차 파싱 프롬프트 생성
    
    Args:
        spans_data: 정제된 스팬 텍스트 블록 리스트
        
    Returns:
        완성된 프롬프트
    """
    spans_text = "\n".join(spans_data)
    
    prompt = f"""
{INSURANCE_TOC_PARSING_PROMPT}

### 분석할 스팬 데이터:
{spans_text}
"""
    return prompt.strip()


def get_content_analysis_prompt(content: str, title: str) -> str:
    """
    본문 분석 프롬프트 생성
    
    Args:
        content: 분석할 본문 내용
        title: 섹션 제목
        
    Returns:
        본문 분석 프롬프트
    """
    return f"""
다음 보험약관 섹션의 내용을 분석하여 주요 정보를 추출해주세요.

섹션 제목: {title}

분석 항목:
1. 주요 내용 요약
2. 중요 조항 식별
3. 표/그림 포함 여부
4. 참조 조항 정보
5. 특이사항

본문:
{content[:2000]}{'...(내용 생략)' if len(content) > 2000 else ''}

JSON 형식으로 응답:
{{
    "summary": "주요 내용 요약",
    "key_clauses": ["중요조항1", "중요조항2"],
    "has_table": true/false,
    "has_figure": true/false,  
    "references": ["관련조항1", "관련조항2"],
    "notes": "특이사항"
}}
"""


def get_validation_prompt(parsed_data: Dict[str, Any]) -> str:
    """
    파싱 결과 검증 프롬프트
    
    Args:
        parsed_data: 파싱된 목차 데이터
        
    Returns:
        검증 프롬프트
    """
    return f"""
다음 보험약관 목차 파싱 결과를 검증해주세요.

파싱 결과:
{parsed_data}

검증 항목:
1. 계층 구조의 논리적 일관성
2. 페이지 번호의 순차성
3. 보험약관 표준 구조 준수
4. 누락되거나 중복된 항목
5. 오타 또는 형식 오류

JSON 형식으로 응답:
{{
    "is_valid": true/false,
    "score": 0.0~1.0,
    "issues": ["문제점1", "문제점2"],
    "suggestions": ["개선사항1", "개선사항2"]
}}
"""


# 시스템 프롬프트
SYSTEM_PROMPT = """
당신은 보험약관 문서 처리 전문가입니다. OpenRouter를 통해 고품질 AI 모델을 활용하여 정확한 분석을 수행합니다.

핵심 원칙:
1. 정확성: 보험약관의 법적 구조를 정확히 인식
2. 일관성: 표준화된 형식으로 결과 제공
3. 완전성: 누락 없는 포괄적 분석
4. 신뢰성: 검증 가능한 근거 제시

항상 JSON 형식으로 구조화된 응답을 제공하며,
보험업계 표준과 법적 요구사항을 준수합니다.
"""
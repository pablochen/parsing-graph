# LangGraph 워크플로우 설계 - 보험약관 PDF 파싱 (GPT-5 전용)

본 문서는 사용자가 제공한 "보험약관 PDF 파싱 시스템 - AI 기반 완전 자동화" 요구사항을 **LangGraph 기반 상태 머신**으로 재설계하고, **GPT-5 전용 호출**, **PyMuPDF 스팬 레벨 처리**, **page_end 자동 계산**, **범위 기반 본문 추출**, **MCP 도구 연동**을 일관된 그래프 실행 흐름으로 구현한 참조 아키텍처 및 코드 예시를 제공합니다.

> ⚠️ **중요 원칙**
>
> * 모든 AI 호출은 **GPT-5** 또는 **GPT-5-mini**만 사용 (`openai/gpt-5`, `openai/gpt-5-mini`)
> * 휴리스틱 로직 제거, 100% AI 의사결정
> * PyMuPDF **스팬(span)** 단위 처리 유지
> * **page_end는 LLM 출력에서 0 고정** → 코드에서 자동 계산
> * **page_start~page_end 범위** 기반 본문 추출

---

## 0. 구성 개요

* **LangGraph State**: 파이프라인 전역 상태(문서 메타, 목차/스팬/섹션, 로그, 에러 등)
* **Nodes**: 기능 단위(문서정보조회, 목차탐지, 스팬추출, LLM 파싱, page_end 계산, 범위추출, CSV 저장, 완료)
* **Edges**: 조건 분기(재탐지 루프/성공/실패 경로)
* **Checkpointer(선택)**: 장시간 실행/재시작을 위한 SQLite 체크포인트
* **MCP**: `pdf.parse_layout_spans`, `pdf.get_info`, `pdf.read`, `fs.write_csv`

---

## 1. State 정의

```python
from typing import TypedDict, List, Dict, Optional, Any

class ParserState(TypedDict, total=False):
    # 입력/메타
    doc_id: str
    total_pages: int
    window_size: int              # 기본 5페이지 윈도우
    window_start: int             # 현재 윈도우 시작 인덱스(0-based)

    # 탐지/파싱 산출물
    toc_pages: List[int]          # AI가 식별한 목차 페이지(0-based)
    spans: List[Dict[str, Any]]   # PyMuPDF 스팬 리스트
    toc_parsed: Dict[str, Any]    # LLM 목차 파싱 결과(JSON)
    sections: List[Dict[str, Any]]# page_end 계산 및 본문 추출 메타 포함 최종 섹션

    # 산출 파일
    csv_path: Optional[str]

    # 로깅/상태관리
    job_status: str               # idle | running | detected | parsed | extracted | completed | failed
    logs: List[str]
    error: Optional[str]
```

초기 상태 예:

```python
init_state: ParserState = {
    "doc_id": "hanwha_personal_needai",
    "window_size": 5,
    "window_start": 0,
    "toc_pages": [],
    "logs": [],
    "job_status": "idle",
}
```

---

## 2. 공용 유틸/클라이언트

```python
import os, json, httpx
from typing import Dict, Any, List, Optional

# === OpenAI GPT-5 전용 래퍼 ===
from openai import OpenAI

ALLOWED_MODELS = {"gpt-5", "gpt-5-mini"}
DEFAULT_MODEL = os.getenv("GPT5_MODEL", "gpt-5-mini")
assert DEFAULT_MODEL in ALLOWED_MODELS, "모든 AI 호출은 gpt-5 / gpt-5-mini만 허용"

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def gpt5_chat(prompt: str, temperature: float = 0.0, model: str = DEFAULT_MODEL) -> str:
    assert model in ALLOWED_MODELS
    resp = openai_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return resp.choices[0].message.content or ""

# === MCP(JSON-RPC over HTTP) ===
MCP_BASE = os.getenv("MCP_BASE", "http://localhost:8001")

async def mcp_call(method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f"{MCP_BASE}/mcp", json={"method": method, "params": params})
        r.raise_for_status()
        return r.json()

# 동기 버전이 필요한 경우
def mcp_call_sync(method: str, params: Dict[str, Any]) -> Dict[str, Any]:
    with httpx.Client(timeout=120) as client:
        r = client.post(f"{MCP_BASE}/mcp", json={"method": method, "params": params})
        r.raise_for_status()
        return r.json()
```

---

## 3. 프롬프트(요구사항 반영)

### 3.1 목차 페이지 탐지 프롬프트 (5페이지 윈도우)

```python
TOC_DETECT_PROMPT = """
다음 5페이지 내용을 분석하여 보험약관의 목차(Table of Contents)가 포함된 페이지들을 찾아주세요.

판단 기준:
1) 보험약관 구조 (가이드북, 주계약약관, 특별약관 등)
2) 계층적 제목 나열 (제X관, 제X조 등)
3) 페이지 번호가 함께 표시

반드시 아래 JSON만 출력:
{"toc_pages": [0기준_페이지_인덱스_정수_배열], "confidence": 0~1, "reason": "판단근거"}
"""
```

### 3.2 보험약관 전용 목차 파싱 프롬프트

> **page_end는 항상 0**으로 반환해야 하며, 코드는 이후 자동 계산합니다.

```python
INSURANCE_TOC_PARSING_PROMPT = """
### 역할
당신은 보험약관 PDF의 목차를 파싱하는 전문 어시스턴트입니다. 
입력된 스팬 텍스트 블록을 기반으로 목차 구조를 JSON으로 정리하세요.
추가 설명 없이 JSON만 출력합니다.

### 파싱 규칙 (핵심 요약)
- level_1/2/3, kwan(제X관 ... 전체문구), jo(제X조 ... 전체문구)
- 오른쪽의 숫자는 page_start로 기록, page_end는 0으로 고정
- 같은 줄에 페이지 번호가 없으면 제외
- 같은 라인의 다중 스팬은 병합하여 완전한 문장 복원
- 폰트 크기/볼드로 상위 레벨 판별(볼드 우선)
- 1레벨만 있어도 페이지가 있으면 기록

### 출력 형식(성공)
{
  "status": 200,
  "message": "목차가 확인 되었습니다.",
  "length": <N>,
  "parsed": [
    {"level_1":"...","level_2":"...","level_3":"...","kwan":"...","jo":"...","page_start": <int>, "page_end": 0}
  ]
}

### 실패 형식(예시)
{"status": 404, "message": "목차가 존재하지 않습니다.", "length": 0, "parsed": []}
{"status": 500, "message": "목차 파싱에 실패했습니다.", "length": 0, "parsed": []}
"""
```

---

## 4. Nodes 구현

> LangGraph의 각 노드는 `ParserState`를 입력으로 받아 갱신 후 반환합니다.

```python
from langgraph.graph import StateGraph

# 4.1 문서 정보 조회 (total_pages)
async def node_doc_info(state: ParserState) -> ParserState:
    doc_id = state["doc_id"]
    info = await mcp_call("pdf.get_info", {"doc_id": doc_id})
    state["total_pages"] = int(info.get("page_count", 0))
    state["job_status"] = "running"
    state.setdefault("logs", []).append(f"[doc_info] total_pages={state['total_pages']}")
    return state

# 4.2 5페이지 윈도우 기반 목차 탐지 루프
async def node_detect_toc_window(state: ParserState) -> ParserState:
    ws = state.get("window_size", 5)
    start = state.get("window_start", 0)
    total = state["total_pages"]
    end = min(start + ws, total)
    pages = list(range(start, end))

    # MCP로 페이지 텍스트(or 요약) 확보 필요 시 확장 가능. 여기서는 doc_id+index만 전달한다고 가정하고 LLM에 조건 설명.
    prompt = (TOC_DETECT_PROMPT + "\n\n" +
              json.dumps({"doc_id": state["doc_id"], "window_pages": pages}, ensure_ascii=False))
    result_str = gpt5_chat(prompt)

    try:
        result = json.loads(result_str)
    except Exception as e:
        state["error"] = f"toc detect json parse error: {e}"
        state["job_status"] = "failed"
        return state

    toc_pages = result.get("toc_pages", []) or []
    state.setdefault("toc_pages", [])
    state["toc_pages"] = sorted(list(set(state["toc_pages"] + toc_pages)))
    state.setdefault("logs", []).append(
        f"[detect] window {start}-{end-1} -> found={toc_pages} conf={result.get('confidence')}"
    )

    # 다음 윈도우로 이동
    state["window_start"] = end
    return state

# 4.3 목차 탐지 종료 판단
# - 더 이상 페이지 없으면 종료
# - toc_pages가 비어있다면 실패 경로로, 있으면 다음 단계로

def cond_after_detect(state: ParserState) -> str:
    total = state.get("total_pages", 0)
    cursor = state.get("window_start", 0)
    if cursor < total:
        return "continue"  # 탐지 루프 계속
    # 탐지 종료 시
    return "next" if state.get("toc_pages") else "no_toc"

# 4.4 스팬 추출 (AI가 선택한 목차 페이지만)
async def node_extract_spans(state: ParserState) -> ParserState:
    doc_id = state["doc_id"]
    pages = state["toc_pages"]
    res = await mcp_call("pdf.parse_layout_spans", {"doc_id": doc_id, "pages": pages})
    state["spans"] = res.get("spans", [])
    state["job_status"] = "detected"
    state.setdefault("logs", []).append(f"[spans] extracted={len(state['spans'])} from pages={pages}")
    return state

# 4.5 스팬을 LLM 목차 파싱 입력 형태로 정리 + LLM 호출
async def node_llm_parse_toc(state: ParserState) -> ParserState:
    # 스팬 정렬 및 텍스트 블록 구성
    spans = state.get("spans", [])
    spans.sort(key=lambda s: (s["page"], s.get("line_id", 0), s.get("span_id", 0)))

    blocks: List[str] = []
    for s in spans:
        text = (s.get("text") or "").strip()
        if not text or len(text) < 2:
            continue
        font_name = s.get("font_name", "Unknown")
        font_size = s.get("font_size", 0)
        bold = s.get("bold", False)
        page = s.get("page", 0)
        line_id = s.get("line_id", 0)
        tag = f"페이지 {page+1}, 라인 {line_id+1}: {text} [{font_name}, {font_size}pt{'_Bold' if bold else ''}]"
        blocks.append(tag)

    prompt = INSURANCE_TOC_PARSING_PROMPT + "\n" + "\n".join(blocks)
    result_str = gpt5_chat(prompt)
    try:
        result = json.loads(result_str)
    except Exception as e:
        state["error"] = f"toc parse json error: {e}"
        state["job_status"] = "failed"
        return state

    state["toc_parsed"] = result
    ok = result.get("status") == 200 and result.get("parsed")
    state["job_status"] = "parsed" if ok else "failed"
    state.setdefault("logs", []).append(f"[llm_toc] status={result.get('status')} length={result.get('length')}")
    if not ok:
        state["error"] = result.get("message", "toc parse failed")
    return state

# 4.6 page_end 자동 계산
async def node_calc_page_end(state: ParserState) -> ParserState:
    toc = state.get("toc_parsed", {})
    items = toc.get("parsed", [])
    # page_start 오름차순 정렬 보장
    items = sorted(items, key=lambda x: int(x.get("page_start", 0)))

    total_pages = state.get("total_pages", 0)
    for i in range(len(items)):
        if i + 1 < len(items):
            items[i]["page_end"] = int(items[i + 1].get("page_start", 0)) - 1
        else:
            items[i]["page_end"] = max(0, total_pages - 1)

    toc["parsed"] = items
    state["toc_parsed"] = toc
    state.setdefault("logs", []).append("[page_end] auto-calculated")
    return state

# 4.7 범위 기반 본문 추출 + 메타 생성
async def node_extract_ranges(state: ParserState) -> ParserState:
    doc_id = state["doc_id"]
    parsed = state.get("toc_parsed", {}).get("parsed", [])
    out_sections: List[Dict[str, Any]] = []

    for i, sec in enumerate(parsed):
        start = int(sec.get("page_start", 0))
        end = int(sec.get("page_end", start))
        pages = list(range(start, end + 1)) if end >= start else [start]

        content_res = await mcp_call("pdf.read", {"doc_id": doc_id, "pages": pages, "mode": "plain"})
        full = content_res.get("plain", "")

        # 제목 우선순위: jo > kwan > level_3 > level_2 > level_1
        title = sec.get("jo") or sec.get("kwan") or sec.get("level_3") or sec.get("level_2") or sec.get("level_1") or ""

        def extract_after_title(full_content: str, title: str) -> str:
            if not title or not full_content:
                return full_content
            pos = full_content.find(title)
            if pos != -1:
                return full_content[pos + len(title):].strip()
            # fuzzy fallback
            try:
                import difflib
                m = difflib.SequenceMatcher(None, title.lower(), full_content.lower()).find_longest_match(0, len(title), 0, len(full_content))
                if m.size > max(3, int(len(title) * 0.8)):
                    start_pos = m.b + m.size
                    return full_content[start_pos:].strip()
            except Exception:
                pass
            return full_content

        pure = extract_after_title(full, title)
        meta = {
            "text": pure,
            "para_count": pure.count("\n\n") + 1 if pure.strip() else 0,
            "char_count": len(pure.strip()),
            "has_table": ("표" in pure) or ("Table" in pure),
            "has_figure": ("그림" in pure) or ("Figure" in pure) or ("도" in pure),
            "pages": pages,
            "title": title,
        }
        merged = {**sec, **meta}
        out_sections.append(merged)

    state["sections"] = out_sections
    state["job_status"] = "extracted"
    state.setdefault("logs", []).append(f"[extract] sections={len(out_sections)}")
    return state

# 4.8 CSV 저장
async def node_write_csv(state: ParserState) -> ParserState:
    doc_id = state["doc_id"]
    headers = [
        "doc_id", "level_1", "level_2", "level_3", "kwan", "jo",
        "page_start", "page_end", "title", "para_count", "char_count",
        "has_table", "has_figure", "extract_path", "json_path"
    ]

    rows = []
    base_dir = f"outputs/{doc_id}"
    os.makedirs(base_dir, exist_ok=True)

    for i, s in enumerate(state.get("sections", []), start=1):
        # 텍스트/JSON 파일 경로
        extract_path = f"{base_dir}/section_{i}.txt"
        json_path = f"{base_dir}/section_{i}.json"
        # 로컬 파일 저장(본문/메타)
        with open(extract_path, "w", encoding="utf-8") as f:
            f.write(s.get("text", ""))
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False)

        rows.append([
            doc_id,
            s.get("level_1", ""), s.get("level_2", ""), s.get("level_3", ""), s.get("kwan", ""), s.get("jo", ""),
            int(s.get("page_start", 0)), int(s.get("page_end", 0)), s.get("title", ""),
            int(s.get("para_count", 0)), int(s.get("char_count", 0)),
            bool(s.get("has_table", False)), bool(s.get("has_figure", False)),
            f"../{extract_path}", f"../{json_path}"
        ])

    csv_path = f"outputs/{doc_id}_parsed.csv"
    # MCP fs.write_csv를 사용해도 되며, 여기선 로컬 저장 예시
    import csv
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    state["csv_path"] = csv_path
    state["job_status"] = "completed"
    state.setdefault("logs", []).append(f"[csv] saved -> {csv_path}")
    return state

# 4.9 실패 처리 노드(옵션)
async def node_fail(state: ParserState) -> ParserState:
    state["job_status"] = "failed"
    state.setdefault("logs", []).append(f"[fail] {state.get('error', 'no_toc_found')}")
    return state
```

---

## 5. 그래프 구성

```python
from langgraph.graph import StateGraph

graph = StateGraph(ParserState)

graph.add_node("doc_info", node_doc_info)
graph.add_node("detect_toc", node_detect_toc_window)
graph.add_node("extract_spans", node_extract_spans)
graph.add_node("llm_toc", node_llm_parse_toc)
graph.add_node("calc_end", node_calc_page_end)
graph.add_node("extract_ranges", node_extract_ranges)
graph.add_node("write_csv", node_write_csv)
graph.add_node("fail", node_fail)

# 시작점
graph.set_entry_point("doc_info")

# 흐름 연결
graph.add_edge("doc_info", "detect_toc")

# 조건부 분기: 탐지 루프
graph.add_conditional_edges("detect_toc", cond_after_detect, {
    "continue": "detect_toc",   # 다음 윈도우 계속 탐지
    "next": "extract_spans",    # 탐지 완료 → 스팬 추출
    "no_toc": "fail",           # 목차 없음 → 실패
})

# 이후 직선 흐름
graph.add_edge("extract_spans", "llm_toc")
graph.add_edge("llm_toc", "calc_end")
graph.add_edge("calc_end", "extract_ranges")
graph.add_edge("extract_ranges", "write_csv")

app = graph.compile()
```

> 필요 시 `langgraph.checkpoint.sqlite.SqliteSaver`를 붙여 장시간 작업에서 재시작/중단 복구를 지원할 수 있습니다.

---

## 6. 실행 예시

```python
# 비동기 실행 예시 (FastAPI 핸들러 등에서)
import asyncio

async def run_flow(doc_id: str):
    init: ParserState = {
        "doc_id": doc_id,
        "window_size": 5,
        "window_start": 0,
        "toc_pages": [],
        "logs": [],
        "job_status": "idle",
    }
    return await app.ainvoke(init)

# 테스트
# result = asyncio.run(run_flow("hanwha_personal_needai"))
# print(result.get("csv_path"))
# print("\n".join(result.get("logs", [])))
```

---

## 7. FastAPI 연동(백엔드 API) 예시

```python
# backend/main.py
from fastapi import FastAPI
from pydantic import BaseModel
import asyncio

app_api = FastAPI()

class ParseBody(BaseModel):
    doc_id: str

@app_api.post("/api/parse/run")
async def parse_run(body: ParseBody):
    out = await run_flow(body.doc_id)
    if out.get("job_status") == "completed":
        return {
            "status": 200,
            "toc_count": len(out.get("toc_parsed", {}).get("parsed", [])),
            "sections": len(out.get("sections", [])),
            "csv": out.get("csv_path"),
        }
    elif not out.get("toc_parsed"):
        return {"status": 204, "reason": "no_toc_found"}
    else:
        return {"status": 500, "error": out.get("error", "unknown")}
```

---

## 8. React 프런트엔드 연결 포인트

* 기존 프런트엔드의 호출은 그대로 유지(`POST /api/parse/run`, `GET /api/docs/{doc_id}/sections` 등)
* LangGraph 플로우는 백엔드 내부의 **오케스트레이터**로 대체
* 진행 로그는 `state.logs`를 SSE(WebSocket)로 스트리밍 구현 가능

---

## 9. 품질/안전 가드

* **모델 가드**: `ALLOWED_MODELS` 강제 → GPT-5/-mini 외 사용 시 `assert`로 즉시 실패
* **LLM JSON 파싱 가드**: 모든 LLM 응답은 `json.loads` 예외 처리
* **정렬 가드**: `page_start` 정렬 후 `page_end` 계산
* **텍스트 매칭 가드**: 정확 매칭 실패 시 fuzzy fallback

---

## 10. 확장 아이디어

* 스팬 전처리 노드 분리(줄바꿈 병합/페이지번호 검증) → LLM 호출 비용 절감
* `extract_ranges` 노드 내 멀티프로세싱/비동기 배치 → 대형 문서 처리 가속
* `SqliteSaver`로 체크포인트 도입 → 중간 재실행
* 섹션별 요약/키워드/임베딩 추가 노드 → 검색 UX 강화

---

## 11. 의존성(예시)

```toml
# pyproject.toml 일부 예시
[tool.poetry.dependencies]
python = "^3.11"
langgraph = "*"
openai = "*"
httpx = "^0.27"
PyMuPDF = "^1.23.26"
fastapi = "^0.111"
uvicorn = "^0.30"
```

---

## 12. 체크리스트

* [x] GPT-5 전용 호출 준수
* [x] 5페이지 윈도우 목차 탐지 루프
* [x] 스팬 레벨 추출(MCP)
* [x] 보험약관 전용 LLM 파싱
* [x] page_end 자동 계산
* [x] 범위 추출 및 CSV 저장
* [x] 실패/로그 상태 관리

---

### 부록 A. 스팬 입력 샘플 → 블록 문자열 변환 규칙

* `페이지 {page+1}, 라인 {line+1}: {text} [{font_name}, {font_size}pt{_Bold}]`
* 공백·잡음 스팬 제거(길이<2)
* 정렬키: `(page, line_id, span_id)`

### 부록 B. 출력 CSV 스키마

* `doc_id, level_1, level_2, level_3, kwan, jo, page_start, page_end, title, para_count, char_count, has_table, has_figure, extract_path, json_path`

### 부록 C. 오류 대응 가이드

* LLM JSON 파싱 실패 → `state.error` 기록, `node_fail`로 분기
* MCP 통신 실패 → 재시도/타임아웃 조정, 부분 재실행(체크포인트)
* 목차 없음 → `no_toc` 경로 처리 후 204 응답 반환

```
```

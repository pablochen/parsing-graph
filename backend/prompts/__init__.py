"""
AI 프롬프트 템플릿 모듈
"""

from .insurance_prompts import (
    TOC_DETECT_PROMPT,
    INSURANCE_TOC_PARSING_PROMPT,
    get_toc_detect_prompt,
    get_toc_parsing_prompt
)

__all__ = [
    "TOC_DETECT_PROMPT",
    "INSURANCE_TOC_PARSING_PROMPT", 
    "get_toc_detect_prompt",
    "get_toc_parsing_prompt"
]
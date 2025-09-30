"""
OpenRouter API 클라이언트
"""
import logging
from typing import Optional
from openai import OpenAI
from ..config import settings

logger = logging.getLogger(__name__)

# OpenRouter 클라이언트 초기화
openrouter_client = OpenAI(
    api_key=settings.OPENROUTER_API_KEY,
    base_url=settings.OPENROUTER_BASE_URL,
    default_headers={
        "HTTP-Referer": settings.OPENROUTER_SITE_URL,
        "X-Title": settings.OPENROUTER_APP_NAME,
    }
)


def openrouter_chat(
    prompt: str, 
    temperature: float = 0.0, 
    model: str = settings.OPENROUTER_MODEL,
    max_tokens: Optional[int] = None,
    system_prompt: Optional[str] = None
) -> str:
    """
    OpenRouter 채팅 완성 함수
    
    Args:
        prompt: 사용자 프롬프트
        temperature: 창의성 정도 (0.0-1.0)
        model: 사용할 모델
        max_tokens: 최대 토큰 수
        system_prompt: 시스템 프롬프트
    
    Returns:
        AI 응답 텍스트
    
    Raises:
        ValueError: 허용되지 않은 모델 사용 시
        Exception: API 호출 실패 시
    """
    # 모델 검증
    if model not in settings.ALLOWED_MODELS:
        raise ValueError(
            f"모델 '{model}'은 허용되지 않습니다. "
            f"허용 모델: {settings.ALLOWED_MODELS}"
        )
    
    try:
        # 메시지 구성
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # API 호출
        response = openrouter_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        content = response.choices[0].message.content or ""
        
        # 로깅
        logger.info(
            f"OpenRouter API 호출 성공: model={model}, "
            f"input_tokens={len(prompt)//4}, output_tokens={len(content)//4}"
        )
        
        return content
        
    except Exception as e:
        logger.error(f"OpenRouter API 호출 실패: {e}")
        raise


async def openrouter_chat_async(
    prompt: str, 
    temperature: float = 0.0, 
    model: str = settings.OPENROUTER_MODEL,
    max_tokens: Optional[int] = None,
    system_prompt: Optional[str] = None
) -> str:
    """
    OpenRouter 비동기 채팅 완성 함수
    """
    import asyncio
    return await asyncio.get_event_loop().run_in_executor(
        None, 
        lambda: openrouter_chat(prompt, temperature, model, max_tokens, system_prompt)
    )


def validate_model(model: str) -> bool:
    """
    모델 유효성 검증
    
    Args:
        model: 검증할 모델명
        
    Returns:
        유효한 모델인지 여부
    """
    return model in settings.ALLOWED_MODELS


def get_available_models() -> list[str]:
    """
    사용 가능한 모델 목록 반환
    
    Returns:
        허용된 모델 목록
    """
    return list(settings.ALLOWED_MODELS)


# 호환성을 위한 별명들
gpt5_chat = openrouter_chat
gpt5_chat_async = openrouter_chat_async
openai_client = openrouter_client
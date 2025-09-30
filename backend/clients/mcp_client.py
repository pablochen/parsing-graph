"""
MCP (Model Context Protocol) 클라이언트
JSON-RPC 2.0 기반 통신
"""
import logging
from typing import Dict, Any, Optional
import httpx
import asyncio
from ..config import settings

logger = logging.getLogger(__name__)


class MCPClientError(Exception):
    """MCP 클라이언트 예외"""
    pass


async def mcp_call(
    method: str, 
    params: Dict[str, Any], 
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """
    비동기 MCP 서버 호출
    
    Args:
        method: 호출할 메서드명 (예: 'pdf.parse_layout_spans')
        params: 메서드 파라미터
        timeout: 타임아웃 (초)
    
    Returns:
        MCP 서버 응답 데이터
        
    Raises:
        MCPClientError: MCP 호출 실패 시
    """
    if timeout is None:
        timeout = settings.MCP_TIMEOUT
    
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params
    }
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{settings.MCP_BASE}/mcp",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            data = response.json()
            
            # JSON-RPC 2.0 에러 체크
            if "error" in data:
                error_info = data["error"]
                raise MCPClientError(
                    f"MCP 서버 에러: {error_info.get('message', 'Unknown error')} "
                    f"(code: {error_info.get('code', 'Unknown')})"
                )
            
            logger.info(f"MCP 호출 성공: {method}")
            return data.get("result", {})
            
    except httpx.HTTPError as e:
        logger.error(f"MCP HTTP 에러: {e}")
        raise MCPClientError(f"MCP 통신 실패: {e}")
    except Exception as e:
        logger.error(f"MCP 호출 실패: {e}")
        raise MCPClientError(f"MCP 예외: {e}")


def mcp_call_sync(
    method: str, 
    params: Dict[str, Any], 
    timeout: Optional[int] = None
) -> Dict[str, Any]:
    """
    동기 MCP 서버 호출
    
    Args:
        method: 호출할 메서드명
        params: 메서드 파라미터  
        timeout: 타임아웃 (초)
    
    Returns:
        MCP 서버 응답 데이터
        
    Raises:
        MCPClientError: MCP 호출 실패 시
    """
    if timeout is None:
        timeout = settings.MCP_TIMEOUT
    
    payload = {
        "jsonrpc": "2.0", 
        "id": 1,
        "method": method,
        "params": params
    }
    
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(
                f"{settings.MCP_BASE}/mcp",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            
            data = response.json()
            
            # JSON-RPC 2.0 에러 체크
            if "error" in data:
                error_info = data["error"]
                raise MCPClientError(
                    f"MCP 서버 에러: {error_info.get('message', 'Unknown error')} "
                    f"(code: {error_info.get('code', 'Unknown')})"
                )
            
            logger.info(f"MCP 호출 성공: {method}")
            return data.get("result", {})
            
    except httpx.HTTPError as e:
        logger.error(f"MCP HTTP 에러: {e}")
        raise MCPClientError(f"MCP 통신 실패: {e}")
    except Exception as e:
        logger.error(f"MCP 호출 실패: {e}")
        raise MCPClientError(f"MCP 예외: {e}")


# 특화된 MCP 호출 함수들
async def pdf_get_info(doc_id: str) -> Dict[str, Any]:
    """PDF 문서 정보 조회"""
    return await mcp_call("pdf.get_info", {"doc_id": doc_id})


async def pdf_parse_layout_spans(doc_id: str, pages: list[int]) -> Dict[str, Any]:
    """PDF 스팬 레벨 파싱"""
    return await mcp_call("pdf.parse_layout_spans", {"doc_id": doc_id, "pages": pages})


async def pdf_read(doc_id: str, pages: list[int], mode: str = "plain") -> Dict[str, Any]:
    """PDF 텍스트 읽기"""
    return await mcp_call("pdf.read", {"doc_id": doc_id, "pages": pages, "mode": mode})


async def fs_write_csv(file_path: str, data: list[list], headers: list[str]) -> Dict[str, Any]:
    """CSV 파일 저장"""
    return await mcp_call("fs.write_csv", {
        "file_path": file_path,
        "data": data, 
        "headers": headers
    })


class MCPConnectionPool:
    """MCP 연결 풀 관리"""
    
    def __init__(self):
        self.connected_servers: Dict[str, Dict[str, Any]] = {}
        
    async def setup_server(self, server_id: str, server_config: Dict[str, Any]) -> str:
        """MCP 서버 설정 및 연결"""
        try:
            # 서버 연결 테스트
            test_result = await mcp_call("server.ping", {}, timeout=10)
            
            # 사용 가능한 도구 및 리소스 조회
            tools = await mcp_call("server.list_tools", {})
            resources = await mcp_call("server.list_resources", {})
            
            self.connected_servers[server_id] = {
                "config": server_config,
                "tools": tools,
                "resources": resources,
                "status": "connected",
                "last_ping": test_result
            }
            
            logger.info(f"MCP 서버 연결 성공: {server_id}")
            return server_id
            
        except Exception as e:
            logger.error(f"MCP 서버 연결 실패: {server_id}, {e}")
            raise MCPClientError(f"서버 연결 실패: {e}")
    
    def get_server_status(self, server_id: str) -> Optional[Dict[str, Any]]:
        """서버 상태 조회"""
        return self.connected_servers.get(server_id)
    
    def list_servers(self) -> Dict[str, Dict[str, Any]]:
        """연결된 서버 목록 반환"""
        return self.connected_servers.copy()


# 전역 연결 풀 인스턴스
mcp_pool = MCPConnectionPool()
#!/usr/bin/env python3
"""
백엔드 서버 시작 스크립트
"""
import os
import sys
import subprocess
import time
from pathlib import Path

# 프로젝트 루트 디렉토리
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"

def check_requirements():
    """필수 요구사항 확인"""
    print("🔍 필수 요구사항 확인 중...")
    
    # Python 버전 확인
    if sys.version_info < (3, 11):
        print("❌ Python 3.11 이상이 필요합니다.")
        return False
    
    # .env 파일 확인
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        print("❌ .env 파일이 없습니다. .env.example을 참고하여 생성하세요.")
        return False
    
    # 의존성 확인
    try:
        import fastapi
        import openai
        import langgraph
        print("✅ 필수 의존성 확인 완료")
        return True
    except ImportError as e:
        print(f"❌ 필수 의존성 누락: {e}")
        print("pip install -r requirements.txt 실행하세요.")
        return False

def start_server():
    """FastAPI 서버 시작"""
    print("🚀 FastAPI 서버 시작 중...")
    
    os.chdir(PROJECT_ROOT)
    
    cmd = [
        sys.executable, "-m", "uvicorn",
        "backend.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload",
        "--log-level", "info"
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋 서버 종료")
    except subprocess.CalledProcessError as e:
        print(f"❌ 서버 시작 실패: {e}")
        return False
    
    return True

def main():
    """메인 함수"""
    print("=== 보험약관 PDF 파싱 시스템 백엔드 ===")
    print()
    
    # 요구사항 확인
    if not check_requirements():
        sys.exit(1)
    
    # MCP 서버 상태 확인 (선택사항)
    print("⚠️  MCP 서버가 실행 중인지 확인하세요 (http://localhost:8001)")
    print("⚠️  OpenAI API 키가 .env 파일에 설정되어 있는지 확인하세요")
    print()
    
    # 서버 시작
    success = start_server()
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
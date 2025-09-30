@echo off
chcp 65001 > nul
echo ================================
echo  백엔드 서버 시작
echo ================================
echo.

:: 현재 디렉토리 확인
echo 📁 현재 위치: %cd%
echo.

:: Python 확인
echo 🔍 Python 확인 중...
python --version >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ Python 버전:
    python --version
) else (
    echo ❌ Python을 찾을 수 없습니다.
    echo    install-dependencies.bat를 먼저 실행하세요.
    pause
    goto end
)
echo.

:: 환경 파일 확인
echo 🔧 환경 설정 확인 중...
if exist ".env" (
    echo ✅ .env 파일 존재
    findstr "OPENROUTER_API_KEY" .env >nul
    if %errorLevel% == 0 (
        echo ✅ OPENROUTER_API_KEY 설정됨
    ) else (
        echo ⚠️  .env 파일에 OPENROUTER_API_KEY를 설정하세요
        echo    예: OPENROUTER_API_KEY=sk-or-v1-...
    )
) else (
    echo ❌ .env 파일이 없습니다.
    echo    install-dependencies.bat를 먼저 실행하세요.
    pause
    goto end
)
echo.

:: 필요한 디렉토리 생성
echo 📁 필요한 디렉토리 확인 중...
if not exist "uploads" (
    mkdir uploads
    echo ✅ uploads 디렉토리 생성
)
if not exist "outputs" (
    mkdir outputs
    echo ✅ outputs 디렉토리 생성
)
if not exist "logs" (
    mkdir logs
    echo ✅ logs 디렉토리 생성
)
echo.

:: FastAPI 모듈 확인
echo 📦 FastAPI 설치 확인 중...
python -c "import fastapi; print('FastAPI 버전:', fastapi.__version__)" 2>nul
if %errorLevel% == 0 (
    echo ✅ FastAPI 설치됨
) else (
    echo ❌ FastAPI가 설치되지 않았습니다.
    echo    install-dependencies.bat를 먼저 실행하세요.
    pause
    goto end
)
echo.

:: LangGraph 모듈 확인
echo 📦 LangGraph 설치 확인 중...
python -c "import langgraph; print('LangGraph 설치 확인됨')" 2>nul
if %errorLevel% == 0 (
    echo ✅ LangGraph 설치됨
) else (
    echo ❌ LangGraph가 설치되지 않았습니다.
    echo    install-dependencies.bat를 먼저 실행하세요.
    pause
    goto end
)
echo.

:: 백엔드 시작
echo 🚀 백엔드 서버 시작 중...
echo.
echo ================================
echo  서버 정보
echo ================================
echo  백엔드 URL: http://localhost:8000
echo  API 문서: http://localhost:8000/docs
echo  ReDoc: http://localhost:8000/redoc
echo ================================
echo.
echo 서버를 종료하려면 Ctrl+C를 누르세요.
echo.

:: Poetry 사용 시도
poetry --version >nul 2>&1
if %errorLevel% == 0 (
    echo Poetry로 실행 시도...
    poetry run python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --log-level info
) else (
    echo 일반 Python으로 실행...
    python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload --log-level info
)

:end
echo.
echo 백엔드 서버가 종료되었습니다.
pause
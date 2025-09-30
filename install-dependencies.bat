@echo off
chcp 65001 > nul
echo ================================
echo  의존성 설치 스크립트
echo ================================
echo.

:: 관리자 권한 확인
net session >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ 관리자 권한으로 실행 중
) else (
    echo ⚠️  관리자 권한이 없습니다. 일부 설치가 제한될 수 있습니다.
)
echo.

:: Python 설치 확인
echo 🔍 Python 설치 확인 중...
python --version >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ Python 설치됨:
    python --version
) else (
    echo ❌ Python이 설치되지 않았습니다.
    echo    https://www.python.org/downloads/ 에서 Python 3.11+ 다운로드
    pause
    goto end
)
echo.

:: Node.js 설치 확인
echo 🔍 Node.js 설치 확인 중...
node --version >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ Node.js 설치됨:
    node --version
    npm --version
) else (
    echo ❌ Node.js가 설치되지 않았습니다.
    echo    https://nodejs.org/ 에서 Node.js 18+ 다운로드
    pause
    goto end
)
echo.

:: pip 업그레이드
echo 📦 pip 업그레이드 중...
python -m pip install --upgrade pip
echo.

:: Poetry 설치 확인
echo 🔍 Poetry 확인 중...
poetry --version >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ Poetry 이미 설치됨
) else (
    echo 📦 Poetry 설치 중...
    curl -sSL https://install.python-poetry.org | python -
    if %errorLevel% == 0 (
        echo ✅ Poetry 설치 완료
        echo ⚠️  터미널을 재시작하거나 PATH를 새로고침하세요
    ) else (
        echo ⚠️  Poetry 설치 실패. pip로 대체 설치 시도...
        pip install poetry
    )
)
echo.

:: Python 백엔드 의존성 설치
echo 🐍 Python 백엔드 의존성 설치 중...
if exist "pyproject.toml" (
    echo Poetry로 설치 시도...
    poetry install
    if %errorLevel% == 0 (
        echo ✅ Poetry로 백엔드 의존성 설치 완료
    ) else (
        echo ⚠️  Poetry 실패. pip로 대체 설치...
        pip install fastapi uvicorn langgraph langchain langchain-openai openai pydantic pydantic-settings httpx PyMuPDF sqlalchemy alembic redis psycopg2-binary python-multipart python-jose bcrypt python-dotenv
        if %errorLevel% == 0 (
            echo ✅ pip로 백엔드 의존성 설치 완료
        ) else (
            echo ❌ 백엔드 의존성 설치 실패
        )
    )
) else (
    echo ❌ pyproject.toml을 찾을 수 없습니다.
)
echo.

:: Node.js 프론트엔드 의존성 설치
echo ⚛️  React 프론트엔드 의존성 설치 중...
if exist "frontend\package.json" (
    cd frontend
    echo 현재 디렉토리: %cd%
    npm install
    if %errorLevel% == 0 (
        echo ✅ 프론트엔드 의존성 설치 완료
    ) else (
        echo ❌ 프론트엔드 의존성 설치 실패
    )
    cd ..
) else (
    echo ❌ frontend\package.json을 찾을 수 없습니다.
)
echo.

:: 필요한 디렉토리 생성
echo 📁 필요한 디렉토리 생성 중...
if not exist "uploads" mkdir uploads
if not exist "outputs" mkdir outputs
if not exist "logs" mkdir logs
echo ✅ 디렉토리 생성 완료
echo.

:: 환경 파일 확인
echo 🔧 환경 설정 파일 확인 중...
if exist ".env" (
    echo ✅ .env 파일 존재
) else (
    if exist ".env.example" (
        echo 📋 .env.example에서 .env 생성 중...
        copy ".env.example" ".env"
        echo ✅ .env 파일 생성 완료
        echo ⚠️  .env 파일을 편집하여 OPENAI_API_KEY를 설정하세요
    ) else (
        echo ❌ .env.example 파일을 찾을 수 없습니다.
    )
)
echo.

:end
echo ================================
echo  설치 완료!
echo ================================
echo.
echo 다음 단계:
echo 1. .env 파일에서 OPENAI_API_KEY 설정
echo 2. start-backend.bat 실행 (백엔드 시작)
echo 3. start-frontend.bat 실행 (프론트엔드 시작)
echo 또는 start-all.bat 실행 (전체 시작)
echo.
pause
@echo off
chcp 65001 > nul
echo ================================
echo  보험약관 PDF 파싱 시스템 시작
echo ================================
echo.

:: 현재 디렉토리 확인
echo 📁 현재 위치: %cd%
echo.

:: 의존성 확인
echo 🔍 시스템 요구사항 확인 중...

:: Python 확인
python --version >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ Python 설치됨
) else (
    echo ❌ Python이 필요합니다. install-dependencies.bat를 먼저 실행하세요.
    pause
    goto end
)

:: Node.js 확인
node --version >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ Node.js 설치됨
) else (
    echo ❌ Node.js가 필요합니다. install-dependencies.bat를 먼저 실행하세요.
    pause
    goto end
)

:: 환경 파일 확인
if exist ".env" (
    echo ✅ .env 파일 존재
    findstr "OPENROUTER_API_KEY" .env >nul
    if %errorLevel% == 0 (
        echo ✅ OPENROUTER_API_KEY 설정됨
    ) else (
        echo ⚠️  .env 파일에 OPENROUTER_API_KEY를 설정하세요
        echo    현재 .env 파일을 편집하시겠습니까? (Y/N)
        set /p choice="선택: "
        if /i "%choice%" equ "Y" (
            notepad .env
            echo 파일을 저장한 후 계속 진행합니다.
            pause
        )
    )
) else (
    echo ❌ .env 파일이 필요합니다. install-dependencies.bat를 먼저 실행하세요.
    pause
    goto end
)
echo.

:: 백엔드 의존성 확인
echo 📦 백엔드 의존성 확인 중...
python -c "import fastapi" >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ 백엔드 의존성 설치됨
) else (
    echo ❌ 백엔드 의존성이 필요합니다. install-dependencies.bat를 먼저 실행하세요.
    pause
    goto end
)

:: 프론트엔드 의존성 확인
echo 📦 프론트엔드 의존성 확인 중...
if exist "frontend\node_modules" (
    echo ✅ 프론트엔드 의존성 설치됨
) else (
    echo ❌ 프론트엔드 의존성이 필요합니다. install-dependencies.bat를 먼저 실행하세요.
    pause
    goto end
)
echo.

:: 필요한 디렉토리 생성
echo 📁 필요한 디렉토리 확인 중...
if not exist "uploads" mkdir uploads
if not exist "outputs" mkdir outputs
if not exist "logs" mkdir logs
echo ✅ 디렉토리 준비 완료
echo.

:: 시작 옵션 선택
echo ================================
echo  시작 방법 선택
echo ================================
echo  1. 백엔드만 시작
echo  2. 프론트엔드만 시작  
echo  3. 백엔드 + 프론트엔드 동시 시작
echo  4. 취소
echo ================================
set /p choice="선택 (1-4): "

if "%choice%"=="1" goto start_backend_only
if "%choice%"=="2" goto start_frontend_only
if "%choice%"=="3" goto start_both
if "%choice%"=="4" goto end
echo 잘못된 선택입니다.
goto end

:start_backend_only
echo.
echo 🚀 백엔드만 시작합니다...
call start-backend.bat
goto end

:start_frontend_only
echo.
echo 🚀 프론트엔드만 시작합니다...
call start-frontend.bat
goto end

:start_both
echo.
echo 🚀 백엔드와 프론트엔드를 동시에 시작합니다...
echo.
echo ================================
echo  실행 정보
echo ================================
echo  백엔드: http://localhost:8000
echo  프론트엔드: http://localhost:3000
echo  API 문서: http://localhost:8000/docs
echo ================================
echo.
echo 두 개의 새 터미널 창이 열립니다.
echo 시스템을 종료하려면 각 터미널에서 Ctrl+C를 누르세요.
echo.
pause

:: 백엔드를 새 터미널에서 시작
start "백엔드 서버" cmd /k "start-backend.bat"

:: 잠시 대기 (백엔드가 먼저 시작되도록)
timeout /t 3 /nobreak >nul

:: 프론트엔드를 새 터미널에서 시작
start "프론트엔드 서버" cmd /k "start-frontend.bat"

echo.
echo ✅ 백엔드와 프론트엔드가 별도 터미널에서 시작되었습니다.
echo.
echo 브라우저에서 http://localhost:3000 에 접속하세요.
echo.
pause
goto end

:end
echo.
echo 프로그램을 종료합니다.
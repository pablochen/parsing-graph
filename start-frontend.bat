@echo off
chcp 65001 > nul
echo ================================
echo  프론트엔드 서버 시작
echo ================================
echo.

:: 현재 디렉토리 확인
echo 📁 현재 위치: %cd%
echo.

:: Node.js 확인
echo 🔍 Node.js 확인 중...
node --version >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ Node.js 버전:
    node --version
    npm --version
) else (
    echo ❌ Node.js를 찾을 수 없습니다.
    echo    install-dependencies.bat를 먼저 실행하세요.
    pause
    goto end
)
echo.

:: frontend 디렉토리 확인
echo 📁 frontend 디렉토리 확인 중...
if exist "frontend" (
    echo ✅ frontend 디렉토리 존재
    cd frontend
    echo 📁 현재 위치: %cd%
) else (
    echo ❌ frontend 디렉토리를 찾을 수 없습니다.
    pause
    goto end
)
echo.

:: package.json 확인
echo 📦 package.json 확인 중...
if exist "package.json" (
    echo ✅ package.json 존재
) else (
    echo ❌ package.json을 찾을 수 없습니다.
    pause
    goto end
)
echo.

:: node_modules 확인
echo 📦 의존성 확인 중...
if exist "node_modules" (
    echo ✅ node_modules 존재
) else (
    echo ⚠️  node_modules가 없습니다. npm install 실행 중...
    npm install
    if %errorLevel% == 0 (
        echo ✅ 의존성 설치 완료
    ) else (
        echo ❌ 의존성 설치 실패
        pause
        goto end
    )
)
echo.

:: React 모듈 확인
echo 📦 React 설치 확인 중...
if exist "node_modules\react" (
    echo ✅ React 설치됨
) else (
    echo ❌ React가 설치되지 않았습니다.
    echo    install-dependencies.bat를 먼저 실행하세요.
    pause
    goto end
)
echo.

:: 백엔드 서버 확인
echo 🔍 백엔드 서버 상태 확인 중...
curl -s http://localhost:8000/health >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ 백엔드 서버 실행 중 (http://localhost:8000)
) else (
    echo ⚠️  백엔드 서버가 실행되지 않았습니다.
    echo    start-backend.bat를 먼저 실행하세요.
    echo    그래도 프론트엔드를 시작하시겠습니까? (Y/N)
    set /p choice="선택: "
    if /i "%choice%" neq "Y" goto end
)
echo.

:: 프론트엔드 시작
echo 🚀 React 개발 서버 시작 중...
echo.
echo ================================
echo  서버 정보
echo ================================
echo  프론트엔드 URL: http://localhost:3000
echo  백엔드 API: http://localhost:8000
echo ================================
echo.
echo 서버를 종료하려면 Ctrl+C를 누르세요.
echo.

:: 환경변수 설정
set VITE_API_BASE_URL=http://localhost:8000/api/v1

:: 개발 서버 시작
npm run dev

:end
echo.
echo 프론트엔드 서버가 종료되었습니다.
cd ..
pause
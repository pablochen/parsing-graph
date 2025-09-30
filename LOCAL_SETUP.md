# 🏠 로컬 실행 가이드

Windows 환경에서 Docker 없이 로컬로 실행하는 완전 가이드입니다.

## 🚀 빠른 시작 (3단계)

### 1단계: 의존성 설치
```cmd
# 프로젝트 디렉토리에서 실행
install-dependencies.bat
```

### 2단계: 환경 설정
```cmd
# .env 파일 편집 (메모장으로 열림)
notepad .env

# OPENAI_API_KEY 설정
OPENAI_API_KEY=your_openai_api_key_here
GPT5_MODEL=gpt-5-mini
```

### 3단계: 시스템 시작
```cmd
# 전체 시스템 시작
start-all.bat

# 또는 개별 시작
start-backend.bat    # 백엔드만
start-frontend.bat   # 프론트엔드만
```

## 📋 제공되는 배치 파일들

### `install-dependencies.bat`
- **기능**: 모든 의존성 자동 설치
- **포함**: Python 패키지, Node.js 패키지, 디렉토리 생성
- **실행 시간**: 약 3-5분

### `start-backend.bat`
- **기능**: FastAPI 백엔드 서버 시작
- **주소**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs

### `start-frontend.bat`
- **기능**: React 프론트엔드 개발 서버 시작
- **주소**: http://localhost:3000
- **자동 프록시**: 백엔드 API 연결

### `start-all.bat`
- **기능**: 백엔드 + 프론트엔드 동시 시작
- **특징**: 별도 터미널 창에서 실행

## 🔧 시스템 요구사항

### 필수 소프트웨어
- **Python 3.11+** ✅ 설치됨 (3.13.5)
- **Node.js 18+** ✅ 설치됨 (22.17.0)
- **Windows 10/11**

### 권장 소프트웨어
- **Git** (소스 코드 관리)
- **Visual Studio Code** (개발 환경)
- **Chrome/Edge** (브라우저)

## 📁 설치 후 디렉토리 구조

```
parsing-graph/
├── 📁 uploads/              # PDF 업로드 디렉토리
├── 📁 outputs/              # 파싱 결과 저장
├── 📁 logs/                 # 로그 파일
├── 📁 backend/              # Python 백엔드
├── 📁 frontend/             # React 프론트엔드
│   └── 📁 node_modules/     # Node.js 의존성
├── 📄 .env                  # 환경 설정 파일
├── 🔧 install-dependencies.bat
├── 🚀 start-backend.bat
├── 🚀 start-frontend.bat
└── 🚀 start-all.bat
```

## 🌐 접속 정보

### 프론트엔드 (사용자 인터페이스)
- **URL**: http://localhost:3000
- **기능**: 대시보드, 문서 관리, 파싱 결과 확인

### 백엔드 API
- **URL**: http://localhost:8000
- **Health Check**: http://localhost:8000/health
- **API 문서**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc

## 🔍 실행 확인 방법

### 1. 백엔드 확인
```cmd
curl http://localhost:8000/health
# 또는 브라우저에서 http://localhost:8000/health 접속
```

### 2. 프론트엔드 확인
- 브라우저에서 http://localhost:3000 접속
- 대시보드가 로드되는지 확인

### 3. API 문서 확인
- 브라우저에서 http://localhost:8000/docs 접속
- Swagger UI에서 API 테스트 가능

## 🐛 문제 해결

### Python 관련 오류
```cmd
# 가상환경 생성 (선택사항)
python -m venv venv
venv\Scripts\activate

# 수동 패키지 설치
pip install fastapi uvicorn langgraph langchain langchain-openai openai
```

### Node.js 관련 오류
```cmd
# frontend 디렉토리에서
cd frontend
npm install
npm run dev
```

### 포트 충돌 오류
```cmd
# 사용 중인 포트 확인
netstat -ano | findstr :8000
netstat -ano | findstr :3000

# 프로세스 종료 (PID 확인 후)
taskkill /PID [PID번호] /F
```

### 환경변수 오류
1. `.env` 파일에 `OPENAI_API_KEY` 설정 확인
2. API 키에 특수문자가 있으면 따옴표로 감싸기
3. `.env` 파일이 UTF-8 인코딩인지 확인

## 🎯 사용 시나리오

### 1. 시스템 최초 설치
```cmd
1. install-dependencies.bat 실행
2. .env 파일에서 OPENAI_API_KEY 설정
3. start-all.bat 실행
4. 브라우저에서 http://localhost:3000 접속
```

### 2. 개발 중 재시작
```cmd
# 빠른 재시작
start-backend.bat    # 터미널 1
start-frontend.bat   # 터미널 2
```

### 3. 새로운 의존성 추가 후
```cmd
# 백엔드 의존성 추가 시
pip install [새패키지]

# 프론트엔드 의존성 추가 시
cd frontend
npm install [새패키지]
```

## 🔒 보안 설정

### API 키 관리
- `.env` 파일을 Git에 커밋하지 마세요
- API 키는 안전한 곳에 별도 보관
- 필요시 환경변수로 설정 가능

### 방화벽 설정
- Windows 방화벽에서 Python, Node.js 허용
- 개발 중에는 localhost만 사용 권장

## 📊 성능 최적화

### 백엔드 최적화
- `--workers` 옵션으로 워커 프로세스 증가
- Redis 캐시 활용 (선택사항)

### 프론트엔드 최적화
- 개발 모드에서는 HMR 자동 적용
- 프로덕션 빌드: `npm run build`

## 📞 지원

### 로그 확인
- **백엔드**: 터미널 출력 또는 `logs/` 디렉토리
- **프론트엔드**: 브라우저 개발자 도구 콘솔

### 디버깅 모드
```cmd
# 백엔드 디버그 모드
set DEBUG=true
start-backend.bat

# 프론트엔드 디버그 모드 (자동 적용)
start-frontend.bat
```

이제 시스템이 완전히 로컬에서 실행 가능합니다! 🎉
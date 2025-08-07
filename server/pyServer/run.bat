@echo off
chcp 65001 >nul

echo 🚗 Freematics Hub Server - Flask Version
echo ========================================

REM Python 버전 확인
python --version
if errorlevel 1 (
    echo ❌ Python이 설치되지 않았습니다.
    echo Python 3.7 이상을 설치해주세요.
    pause
    exit /b 1
)

REM 가상환경 확인
if not exist "venv" (
    echo 📦 가상환경을 생성합니다...
    python -m venv venv
)

REM 가상환경 활성화
echo 🔧 가상환경을 활성화합니다...
call venv\Scripts\activate.bat

REM 의존성 설치
echo 📥 의존성을 설치합니다...
pip install -r requirements.txt

REM 디렉토리 생성
echo 📁 필요한 디렉토리를 생성합니다...
if not exist "data" mkdir data
if not exist "log" mkdir log

REM 환경변수 설정 (선택사항)
if "%SECRET_KEY%"=="" (
    set SECRET_KEY=freematics-flask-server-%RANDOM%
    echo 🔑 SECRET_KEY가 설정되었습니다: %SECRET_KEY%
)

REM 서버 시작
echo 🚀 Flask 서버를 시작합니다...
echo 🌐 웹 인터페이스: http://localhost:8080
echo 📡 API 엔드포인트: http://localhost:8080/api/test
echo.
echo 서버를 중지하려면 Ctrl+C를 누르세요.
echo ========================================

python app.py

pause 
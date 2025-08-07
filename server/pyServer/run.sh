#!/bin/bash

# Freematics Hub Server - Flask Version
# 실행 스크립트

echo "🚗 Freematics Hub Server - Flask Version"
echo "========================================"

# Python 버전 확인
python_version=$(python3 --version 2>&1)
echo "Python 버전: $python_version"

# 가상환경 확인
if [ ! -d "venv" ]; then
    echo "📦 가상환경을 생성합니다..."
    python3 -m venv venv
fi

# 가상환경 활성화
echo "🔧 가상환경을 활성화합니다..."
source venv/bin/activate

# 의존성 설치
echo "📥 의존성을 설치합니다..."
pip install -r requirements.txt

# 디렉토리 생성
echo "📁 필요한 디렉토리를 생성합니다..."
mkdir -p data log

# 환경변수 파일 확인
if [ ! -f ".env" ]; then
    echo "📝 환경변수 파일이 없습니다. PostgreSQL 설정을 실행합니다..."
    if [ -f "setup_postgresql.sh" ]; then
        chmod +x setup_postgresql.sh
        ./setup_postgresql.sh
    else
        echo "⚠️ setup_postgresql.sh가 없습니다. env.example을 복사합니다..."
        cp env.example .env
    fi
fi

# 환경변수 로드
if [ -f ".env" ]; then
    echo "📋 환경변수 파일을 로드합니다..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# 서버 시작
echo "🚀 Flask 서버를 시작합니다..."
echo "🌐 웹 인터페이스: http://localhost:8080"
echo "📡 HTTP API: http://localhost:8080/api/test"
echo "📡 UDP 서버: localhost:33000"
echo ""
echo "서버를 중지하려면 Ctrl+C를 누르세요."
echo "========================================"

python3 app.py 
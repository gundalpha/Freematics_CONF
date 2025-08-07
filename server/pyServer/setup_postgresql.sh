#!/bin/bash

# PostgreSQL 데이터베이스 설정 스크립트
# Freematics Hub Server - Flask Version

echo "🐘 PostgreSQL 데이터베이스 설정"
echo "================================"

# PostgreSQL 설치 확인
if ! command -v psql &> /dev/null; then
    echo "❌ PostgreSQL이 설치되지 않았습니다."
    echo "Ubuntu/Debian: sudo apt-get install postgresql postgresql-contrib"
    echo "CentOS/RHEL: sudo yum install postgresql postgresql-server"
    echo "macOS: brew install postgresql"
    exit 1
fi

echo "✅ PostgreSQL이 설치되어 있습니다."

# PostgreSQL 서비스 시작
echo "🚀 PostgreSQL 서비스를 시작합니다..."
sudo systemctl start postgresql
sudo systemctl enable postgresql

# 데이터베이스 사용자 생성
echo "👤 데이터베이스 사용자를 생성합니다..."
sudo -u postgres psql -c "CREATE USER confitech WITH PASSWORD 'conf11';" 2>/dev/null || echo "사용자가 이미 존재합니다."

# 데이터베이스 생성
echo "🗄️ 데이터베이스를 생성합니다..."
sudo -u postgres psql -c "CREATE DATABASE trackdb OWNER confitech;" 2>/dev/null || echo "데이터베이스가 이미 존재합니다."

# 권한 부여
echo "🔐 권한을 부여합니다..."
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE trackdb TO confitech;"
sudo -u postgres psql -c "ALTER USER confitech CREATEDB;"

# 환경변수 파일 생성
echo "📝 환경변수 파일을 생성합니다..."
cat > .env << EOF
# PostgreSQL 데이터베이스 설정
DB_HOST=localhost
DB_PORT=5432
DB_NAME=trackdb
DB_USER=confitech
DB_PASSWORD=conf11

# Flask 설정
SECRET_KEY=freematics-flask-server-$(date +%s)
FLASK_ENV=development

# 서버 설정
HTTP_PORT=8080
MAX_CHANNELS=100
CHANNEL_TIMEOUT=300

# 로그 설정
LOG_LEVEL=INFO
EOF

echo "✅ PostgreSQL 설정이 완료되었습니다!"
echo ""
echo "📋 설정 정보:"
echo "   데이터베이스: trackdb"
echo "   사용자: confitech"
echo "   비밀번호: conf11"
echo "   호스트: localhost"
echo "   포트: 5432"
echo ""
echo "🚀 서버를 시작하려면 다음 명령을 실행하세요:"
echo "   python3 app.py"
echo ""
echo "🌐 웹 인터페이스: http://localhost:8080" 
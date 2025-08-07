# Freematics Hub Server - Flask Version

Freematics Hub Server의 Python Flask 버전입니다. 원본 C 버전의 기능을 Python으로 재구현했습니다.

**주요 변경사항:**
- SQLite에서 PostgreSQL로 데이터베이스 변경
- SQLAlchemy ORM 사용
- 환경변수 기반 설정
- 자동 폴백 시스템 (PostgreSQL 연결 실패 시 SQLite 사용)
- UDP 서버 지원 (원본 C 버전과 호환)
- 실시간 명령 전송 기능

## 🚀 주요 기능

- **실시간 차량 데이터 수집**: OBD-II 데이터, GPS 데이터, 센서 데이터 등
- **멀티 채널 지원**: 여러 디바이스 동시 연결 지원
- **RESTful API**: 표준 HTTP API 제공
- **UDP 서버**: 실시간 데이터 수신 및 명령 전송
- **웹 인터페이스**: 실시간 모니터링 대시보드
- **PostgreSQL/SQLite 데이터베이스**: 데이터 영속성 보장
- **로깅 시스템**: 상세한 로그 기록

## 📋 요구사항

- Python 3.7 이상
- pip (Python 패키지 관리자)
- PostgreSQL 12 이상 (선택사항, 없으면 SQLite 사용)

## 🛠️ 설치 방법

1. **저장소 클론**
```bash
git clone <repository-url>
cd server/pyServer
```

2. **가상환경 생성 (권장)**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows
```

3. **PostgreSQL 설정 (선택사항)**
```bash
# PostgreSQL 자동 설정
chmod +x setup_postgresql.sh
./setup_postgresql.sh

# 또는 수동 설정
sudo apt-get install postgresql postgresql-contrib  # Ubuntu/Debian
sudo systemctl start postgresql
sudo -u postgres createuser teleserver
sudo -u postgres createdb teleserver
```

4. **의존성 설치**
```bash
pip install -r requirements.txt
```

## 🚀 실행 방법

### 기본 실행
```bash
python app.py
```

### 환경변수 설정
```bash
# .env 파일 생성 (setup_postgresql.sh가 자동으로 생성)
cp env.example .env
# .env 파일을 편집하여 설정 변경

# 또는 환경변수 직접 설정
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=teleserver
export DB_USER=teleserver
export DB_PASSWORD=teleserver123
export SECRET_KEY="your-secret-key-here"
python app.py
```

### 포트 변경
```bash
python app.py --port 9090
```

## 🌐 웹 인터페이스

서버 실행 후 브라우저에서 다음 주소로 접속:

```
http://localhost:8080
```

**서버 정보:**
- HTTP 서버: `http://localhost:8080`
- UDP 서버: `localhost:33000`
- 웹 인터페이스: `http://localhost:8080`

## 📡 API 엔드포인트

### 1. 서버 상태 확인
```
GET /api/test
```

**응답:**
```json
{
  "date": "231201",
  "time": "143022",
  "tick": 1701430222000
}
```

### 2. 디바이스 로그인
```
GET /api/notify?id=DEVICE_ID&EV=1&VIN=12345678901234567&SSI=-50&DF=0
```

**파라미터:**
- `id`: 디바이스 ID (필수)
- `EV`: 이벤트 타입 (1=로그인, 2=로그아웃, 3=동기화)
- `VIN`: 차량 식별 번호 (선택)
- `SSI`: 신호 강도 (선택)
- `DF`: 디바이스 플래그 (선택)

### 3. 데이터 전송
```
POST /api/post?id=DEVICE_ID
Content-Type: text/plain

0:1701430222000,100:25,101:30,200:37.7749,201:-122.4194
```

**페이로드 형식:**
- `0:timestamp` - 타임스탬프
- `100:value` - RSSI 값
- `101:value` - 디바이스 온도
- `200:value` - GPS 위도
- `201:value` - GPS 경도

### 4. 채널 목록 조회
```
GET /api/channels
GET /api/channels?devid=DEVICE_ID
GET /api/channels?data=1&extend=1
```

**파라미터:**
- `devid`: 특정 디바이스 ID
- `data`: 데이터 포함 여부 (1=포함)
- `extend`: 확장 정보 포함 여부 (1=포함)

### 5. 채널 데이터 조회
```
GET /api/get?id=DEVICE_ID
```

### 6. 데이터 푸시
```
GET /api/push?id=DEVICE_ID&ts=1701430222000&100=25&101=30
```

### 7. UDP 명령 전송
```
GET /api/command?id=DEVICE_ID&cmd=COMMAND
```

**UDP 메시지 형식:**
- 데이터: `<DEVICE_ID>#<timestamp>:<pid>=<data>[*checksum]`
- 이벤트: `<DEVICE_ID>#EV=<event_id>,TS=<timestamp>,VIN=<vin>,SSI=<rssi>[*checksum]`
- 명령: `<DEVICE_ID>#EV=5,TK=<token>,CMD=<command>[*checksum]`

## 📊 데이터 구조

### PID (Parameter ID) 정의
- `0x000`: 타임스탬프
- `0x100`: RSSI (신호 강도)
- `0x101`: 디바이스 온도
- `0x200`: GPS 위도
- `0x201`: GPS 경도
- `0x202`: GPS 속도
- `0x203`: GPS 고도
- `0x204`: GPS 방향

### 채널 데이터 구조
```python
@dataclass
class ChannelData:
    id: str                    # 채널 ID
    devid: str                 # 디바이스 ID
    vin: str                   # 차량 식별 번호
    flags: int                 # 상태 플래그
    device_tick: int           # 디바이스 타임스탬프
    server_data_tick: int      # 서버 데이터 수신 시간
    elapsed_time: int          # 경과 시간 (초)
    recv_count: int            # 수신 패킷 수
    data_received: int         # 수신 데이터 크기
    sample_rate: float         # 샘플링 레이트
    rssi: int                  # 신호 강도
    data: Dict[int, PIDData]   # PID 데이터
```

## 🔧 설정

### 환경변수 설정 (.env 파일)
```bash
# PostgreSQL 데이터베이스 설정
DB_HOST=localhost
DB_PORT=5432
DB_NAME=trackdb
DB_USER=confitech
DB_PASSWORD=conf11

# Flask 설정
SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# 서버 설정
HTTP_PORT=8080
MAX_CHANNELS=100
CHANNEL_TIMEOUT=300

# 로그 설정
LOG_LEVEL=INFO
```

## 📁 디렉토리 구조

```
pyServer/
├── app.py                    # 메인 애플리케이션
├── requirements.txt          # Python 의존성
├── README.md                # 이 파일
├── templates/               # HTML 템플릿
│   └── index.html           # 메인 웹 인터페이스
├── data/                    # 데이터 저장소
├── log/                     # 로그 파일
├── .env                     # 환경변수 파일 (자동 생성)
├── env.example              # 환경변수 예제
├── setup_postgresql.sh      # PostgreSQL 설정 스크립트
├── run.sh                   # 실행 스크립트 (Linux/Mac)
├── run.bat                  # 실행 스크립트 (Windows)
└── teleserver.db            # SQLite 데이터베이스 (폴백용)
```

## 🐛 문제 해결

### 1. 포트 충돌
```bash
# 다른 포트 사용
python app.py --port 9090
```

### 2. 권한 문제
```bash
# 로그 및 데이터 디렉토리 권한 확인
chmod 755 data log
```

### 3. PostgreSQL 연결 오류
```bash
# PostgreSQL 서비스 상태 확인
sudo systemctl status postgresql

# PostgreSQL 재시작
sudo systemctl restart postgresql

# 데이터베이스 연결 테스트
psql -h localhost -U teleserver -d teleserver

# SQLite 폴백 사용 (자동)
# PostgreSQL 연결 실패 시 자동으로 SQLite 사용
```

## 📝 로그

로그는 다음 위치에 저장됩니다:
- `teleserver.log`: 애플리케이션 로그
- `log/YYYYMMDD.txt`: 일별 로그

## 🔒 보안

- 기본 인증: `admin/admin`
- 환경변수 `SECRET_KEY` 설정 권장
- 프로덕션 환경에서는 HTTPS 사용 권장

## 🤝 기여

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 GPL v3.0 라이선스 하에 배포됩니다.

## 👨‍💻 개발자

- 원본: Stanley Huang <stanley@freematics.com.au>
- Flask 버전: [Your Name]

## 🔗 관련 링크

- [Freematics Hub](https://freematics.com/hub)
- [원본 C 버전](../teleserver/)
- [API 문서](https://freematics.com/hub/api) 
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Freematics Hub Server - Flask Version
Developed by Stanley Huang <stanley@freematics.com.au>
Python version by [Your Name]
Distributed under GPL v3.0 license
Visit https://freematics.com/hub for more information
"""

import os
import json
import time
import datetime
import threading
import socket
import struct
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import logging
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import uuid
from UDPServer import UDPServer

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('teleserver.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# CORS 설정
CORS(app)

# 환경변수 로드
load_dotenv()

# UDP 이벤트 상수
EVENT_LOGIN = 1
EVENT_LOGOUT = 2
EVENT_SYNC = 3
EVENT_RECONNECT = 4
EVENT_COMMAND = 5
EVENT_ACK = 6
EVENT_PING = 7

# 기본 설정
DEFAULT_CONFIG = {
    'http_port': int(os.getenv('HTTP_PORT', 8080)),
    'udp_port': int(os.getenv('UDP_PORT', 33000)),
    'max_channels': int(os.getenv('MAX_CHANNELS', 100)),
    'data_dir': os.getenv('DATA_DIR', 'data'),
    'log_dir': os.getenv('LOG_DIR', 'log'),
    'username': os.getenv('USERNAME', 'admin'),
    'password': os.getenv('PASSWORD', 'admin'),
    'cache_size': int(os.getenv('CACHE_SIZE', 1000)),
    'channel_timeout': int(os.getenv('CHANNEL_TIMEOUT', 300)),  # 5분
    'db_host': os.getenv('DB_HOST', 'localhost'),
    'db_port': int(os.getenv('DB_PORT', 5432)),
    'db_name': os.getenv('DB_NAME', 'teleserver'),
    'db_user': os.getenv('DB_USER', 'postgres'),
    'db_password': os.getenv('DB_PASSWORD', 'postgres'),
    'server_key': os.getenv('SERVER_KEY', ''),
    'sync_interval': int(os.getenv('SYNC_INTERVAL', 30))  # 30초
}

# 전역 변수
config = DEFAULT_CONFIG.copy()
channels: Dict[str, 'ChannelData'] = {}
channel_lock = threading.Lock()

@dataclass
class PIDData:
    """PID 데이터 구조"""
    ts: int = 0
    value: str = ""

@dataclass
class ChannelData:
    """채널 데이터 구조"""
    id: str
    devid: str
    vin: str = ""
    flags: int = 0
    device_tick: int = 0
    server_data_tick: int = 0
    server_ping_tick: int = 0
    session_start_tick: int = 0
    elapsed_time: int = 0
    recv_count: int = 0
    tx_count: int = 0
    data_received: int = 0
    sample_rate: float = 0.0
    rssi: int = 0
    device_temp: int = 0
    devflags: int = 0
    cache_size: int = 1000
    cache_read_pos: int = 0
    cache_write_pos: int = 0
    data: Dict[int, PIDData] = None
    cache: List[Dict] = None
    ip_addr: str = ""
    created_at: str = ""
    udp_peer: tuple = None  # (ip, port)
    server_sync_tick: int = 0
    cmd_count: int = 0
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if self.cache is None:
            self.cache = []
        self.created_at = datetime.datetime.now().isoformat()

# SQLAlchemy 설정
Base = declarative_base()

class ChannelModel(Base):
    """PostgreSQL 채널 모델"""
    __tablename__ = 'channels'
    
    id = Column(String, primary_key=True)
    devid = Column(String, unique=True, nullable=False)
    vin = Column(String)
    flags = Column(Integer, default=0)
    device_tick = Column(Integer, default=0)
    server_data_tick = Column(Integer, default=0)
    server_ping_tick = Column(Integer, default=0)
    session_start_tick = Column(Integer, default=0)
    elapsed_time = Column(Integer, default=0)
    recv_count = Column(Integer, default=0)
    tx_count = Column(Integer, default=0)
    data_received = Column(Integer, default=0)
    sample_rate = Column(Float, default=0.0)
    rssi = Column(Integer, default=0)
    device_temp = Column(Integer, default=0)
    devflags = Column(Integer, default=0)
    cache_size = Column(Integer, default=1000)
    cache_read_pos = Column(Integer, default=0)
    cache_write_pos = Column(Integer, default=0)
    ip_addr = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

class PIDDataModel(Base):
    """PostgreSQL PID 데이터 모델"""
    __tablename__ = 'pid_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(String)
    pid = Column(Integer)
    ts = Column(Integer)
    value = Column(Text)
    created_at = Column(DateTime)

class CacheDataModel(Base):
    """PostgreSQL 캐시 데이터 모델"""
    __tablename__ = 'cache_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(String)
    ts = Column(Integer)
    pid = Column(Integer)
    data = Column(Text)
    created_at = Column(DateTime)

class Database:
    """PostgreSQL 데이터베이스 관리"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self.init_db()
    
    def init_db(self):
        """데이터베이스 초기화"""
        try:
            # PostgreSQL 연결 문자열 생성
            db_url = f"postgresql://{config['db_user']}:{config['db_password']}@{config['db_host']}:{config['db_port']}/{config['db_name']}"
            
            # 엔진 생성
            self.engine = create_engine(db_url, echo=False)
            
            # 테이블 생성
            Base.metadata.create_all(bind=self.engine)
            
            # 세션 팩토리 생성
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
            logger.info("PostgreSQL 데이터베이스 연결 성공")
            
        except Exception as e:
            logger.error(f"PostgreSQL 데이터베이스 연결 실패: {e}")
    
    def save_channel(self, channel: ChannelData):
        """채널 데이터 저장"""
        self._save_channel_postgresql(channel)
    
    def _save_channel_postgresql(self, channel: ChannelData):
        """PostgreSQL에 채널 데이터 저장"""
        try:
            with self.SessionLocal() as session:
                # 기존 채널 확인
                existing = session.query(ChannelModel).filter(ChannelModel.id == channel.id).first()
                
                if existing:
                    # 기존 데이터 업데이트
                    existing.devid = channel.devid
                    existing.vin = channel.vin
                    existing.flags = channel.flags
                    existing.device_tick = channel.device_tick
                    existing.server_data_tick = channel.server_data_tick
                    existing.server_ping_tick = channel.server_ping_tick
                    existing.session_start_tick = channel.session_start_tick
                    existing.elapsed_time = channel.elapsed_time
                    existing.recv_count = channel.recv_count
                    existing.tx_count = channel.tx_count
                    existing.data_received = channel.data_received
                    existing.sample_rate = channel.sample_rate
                    existing.rssi = channel.rssi
                    existing.device_temp = channel.device_temp
                    existing.devflags = channel.devflags
                    existing.cache_size = channel.cache_size
                    existing.cache_read_pos = channel.cache_read_pos
                    existing.cache_write_pos = channel.cache_write_pos
                    existing.ip_addr = channel.ip_addr
                    existing.updated_at = datetime.datetime.now()
                else:
                    # 새 채널 생성
                    new_channel = ChannelModel(
                        id=channel.id,
                        devid=channel.devid,
                        vin=channel.vin,
                        flags=channel.flags,
                        device_tick=channel.device_tick,
                        server_data_tick=channel.server_data_tick,
                        server_ping_tick=channel.server_ping_tick,
                        session_start_tick=channel.session_start_tick,
                        elapsed_time=channel.elapsed_time,
                        recv_count=channel.recv_count,
                        tx_count=channel.tx_count,
                        data_received=channel.data_received,
                        sample_rate=channel.sample_rate,
                        rssi=channel.rssi,
                        device_temp=channel.device_temp,
                        devflags=channel.devflags,
                        cache_size=channel.cache_size,
                        cache_read_pos=channel.cache_read_pos,
                        cache_write_pos=channel.cache_write_pos,
                        ip_addr=channel.ip_addr,
                        created_at=datetime.datetime.fromisoformat(channel.created_at),
                        updated_at=datetime.datetime.now()
                    )
                    session.add(new_channel)
                
                session.commit()
        except Exception as e:
            logger.error(f"PostgreSQL 채널 저장 실패: {e}")
        
    def load_channels(self) -> Dict[str, ChannelData]:
        """모든 채널 데이터 로드"""
        return self._load_channels_postgresql()
    
    def _load_channels_postgresql(self) -> Dict[str, ChannelData]:
        """PostgreSQL에서 채널 데이터 로드"""
        channels = {}
        try:
            with self.SessionLocal() as session:
                db_channels = session.query(ChannelModel).all()
                for db_channel in db_channels:
                    channel = ChannelData(
                        id=db_channel.id,
                        devid=db_channel.devid,
                        vin=db_channel.vin or "",
                        flags=db_channel.flags,
                        device_tick=db_channel.device_tick,
                        server_data_tick=db_channel.server_data_tick,
                        server_ping_tick=db_channel.server_ping_tick,
                        session_start_tick=db_channel.session_start_tick,
                        elapsed_time=db_channel.elapsed_time,
                        recv_count=db_channel.recv_count,
                        tx_count=db_channel.tx_count,
                        data_received=db_channel.data_received,
                        sample_rate=db_channel.sample_rate,
                        rssi=db_channel.rssi,
                        device_temp=db_channel.device_temp,
                        devflags=db_channel.devflags,
                        cache_size=db_channel.cache_size,
                        cache_read_pos=db_channel.cache_read_pos,
                        cache_write_pos=db_channel.cache_write_pos,
                        ip_addr=db_channel.ip_addr or "",
                        created_at=db_channel.created_at.isoformat() if db_channel.created_at else datetime.datetime.now().isoformat()
                    )
                    channels[channel.id] = channel
        except Exception as e:
            logger.error(f"PostgreSQL 채널 로드 실패: {e}")
        return channels
    
# 데이터베이스 인스턴스
db = Database()

# UDP 서버 인스턴스
udp_server = UDPServer(config['udp_port'])

def hex_to_int(hex_str: str) -> int:
    """16진수 문자열을 정수로 변환"""
    try:
        return int(hex_str, 16)
    except ValueError:
        return -1

def is_hex(char: str) -> bool:
    """16진수 문자인지 확인"""
    return char in '0123456789ABCDEFabcdef'

def is_valid_devid(devid: str) -> bool:
    """유효한 디바이스 ID인지 확인"""
    if not devid or len(devid) < 4:
        return False
    return all(c.isalnum() for c in devid)

def find_channel_by_devid(devid: str) -> Optional[ChannelData]:
    """디바이스 ID로 채널 찾기"""
    with channel_lock:
        for channel in channels.values():
            if channel.devid == devid:
                return channel
    return None

def find_empty_channel() -> Optional[ChannelData]:
    """빈 채널 찾기"""
    with channel_lock:
        if len(channels) >= config['max_channels']:
            return None
        
        channel_id = str(uuid.uuid4())
        return ChannelData(id=channel_id, devid="")

def device_login(channel: ChannelData):
    """디바이스 로그인 처리"""
    channel.flags |= 1  # FLAG_RUNNING
    channel.flags &= ~2  # FLAG_SLEEPING 제거
    channel.proxy_tick = 0
    # 통계 초기화
    channel.data_received = 0
    channel.recv_count = 0
    channel.tx_count = 0
    channel.elapsed_time = 0
    db.save_channel(channel)
    logger.info(f"디바이스 로그인: {channel.devid}")

def device_logout(channel: ChannelData):
    """디바이스 로그아웃 처리"""
    current_time = int(time.time() * 1000)
    channel.flags &= ~1  # FLAG_RUNNING 제거
    channel.server_ping_tick = current_time
    db.save_channel(channel)
    logger.info(f"디바이스 로그아웃: {channel.devid}")

def assign_channel(devid: str) -> Optional[ChannelData]:
    """채널 할당"""
    if not is_valid_devid(devid):
        logger.error(f"Invalid device ID: {devid}")
        return None
    
    # 기존 채널 확인
    channel = find_channel_by_devid(devid)
    if channel:
        return channel
    
    # 새 채널 생성
    channel = find_empty_channel()
    if not channel:
        logger.error("No available channels")
        return None
    
    channel.devid = devid
    channel.session_start_tick = int(time.time() * 1000)
    channel.server_data_tick = channel.session_start_tick
    
    with channel_lock:
        channels[channel.id] = channel
    
    db.save_channel(channel)
    logger.info(f"New channel assigned: {devid} -> {channel.id}")
    return channel

def process_payload(payload: str, channel: ChannelData, event_id: int = 0) -> int:
    """페이로드 처리"""
    current_time = int(time.time() * 1000)
    
    if event_id == 0 and not (channel.flags & 1):  # FLAG_RUNNING
        channel.flags |= 1
        channel.session_start_tick = current_time
    
    # 페이로드 파싱
    parts = payload.split(',')
    count = 0
    timestamp = 0
    
    for part in parts:
        if ':' not in part:
            continue
        
        pid_str, value = part.split(':', 1)
        pid = hex_to_int(pid_str)
        
        if pid == -1:
            continue
        
        if pid == 0:  # 타임스탬프
            timestamp = int(value)
            continue
        
        if timestamp == 0:
            continue
        
        # 데이터 저장
        channel.data[pid] = PIDData(ts=timestamp, value=value)
        
        # 특별한 PID 처리
        if pid == 0x100:  # RSSI
            channel.rssi = int(value)
        elif pid == 0x101:  # DEVICE_TEMP
            channel.device_temp = int(value)
        
        count += 1
    
    if timestamp == 0:
        timestamp = channel.device_tick
    
    # 통계 업데이트
    if channel.device_tick > 0:
        interval = timestamp - channel.device_tick
        if interval > 100:
            channel.sample_rate = (count * 60000) / interval
    
    channel.device_tick = timestamp
    channel.server_data_tick = current_time
    channel.elapsed_time = int((current_time - channel.session_start_tick) / 1000)
    channel.recv_count += 1
    channel.data_received += len(payload)
    
    # 데이터베이스에 저장
    db.save_channel(channel)
    
    logger.info(f"[{channel.id}] #{channel.recv_count} {len(payload)} bytes | Samples:{count} | Device Tick:{timestamp}")
    return count

def check_channels():
    """채널 상태 확인 및 정리"""
    current_time = int(time.time() * 1000)
    timeout_ms = config['channel_timeout'] * 1000
    
    with channel_lock:
        channels_to_remove = []
        for channel_id, channel in channels.items():
            if channel.flags & 1:  # FLAG_RUNNING
                if current_time - channel.server_data_tick > timeout_ms:
                    channel.flags &= ~1  # FLAG_RUNNING 제거
                    logger.info(f"Channel {channel.devid} timed out")
        
        # 오래된 채널 제거 (선택적)
        # for channel_id, channel in channels.items():
        #     if current_time - channel.server_ping_tick > timeout_ms * 2:
        #         channels_to_remove.append(channel_id)
        
        # for channel_id in channels_to_remove:
        #     del channels[channel_id]

# API 라우트들

@app.route('/')
def index():
    """메인 페이지"""
    return render_template('index.html')

@app.route('/api/test')
def api_test():
    """테스트 API"""
    current_time = datetime.datetime.now()
    return jsonify({
        'date': current_time.strftime('%y%m%d'),
        'time': current_time.strftime('%H%M%S'),
        'tick': int(time.time() * 1000)
    })

@app.route('/api/notify', methods=['GET', 'POST'])
def api_notify():
    """디바이스 알림 처리"""
    if request.method == 'GET':
        vin = request.args.get('VIN', '')
        event = int(request.args.get('EV', 0))
        devflags = int(request.args.get('DF', 0))
        rssi = int(request.args.get('SSI', 0))
        devid = request.args.get('id', '')
    else:
        data = request.get_json() or {}
        vin = data.get('VIN', '')
        event = data.get('EV', 0)
        devflags = data.get('DF', 0)
        rssi = data.get('SSI', 0)
        devid = data.get('id', '')
    
    if not devid or not is_valid_devid(devid):
        return jsonify({'result': 'failed', 'error': 'Invalid ID'}), 403
    
    current_time = int(time.time() * 1000)
    
    if event == 1:  # EVENT_LOGIN
        channel = assign_channel(devid)
        if not channel:
            return jsonify({'result': 'failed', 'error': 'Channel assignment failed'}), 403
        
        if vin and len(vin) == 17:
            channel.vin = vin
        channel.devflags = devflags
        channel.rssi = rssi
        channel.session_start_tick = current_time
        channel.server_data_tick = current_time
        channel.flags |= 1  # FLAG_RUNNING
        
        db.save_channel(channel)
        logger.info(f"Device login: {devid}")
        
        return jsonify({'id': channel.id, 'result': 'done'})
    
    elif event == 2:  # EVENT_LOGOUT
        channel = find_channel_by_devid(devid)
        if channel:
            channel.flags &= ~1  # FLAG_RUNNING 제거
            channel.server_ping_tick = current_time
            db.save_channel(channel)
            logger.info(f"Device logout: {devid}")
        
        return jsonify({'result': 'done'})
    
    elif event == 3:  # EVENT_SYNC
        return jsonify({'result': 'done'})
    
    return jsonify({'result': 'failed', 'error': 'Invalid request'}), 400

@app.route('/api/post', methods=['GET', 'POST'])
def api_post():
    """데이터 포스트 처리"""
    devid = request.args.get('id', '')
    if not devid:
        return jsonify({'result': 'failed', 'error': 'Missing device ID'}), 403
    
    channel = find_channel_by_devid(devid)
    if not channel:
        return jsonify({'result': 'failed', 'error': 'Channel not found'}), 403
    
    if request.method == 'GET':
        # GET 요청 처리 (GPS 데이터 등)
        lat = request.args.get('lat', '')
        lon = request.args.get('lon', '')
        ts = int(request.args.get('timestamp', 0))
        alt = request.args.get('altitude', '')
        speed = request.args.get('speed', '')
        heading = request.args.get('heading', '')
        
        if ts > 0:
            channel.device_tick = ts
            if lat:
                channel.data[0x200] = PIDData(ts=ts, value=lat)  # PID_GPS_LATITUDE
            if lon:
                channel.data[0x201] = PIDData(ts=ts, value=lon)  # PID_GPS_LONGITUDE
            if speed:
                channel.data[0x202] = PIDData(ts=ts, value=speed)  # PID_GPS_SPEED
            if alt:
                channel.data[0x203] = PIDData(ts=ts, value=alt)  # PID_GPS_ALTITUDE
            if heading:
                channel.data[0x204] = PIDData(ts=ts, value=heading)  # PID_GPS_HEADING
        
        logger.info(f"GET from {request.remote_addr} | LAT:{lat} LON:{lon} ALT:{alt}")
        return jsonify({'result': 'OK'})
    
    else:
        # POST 요청 처리
        payload = request.get_data(as_text=True)
        if not payload:
            return jsonify({'result': 'failed', 'error': 'No payload'}), 400
        
        count = process_payload(payload, channel, 0)
        channel.ip_addr = request.remote_addr
        
        logger.info(f"POST from {request.remote_addr} | {len(payload)} bytes")
        return jsonify({'result': f'OK {count}'})

@app.route('/api/channels')
def api_channels():
    """채널 목록 조회"""
    cmd = request.args.get('cmd', '')
    channel_id = request.args.get('id', '')
    devid = request.args.get('devid', '')
    extend = request.args.get('extend', '0') == '1'
    data = request.args.get('data', '0') == '1'
    
    if cmd == 'clear' and channel_id:
        with channel_lock:
            if channel_id in channels:
                del channels[channel_id]
                logger.info(f"Channel {channel_id} removed")
    
    current_time = int(time.time() * 1000)
    channel_list = []
    
    with channel_lock:
        for channel in channels.values():
            if devid and channel.devid != devid:
                continue
            
            age_data = current_time - channel.server_data_tick if channel.server_data_tick > 0 else 0
            age_ping = current_time - channel.server_ping_tick if channel.server_ping_tick > 0 else 0
            
            channel_info = {
                'id': channel.id,
                'devid': channel.devid,
                'recv': channel.data_received,
                'rate': int(channel.sample_rate),
                'tick': channel.server_data_tick,
                'devtick': channel.device_tick,
                'elapsed': channel.elapsed_time,
                'age': {
                    'data': age_data,
                    'ping': age_ping
                },
                'rssi': channel.rssi,
                'flags': channel.devflags,
                'parked': 0 if (channel.flags & 1) else 1
            }
            
            if extend:
                if channel.vin:
                    channel_info['vin'] = channel.vin
                if channel.ip_addr:
                    channel_info['ip'] = channel.ip_addr
            
            if data:
                channel_info['data'] = []
                for pid, pid_data in channel.data.items():
                    if pid_data.ts > 0:
                        age = age_data + (channel.device_tick - pid_data.ts) if channel.device_tick >= pid_data.ts else 0
                        channel_info['data'].append([pid, pid_data.value, age])
            
            channel_list.append(channel_info)
    
    if devid:
        return jsonify(channel_list[0] if channel_list else {})
    else:
        return jsonify({'channels': channel_list})

@app.route('/api/get')
def api_get():
    """채널 데이터 조회"""
    devid = request.args.get('id', '')
    if not devid:
        return jsonify({'result': 'failed', 'error': 'Missing device ID'}), 403
    
    channel = find_channel_by_devid(devid)
    if not channel:
        return jsonify({'result': 'failed', 'error': 'Channel not found'}), 403
    
    current_time = int(time.time() * 1000)
    age_data = current_time - channel.server_data_tick if channel.server_data_tick > 0 else 0
    age_ping = current_time - channel.server_ping_tick if channel.server_ping_tick > 0 else 0
    
    stats = {
        'tick': channel.server_data_tick,
        'devtick': channel.device_tick,
        'elapsed': channel.elapsed_time,
        'age': {
            'data': age_data,
            'ping': age_ping
        },
        'rssi': channel.rssi,
        'flags': channel.devflags,
        'parked': 0 if (channel.flags & 1) else 1
    }
    
    data = []
    for pid, pid_data in channel.data.items():
        if pid_data.ts > 0:
            age = age_data + (channel.device_tick - pid_data.ts) if channel.device_tick >= pid_data.ts else 0
            data.append([pid, pid_data.value, age])
    
    return jsonify({
        'stats': stats,
        'data': data
    })

@app.route('/api/push', methods=['GET', 'POST'])
def api_push():
    """데이터 푸시 처리"""
    devid = request.args.get('id', '')
    if not devid:
        return jsonify({'result': 'failed', 'error': 'Missing device ID'}), 403
    
    channel = find_channel_by_devid(devid)
    if not channel:
        return jsonify({'result': 'failed', 'error': 'Channel not found'}), 403
    
    current_time = int(time.time() * 1000)
    channel.device_tick = int(request.args.get('ts', 0))
    count = 0
    
    # URL 파라미터에서 PID 데이터 처리
    for key, value in request.args.items():
        if key.isdigit() or (len(key) == 4 and all(c in '0123456789ABCDEFabcdef' for c in key)):
            pid = hex_to_int(key)
            if pid > 0:
                channel.data[pid] = PIDData(ts=channel.device_tick, value=value)
                count += 1
    
    channel.server_data_tick = current_time
    channel.elapsed_time = int((current_time - channel.session_start_tick) / 1000)
    channel.recv_count += 1
    
    db.save_channel(channel)
    
    logger.info(f"PUSH from {request.remote_addr} | {count} PIDs")
    return jsonify({'result': count})

@app.route('/api/command', methods=['GET', 'POST'])
def api_command():
    """명령 처리"""
    devid = request.args.get('id', '')
    if not devid:
        return jsonify({'result': 'failed', 'error': 'Missing device ID'}), 403
    
    channel = find_channel_by_devid(devid)
    if not channel:
        return jsonify({'result': 'failed', 'error': 'Channel not found'}), 403
    
    cmd = request.args.get('cmd', '')
    token = request.args.get('token', '0')
    
    if not cmd and not token:
        return jsonify({'result': 'failed', 'error': 'Invalid request'}), 400
    
    channel.server_data_tick = int(time.time() * 1000)
    
    if cmd:
        # UDP 명령 전송
        if channel.udp_peer:
            token = udp_server.send_command(channel, cmd)
            if token:
                return jsonify({'result': 'pending', 'token': token})
            else:
                return jsonify({'result': 'failed', 'error': 'Command unsent'})
        else:
            return jsonify({'result': 'failed', 'error': 'Device not connected via UDP'})
    else:
        # 토큰 상태 확인 (구현 필요)
        return jsonify({'result': 'failed', 'error': 'Invalid token'})

def background_tasks():
    """백그라운드 작업"""
    while True:
        try:
            check_channels()
            time.sleep(10)  # 10초마다 체크
        except Exception as e:
            logger.error(f"Background task error: {e}")

if __name__ == '__main__':
    # 디렉토리 생성
    os.makedirs(config['data_dir'], exist_ok=True)
    os.makedirs(config['log_dir'], exist_ok=True)
    
    # 기존 채널 로드
    channels.update(db.load_channels())
    logger.info(f"Loaded {len(channels)} channels from database")
    
    # UDP 서버 시작
    if not udp_server.start():
        logger.warning("UDP 서버 시작 실패, HTTP 서버만 실행됩니다.")
    
    # 백그라운드 작업 시작
    background_thread = threading.Thread(target=background_tasks, daemon=True)
    background_thread.start()
    
    # Flask 서버 시작
    logger.info(f"Starting Flask TeleServer on port {config['http_port']}")
    try:
        app.run(
            host='0.0.0.0',
            port=config['http_port'],
            debug=False,
            threaded=True
        )
    except KeyboardInterrupt:
        logger.info("서버 종료 중...")
        udp_server.stop()
        logger.info("서버가 종료되었습니다.") 
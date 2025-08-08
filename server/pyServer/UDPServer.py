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
#from werkzeug.security import check_password_hash, generate_password_hash
#from werkzeug.utils import secure_filename
#import psycopg2
#from psycopg2.extras import RealDictCursor
#from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)

class UDPServer:
    """UDP 서버 클래스"""
    
    def __init__(self, port=33000):
        self.port = port
        self.socket = None
        self.running = False
        self.thread = None
    
    def start(self, port=33000):
        """UDP 서버 시작"""
        self.port = port
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind(('0.0.0.0', self.port))
            self.socket.settimeout(1.0)  # 1초 타임아웃
            self.running = True
            self.thread = threading.Thread(target=self._listen, daemon=True)
            self.thread.start()
            logger.info(f"UDP 서버가 포트 {self.port}에서 시작되었습니다.")
            return True
        except Exception as e:
            logger.error(f"UDP 서버 시작 실패: {e}")
            return False
    
    def stop(self):
        """UDP 서버 중지"""
        self.running = False
        if self.socket:
            self.socket.close()
        logger.info("UDP 서버가 중지되었습니다.")
    
    def _listen(self):
        """UDP 메시지 수신 루프"""
        while self.running:
            try:
                data, addr = self.socket.recvfrom(4096)
                self._handle_message(data.decode('utf-8', errors='ignore'), addr)
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"UDP 메시지 처리 오류: {e}")
    
    def _handle_message(self, message, addr):
        """UDP 메시지 처리"""
        try:
            logger.info(f"UDP 메시지 수신: {len(message)} bytes from {addr[0]}")
            
            # 체크섬 검증
            if not self._verify_checksum(message):
                logger.warning(f"체크섬 불일치: {message}")
                return
            
            # 메시지 파싱
            parts = message.split('#', 1)
            if len(parts) != 2:
                logger.warning(f"잘못된 메시지 형식: {message}")
                return
            
            device_id = parts[0]
            data = parts[1]
            
            # 채널 찾기
            channel = find_channel_by_deviceID(device_id)
            if not channel:
                # 새 채널 생성
                channel = assign_channel(device_id)
                if not channel:
                    logger.error(f"채널 할당 실패: {device_id}")
                    return
            
            # 이벤트 파싱
            event_id = 0
            device_tick = 0
            token = 0
            msg = ""
            vin = ""
            devflags = 0
            rssi = 0
            key = ""
            
            if "EV=" in data:
                # 이벤트 메시지
                params = data.split(',')
                for param in params:
                    if param.startswith('EV='):
                        event_id = int(param[3:])
                    elif param.startswith('TS='):
                        device_tick = int(param[3:])
                    elif param.startswith('TK='):
                        token = int(param[3:])
                    elif param.startswith('MSG='):
                        msg = param[4:]
                    elif param.startswith('VIN='):
                        vin = param[4:]
                    elif param.startswith('DF='):
                        devflags = int(param[3:])
                    elif param.startswith('SSI='):
                        rssi = int(param[4:])
                    elif param.startswith('SK='):
                        key = param[3:]
                
                # 이벤트 처리
                self._handle_event(channel, event_id, device_tick, token, msg, vin, devflags, rssi, key, addr)
            else:
                # 데이터 메시지
                self._handle_data(channel, data, addr)
                
        except Exception as e:
            logger.error(f"UDP 메시지 처리 오류: {e}")
    
    def _handle_event(self, channel, event_id, device_tick, token, msg, vin, devflags, rssi, key, addr):
        """이벤트 처리"""
        current_time = int(time.time() * 1000)
        
        if event_id == EVENT_LOGIN:
            # 로그인 이벤트
            if vin and len(vin) == 17:
                channel.vin = vin
            channel.rssi = rssi
            channel.devflags = devflags
            channel.udp_peer = addr
            
            # 서버 키 검증
            if config['server_key'] and key != config['server_key']:
                logger.warning(f"서버 키 불일치: {key}")
                return
            
            # 로그인 처리
            if not (channel.flags & 1) or current_time - channel.server_data_tick > 60000:  # 1분
                device_login(channel)
                channel.server_data_tick = current_time
                channel.session_start_tick = current_time
            else:
                logger.info(f"디바이스 재로그인: {channel.devid}")
            
            channel.device_tick = device_tick
            # 캐시 초기화
            channel.cache_read_pos = 0
            channel.cache_write_pos = 0
            channel.data.clear()
            
        elif event_id == EVENT_ACK:
            # 명령 응답 처리
            if msg and token:
                # 명령 응답 처리 로직 (구현 필요)
                logger.info(f"명령 응답: {token} - {msg}")
        
        # 응답 전송
        self._send_response(channel, event_id, addr)
    
    def _handle_data(self, channel, data, addr):
        """데이터 메시지 처리"""
        current_time = int(time.time() * 1000)
        
        # 데이터 처리
        count = process_payload(data, channel, 0)
        channel.ip_addr = addr[0]
        
        # 동기화 필요 여부 확인
        if current_time - channel.server_sync_tick >= config['sync_interval'] * 1000:
            channel.server_sync_tick = current_time
            self._send_response(channel, EVENT_SYNC, addr)
        else:
            # 응답 없음
            pass
    
    def _send_response(self, channel, event_id, addr):
        """UDP 응답 전송"""
        try:
            response = f"{channel.id:X}#EV={event_id},RX={channel.recv_count},TX={channel.tx_count + 1}"
            response = self._add_checksum(response)
            
            self.socket.sendto(response.encode('utf-8'), addr)
            logger.info(f"UDP 응답 전송: {response}")
            
            # 통계 업데이트
            channel.tx_count += 1
            
            # 이벤트별 처리
            if event_id == EVENT_LOGOUT:
                device_logout(channel)
            elif event_id == EVENT_PING:
                logger.info("Ping 수신")
                channel.server_ping_tick = int(time.time() * 1000)
                channel.flags &= ~1  # FLAG_RUNNING 제거
                channel.flags |= 2   # FLAG_SLEEPING 추가
            elif event_id == EVENT_RECONNECT:
                logger.info(f"디바이스 재연결: {channel.devid}")
                
        except Exception as e:
            logger.error(f"UDP 응답 전송 실패: {e}")
    
    def _verify_checksum(self, data):
        """체크섬 검증"""
        if '*' not in data:
            return False
        
        parts = data.rsplit('*', 1)
        if len(parts) != 2:
            return False
        
        message = parts[0]
        checksum = parts[1]
        
        # 체크섬 계산
        calculated_sum = sum(ord(c) for c in message) & 0xFF
        received_sum = int(checksum, 16)
        
        return calculated_sum == received_sum
    
    def _add_checksum(self, data):
        """체크섬 추가"""
        checksum = sum(ord(c) for c in data) & 0xFF
        return f"{data}*{checksum:X}"
    
    def send_command(self, channel, command, token=None):
        """명령 전송"""
        if not channel.udp_peer:
            logger.error("UDP 피어 정보가 없습니다.")
            return False
        
        if token is None:
            token = channel.cmd_count + 1
            channel.cmd_count += 1
        
        try:
            message = f"{channel.id:X}#EV={EVENT_COMMAND},TK={token},CMD={command}"
            message = self._add_checksum(message)
            
            self.socket.sendto(message.encode('utf-8'), channel.udp_peer)
            logger.info(f"명령 전송: {command} (토큰: {token})")
            
            # 명령 상태 업데이트
            channel.server_data_tick = int(time.time() * 1000)
            
            return token
        except Exception as e:
            logger.error(f"명령 전송 실패: {e}")
            return False

# exchange/utility/api_key_manager.py
"""
API 키 관리 유틸리티
데이터베이스에서 API 키를 조회하고 기존 exchange 모듈과 연동
"""

import os
from typing import Dict, Optional, Tuple
from exchange.database import db
from exchange.utility.setting import settings
import traceback
from loguru import logger


class APIKeyManager:
    """API 키 관리 클래스"""
    
    def __init__(self):
        self._cache = {}  # API 키 캐시
        self._cache_timeout = 300  # 5분 캐시
        
    def get_api_credentials(self, exchange: str, kis_number: Optional[int] = None) -> Dict[str, str]:
        """
        거래소별 API 인증 정보 조회
        
        Args:
            exchange: 거래소 이름 (UPBIT, BINANCE, BYBIT, BITGET, OKX, KIS)
            kis_number: KIS 거래소의 경우 계좌 번호 (1-10)
            
        Returns:
            Dict containing API credentials
        """
        try:
            # 1. 데이터베이스에서 활성화된 API 키 조회 시도
            db_credentials = self._get_credentials_from_db(exchange, kis_number)
            if db_credentials:
                logger.info(f"데이터베이스에서 {exchange} API 키 로드됨")
                return db_credentials
            
            # 2. 데이터베이스에 없으면 환경변수에서 조회 (기존 방식 호환)
            env_credentials = self._get_credentials_from_env(exchange, kis_number)
            if env_credentials:
                logger.info(f"환경변수에서 {exchange} API 키 로드됨")
                return env_credentials
            
            # 3. 둘 다 없으면 빈 딕셔너리 반환
            logger.warning(f"{exchange} API 키를 찾을 수 없습니다")
            return {}
            
        except Exception as e:
            logger.error(f"API 키 조회 중 오류 발생: {exchange} - {str(e)}")
            logger.error(traceback.format_exc())
            return {}
    
    def _get_credentials_from_db(self, exchange: str, kis_number: Optional[int] = None) -> Optional[Dict[str, str]]:
        """데이터베이스에서 API 인증 정보 조회"""
        try:
            # KIS의 경우 계좌 번호별로 구분하여 조회
            if exchange == "KIS" and kis_number:
                query = """
                SELECT api_key, secret_key, passphrase, account_number, account_code 
                FROM api_keys 
                WHERE exchange = ? AND account_number LIKE ? AND is_active = 1 
                ORDER BY created_at DESC LIMIT 1
                """
                # kis_number를 기반으로 계좌 번호 패턴 생성 (예: kis_number=1 -> KIS1, kis_number=2 -> KIS2)
                account_pattern = f"KIS{kis_number}%"
                result = db.fetch_one(query, (exchange, account_pattern))
            else:
                query = """
                SELECT api_key, secret_key, passphrase, account_number, account_code 
                FROM api_keys 
                WHERE exchange = ? AND is_active = 1 
                ORDER BY created_at DESC LIMIT 1
                """
                result = db.fetch_one(query, (exchange,))
            
            if result:
                credentials = {
                    'api_key': result[0],
                    'secret_key': result[1],
                }
                
                # 선택적 필드들 추가
                if result[2]:  # passphrase
                    credentials['passphrase'] = result[2]
                if result[3]:  # account_number
                    credentials['account_number'] = result[3]
                if result[4]:  # account_code
                    credentials['account_code'] = result[4]
                
                return credentials
            
            return None
            
        except Exception as e:
            logger.error(f"데이터베이스 API 키 조회 오류: {str(e)}")
            return None
    
    def _get_credentials_from_env(self, exchange: str, kis_number: Optional[int] = None) -> Optional[Dict[str, str]]:
        """환경변수에서 API 인증 정보 조회 (기존 방식 호환)"""
        try:
            credentials = {}
            
            if exchange == "UPBIT":
                if settings.UPBIT_KEY and settings.UPBIT_SECRET:
                    credentials = {
                        'api_key': settings.UPBIT_KEY,
                        'secret_key': settings.UPBIT_SECRET
                    }
                    
            elif exchange == "BINANCE":
                if settings.BINANCE_KEY and settings.BINANCE_SECRET:
                    credentials = {
                        'api_key': settings.BINANCE_KEY,
                        'secret_key': settings.BINANCE_SECRET
                    }
                    
            elif exchange == "BYBIT":
                if settings.BYBIT_KEY and settings.BYBIT_SECRET:
                    credentials = {
                        'api_key': settings.BYBIT_KEY,
                        'secret_key': settings.BYBIT_SECRET
                    }
                    
            elif exchange == "BITGET":
                # 데모 모드 확인
                if settings.BITGET_DEMO_MODE and settings.BITGET_DEMO_MODE.lower() == "true":
                    if settings.BITGET_DEMO_KEY and settings.BITGET_DEMO_SECRET:
                        credentials = {
                            'api_key': settings.BITGET_DEMO_KEY,
                            'secret_key': settings.BITGET_DEMO_SECRET,
                            'sandbox': True
                        }
                        if settings.BITGET_DEMO_PASSPHRASE:
                            credentials['passphrase'] = settings.BITGET_DEMO_PASSPHRASE
                else:
                    if settings.BITGET_KEY and settings.BITGET_SECRET:
                        credentials = {
                            'api_key': settings.BITGET_KEY,
                            'secret_key': settings.BITGET_SECRET
                        }
                        if settings.BITGET_PASSPHRASE:
                            credentials['passphrase'] = settings.BITGET_PASSPHRASE
                            
            elif exchange == "OKX":
                if settings.OKX_KEY and settings.OKX_SECRET and settings.OKX_PASSPHRASE:
                    credentials = {
                        'api_key': settings.OKX_KEY,
                        'secret_key': settings.OKX_SECRET,
                        'passphrase': settings.OKX_PASSPHRASE
                    }
                    
            elif exchange == "KIS" and kis_number:
                # KIS 계좌별 환경변수 조회
                kis_key_attr = f"KIS{kis_number}_KEY"
                kis_secret_attr = f"KIS{kis_number}_SECRET"
                kis_account_attr = f"KIS{kis_number}_ACCOUNT_NUMBER"
                kis_code_attr = f"KIS{kis_number}_ACCOUNT_CODE"
                
                kis_key = getattr(settings, kis_key_attr, None)
                kis_secret = getattr(settings, kis_secret_attr, None)
                kis_account = getattr(settings, kis_account_attr, None)
                kis_code = getattr(settings, kis_code_attr, None)
                
                if kis_key and kis_secret:
                    credentials = {
                        'api_key': kis_key,
                        'secret_key': kis_secret
                    }
                    if kis_account:
                        credentials['account_number'] = kis_account
                    if kis_code:
                        credentials['account_code'] = kis_code
            
            return credentials if credentials else None
            
        except Exception as e:
            logger.error(f"환경변수 API 키 조회 오류: {str(e)}")
            return None
    
    def add_api_key(self, exchange: str, api_key: str, secret_key: str, 
                   passphrase: str = "", account_number: str = "", account_code: str = "") -> bool:
        """데이터베이스에 새로운 API 키 추가"""
        try:
            query = """
            INSERT INTO api_keys (exchange, api_key, secret_key, passphrase, account_number, account_code)
            VALUES (?, ?, ?, ?, ?, ?)
            """
            db.excute(query, (exchange, api_key, secret_key, passphrase, account_number, account_code))
            logger.info(f"{exchange} API 키가 성공적으로 추가되었습니다")
            return True
        except Exception as e:
            logger.error(f"API 키 추가 중 오류: {str(e)}")
            return False
    
    def update_api_key(self, key_id: int, exchange: str, api_key: str, secret_key: str,
                      passphrase: str = "", account_number: str = "", account_code: str = "") -> bool:
        """데이터베이스의 API 키 업데이트"""
        try:
            query = """
            UPDATE api_keys 
            SET exchange = ?, api_key = ?, secret_key = ?, passphrase = ?, 
                account_number = ?, account_code = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """
            db.excute(query, (exchange, api_key, secret_key, passphrase, account_number, account_code, key_id))
            logger.info(f"API 키 ID {key_id}가 성공적으로 업데이트되었습니다")
            return True
        except Exception as e:
            logger.error(f"API 키 업데이트 중 오류: {str(e)}")
            return False
    
    def delete_api_key(self, key_id: int) -> bool:
        """데이터베이스에서 API 키 삭제"""
        try:
            query = "DELETE FROM api_keys WHERE id = ?"
            db.excute(query, (key_id,))
            logger.info(f"API 키 ID {key_id}가 성공적으로 삭제되었습니다")
            return True
        except Exception as e:
            logger.error(f"API 키 삭제 중 오류: {str(e)}")
            return False
    
    def toggle_api_key(self, key_id: int) -> bool:
        """API 키 활성화/비활성화 토글"""
        try:
            query = "UPDATE api_keys SET is_active = NOT is_active WHERE id = ?"
            db.excute(query, (key_id,))
            logger.info(f"API 키 ID {key_id}의 활성화 상태가 변경되었습니다")
            return True
        except Exception as e:
            logger.error(f"API 키 상태 변경 중 오류: {str(e)}")
            return False
    
    def get_all_api_keys(self) -> list:
        """모든 API 키 목록 조회 (관리자용)"""
        try:
            query = "SELECT * FROM api_keys ORDER BY exchange, created_at DESC"
            return db.fetch_all(query, {})
        except Exception as e:
            logger.error(f"API 키 목록 조회 중 오류: {str(e)}")
            return []


# 전역 인스턴스
api_key_manager = APIKeyManager()


def get_exchange_credentials(exchange: str, kis_number: Optional[int] = None) -> Dict[str, str]:
    """
    거래소별 API 인증 정보 조회 (외부 인터페이스)
    
    이 함수를 통해 기존 exchange 모듈들이 API 키를 조회할 수 있습니다.
    """
    return api_key_manager.get_api_credentials(exchange, kis_number)

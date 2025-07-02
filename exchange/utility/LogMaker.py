import sys
from exchange.model import MarketOrder, COST_BASED_ORDER_EXCHANGES, STOCK_EXCHANGES
from exchange.utility import settings
from datetime import datetime, timedelta
from loguru import logger
from devtools import debug, pformat
import traceback
import os

# 디스코드 웹훅 관련 import (선택적)
try:
    from dhooks import Webhook, Embed
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    print("디스코드 웹훅 기능을 사용하려면 'pip install dhooks' 실행")

# 로그 폴더 확인 및 생성
log_dir = "./log"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 로그 설정
logger.remove(0)
logger.add(
    "./log/poa.log",
    rotation="1 days",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
)
logger.add(
    sys.stderr,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <level>{message}</level>",
)

# 디스코드 웹훅 초기화
hook = None
if DISCORD_AVAILABLE:
    try:
        discord_url = getattr(settings, 'DISCORD_WEBHOOK_URL', None)
        if discord_url and discord_url.strip():
            # discordapp.com을 discord.com으로 변경
            url = discord_url.replace("discordapp", "discord")
            hook = Webhook(url)
            logger.info("디스코드 웹훅이 성공적으로 초기화되었습니다")
        else:
            logger.info("디스코드 웹훅 URL이 설정되지 않음 - 콘솔 로그만 사용")
    except Exception as e:
        logger.warning(f"디스코드 웹훅 초기화 실패: {str(e)} - 콘솔 로그만 사용")
        hook = None
else:
    logger.info("dhooks 라이브러리가 없음 - 콘솔 로그만 사용")


def get_error(e):
    tb = traceback.extract_tb(e.__traceback__)
    target_folder = os.path.abspath(os.path.dirname(tb[0].filename))
    error_msg = []

    for tb_info in tb:
        error_msg.append(f"File {tb_info.filename}, line {tb_info.lineno}, in {tb_info.name}")
        if "raise error." in tb_info.line:
            continue
        error_msg.append(f"  {tb_info.line}")

    error_msg.append(str(e))
    return "\n".join(error_msg)


def parse_time(utc_timestamp):
    timestamp = utc_timestamp + timedelta(hours=9).seconds
    date = datetime.fromtimestamp(timestamp)
    return date.strftime("%y-%m-%d %H:%M:%S")


def logger_test():
    date = parse_time(datetime.utcnow().timestamp())
    logger.info(date)


def log_message(message="None", embed=None):
    """로그 메시지를 콘솔과 디스코드로 전송"""
    # 콘솔 로그는 항상 출력
    logger.info(message)
    print(message)
    
    # 디스코드 웹훅이 사용 가능한 경우에만 전송
    if hook and DISCORD_AVAILABLE:
        try:
            if embed:
                hook.send(embed=embed)
            else:
                hook.send(str(message))
        except Exception as e:
            logger.warning(f"디스코드 메시지 전송 실패: {str(e)}")


def log_order_message(exchange_name, order_result: dict, order_info: MarketOrder):
    """주문 체결 메시지를 로그 및 디스코드로 전송"""
    date = parse_time(datetime.utcnow().timestamp())
    
    # 수량/비용 계산 로직 (기존과 동일)
    if not order_info.is_futures and order_info.is_buy and exchange_name in COST_BASED_ORDER_EXCHANGES:
        f_name = "비용"
        if order_info.amount is not None:
            if exchange_name == "UPBIT":
                amount = str(order_result.get("cost"))
            elif exchange_name == "BITGET":
                amount = str(order_info.amount * order_info.price)
            elif exchange_name == "BYBIT":
                amount = str(order_result.get("info").get("orderQty"))
        elif order_info.percent is not None:
            f_name = "비율"
            amount = f"{order_info.percent}%"
    else:
        f_name = "수량"
        amount = None
        if exchange_name in ("KRX", "NASDAQ", "AMEX", "NYSE"):
            if order_info.amount is not None:
                amount = str(order_info.amount)
            elif order_info.percent is not None:
                f_name = "비율"
                amount = f"{order_info.percent}%"
        elif order_result.get("amount") is None:
            if order_info.amount is not None:
                if exchange_name == "OKX":
                    if order_info.is_futures:
                        f_name = "계약(수량)"
                        amount = f"{order_info.amount // order_info.contract_size}({order_info.contract_size * (order_info.amount // order_info.contract_size)})"
                    else:
                        amount = f"{order_info.amount}"
                else:
                    amount = str(order_info.amount)
            elif order_info.percent is not None:
                if order_info.amount_by_percent is not None:
                    f_name = "비율(수량)" if order_info.is_contract is None else "비율(계약)"
                    amount = f"{order_info.percent}%({order_info.amount_by_percent})"
                else:
                    f_name = "비율"
                    amount = f"{order_info.percent}%"
        elif order_result.get("amount") is not None:
            if order_info.contract_size is not None:
                f_name = "계약"
                if order_result.get("cost") is not None:
                    f_name = "계약(비용)"
                    amount = f"{order_result.get('amount')}({order_result.get('cost'):.2f})"
                else:
                    amount = f"{order_result.get('amount')}"
            else:
                if order_info.amount is not None:
                    f_name = "수량"
                    amount = f"{order_result.get('amount')}"
                elif order_info.percent is not None:
                    f_name = "비율(수량)" if order_info.is_contract is None else "비율(계약)"
                    amount = f"{order_info.percent}%({order_result.get('amount')})"

    symbol = f"{order_info.base}/{order_info.quote+'.P' if order_info.is_crypto and order_info.is_futures else order_info.quote}"

    # 거래 유형 결정
    side = ""
    if order_info.is_futures:
        if order_info.is_entry:
            if order_info.is_buy:
                side = "롱 진입"
            elif order_info.is_sell:
                side = "숏 진입"
        elif order_info.is_close:
            if order_info.is_buy:
                side = "숏 종료"
            elif order_info.is_sell:
                side = "롱 종료"
    else:
        if order_info.is_buy:
            side = "매수"
        elif order_info.is_sell:
            side = "매도"

    # 메시지 생성 및 전송
    if exchange_name in STOCK_EXCHANGES:
        content = f"✅ 주식 체결 알림\n일시: {date}\n거래소: {exchange_name}\n티커: {order_info.base}\n거래유형: {side}\n수량: {amount}\n계좌: {order_info.kis_number}번째 계좌"
        
        if DISCORD_AVAILABLE:
            embed = Embed(
                title=f"📈 {order_info.order_name}",
                description=f"체결: {exchange_name} {order_info.base} {side} {amount}",
                color=0x00FF00,  # 녹색
            )
            embed.add_field(name="일시", value=str(date), inline=False)
            embed.add_field(name="거래소", value=exchange_name, inline=False)
            embed.add_field(name="티커", value=order_info.base, inline=False)
            embed.add_field(name="거래유형", value=side, inline=False)
            embed.add_field(name="수량", value=amount, inline=False)
            embed.add_field(name="계좌", value=f"{order_info.kis_number}번째 계좌", inline=False)
        else:
            embed = None
            
        log_message(content, embed)
    else:
        content = f"✅ 암호화폐 체결 알림\n일시: {date}\n거래소: {exchange_name}\n심볼: {symbol}\n거래유형: {side}\n{f_name}: {amount}"
        
        if DISCORD_AVAILABLE:
            embed = Embed(
                title=f"🚀 {order_info.order_name}",
                description=f"체결: {exchange_name} {symbol} {side} {amount}",
                color=0x00FF00,  # 녹색
            )
            embed.add_field(name="일시", value=str(date), inline=False)
            embed.add_field(name="거래소", value=exchange_name, inline=False)
            embed.add_field(name="심볼", value=symbol, inline=False)
            embed.add_field(name="거래유형", value=side, inline=False)
            if amount:
                embed.add_field(name=f_name, value=amount, inline=False)
            if order_info.leverage is not None:
                embed.add_field(name="레버리지", value=f"{order_info.leverage}배", inline=False)
            if order_result.get("price"):
                embed.add_field(name="체결가", value=str(order_result.get("price")), inline=False)
        else:
            embed = None
            
        log_message(content, embed)


def log_hedge_message(exchange, base, quote, exchange_amount, upbit_amount, hedge):
    """헷지 거래 메시지를 로그 및 디스코드로 전송"""
    date = parse_time(datetime.utcnow().timestamp())
    hedge_type = "헷지 시작" if hedge == "ON" else "헷지 종료"
    content = f"⚖️ {hedge_type}: {base}\n{exchange}: {exchange_amount}\nUPBIT: {upbit_amount}"
    
    if DISCORD_AVAILABLE:
        embed = Embed(
            title=f"⚖️ {hedge_type}", 
            description=content, 
            color=0x0000FF  # 파란색
        )
        embed.add_field(name="일시", value=str(date), inline=False)
        embed.add_field(name="거래소", value=f"{exchange}-UPBIT", inline=False)
        embed.add_field(name="심볼", value=f"{base}/{quote}-{base}/KRW", inline=False)
        embed.add_field(name="거래유형", value=hedge_type, inline=False)
        embed.add_field(
            name="수량",
            value=f"{exchange}: {exchange_amount}\nUPBIT: {upbit_amount}",
            inline=False,
        )
    else:
        embed = None
        
    log_message(content, embed)


def log_error_message(error, name):
    """에러 메시지를 로그 및 디스코드로 전송"""
    content = f"❌ {name} 에러 발생\n{error}"
    
    if DISCORD_AVAILABLE:
        embed = Embed(
            title=f"❌ {name} 에러", 
            description=f"[{name} 에러가 발생했습니다]\n{error}", 
            color=0xFF0000  # 빨간색
        )
    else:
        embed = None
        
    logger.error(f"{name} [에러가 발생했습니다]\n{error}")
    log_message(content, embed)


def log_order_error_message(error: str | Exception, order_info: MarketOrder):
    """주문 에러 메시지를 로그 및 디스코드로 전송"""
    if isinstance(error, Exception):
        error = get_error(error)

    if order_info is not None:
        content = f"❌ 주문 오류 발생\n주문명: {order_info.order_name}\n거래소: {order_info.exchange}\n심볼: {order_info.base}/{order_info.quote}\n오류: {error}"
        
        if DISCORD_AVAILABLE:
            embed = Embed(
                title=f"❌ {order_info.order_name} 주문 오류",
                description=f"[주문 오류가 발생했습니다]\n{error}",
                color=0xFF0000,
            )
        else:
            embed = None
            
        log_message(content, embed)
        logger.error(f"[주문 오류가 발생했습니다]\n{error}")
    else:
        content = f"❌ 오류 발생\n{error}"
        
        if DISCORD_AVAILABLE:
            embed = Embed(
                title="❌ 오류",
                description=f"[오류가 발생했습니다]\n{error}",
                color=0xFF0000,
            )
        else:
            embed = None
            
        log_message(content, embed)
        logger.error(f"[오류가 발생했습니다]\n{error}")


def log_validation_error_message(msg):
    """검증 에러 메시지를 로그 및 디스코드로 전송"""
    content = f"⚠️ 검증 오류 발생\n{msg}"
    logger.error(f"검증 오류가 발생했습니다\n{msg}")
    log_message(content)


def print_alert_message(order_info: MarketOrder, result="성공"):
    """웹훅 메시지를 콘솔에 출력"""
    msg = pformat(order_info.dict(exclude_none=True))

    if result == "성공":
        logger.info(f"주문 {result} 웹훅메세지\n{msg}")
    else:
        logger.error(f"주문 {result} 웹훅메세지\n{msg}")


def log_alert_message(order_info: MarketOrder, result="성공"):
    """웹훅 alert 메시지를 로그 및 디스코드로 전송"""
    content = f"📡 웹훅 메시지 수신\n결과: {result}\n주문명: {order_info.order_name}\n거래소: {order_info.exchange}\n심볼: {order_info.base}/{order_info.quote}"
    
    if DISCORD_AVAILABLE:
        embed = Embed(
            title=f"📡 {order_info.order_name} 웹훅",
            description="[웹훅 alert_message]",
            color=0xFFFF00 if result == "성공" else 0xFF0000,  # 노란색 또는 빨간색
        )
        order_info_dict = order_info.dict(exclude_none=True)
        for key, value in order_info_dict.items():
            embed.add_field(name=key, value=str(value), inline=False)
    else:
        embed = None
        
    log_message(content, embed)
    print_alert_message(order_info, result)


def log_system_startup():
    """시스템 시작 메시지"""
    content = f"🚀 POA Bot Enhanced 시스템 시작\n시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n디스코드 웹훅: {'활성화' if hook else '비활성화'}"
    
    if DISCORD_AVAILABLE and hook:
        embed = Embed(
            title="🚀 POA Bot Enhanced 시작",
            description="자동매매 시스템이 성공적으로 시작되었습니다",
            color=0x00FF00,
        )
        embed.add_field(name="시작 시간", value=datetime.now().strftime('%Y-%m-%d %H:%M:%S'), inline=False)
        embed.add_field(name="디스코드 알림", value="활성화", inline=False)
        embed.add_field(name="웹 관리자", value="http://server-ip:8000/admin", inline=False)
    else:
        embed = None
        
    log_message(content, embed)


def log_system_shutdown():
    """시스템 종료 메시지"""
    content = f"🛑 POA Bot Enhanced 시스템 종료\n시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    if DISCORD_AVAILABLE and hook:
        embed = Embed(
            title="🛑 POA Bot Enhanced 종료",
            description="자동매매 시스템이 종료되었습니다",
            color=0xFF0000,
        )
        embed.add_field(name="종료 시간", value=datetime.now().strftime('%Y-%m-%d %H:%M:%S'), inline=False)
    else:
        embed = None
        
    log_message(content, embed)

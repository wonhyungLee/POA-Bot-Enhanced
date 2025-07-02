from fastapi.exception_handlers import (
    request_validation_exception_handler,
)
from pprint import pprint
from fastapi import FastAPI, Request, status, BackgroundTasks, Form, HTTPException, Depends
from fastapi.responses import ORJSONResponse, RedirectResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
from exchange.stock.kis import KoreaInvestment
from exchange.model import MarketOrder, PriceRequest, HedgeData, OrderRequest
from exchange.utility import (
    settings,
    log_order_message,
    log_alert_message,
    print_alert_message,
    logger_test,
    log_order_error_message,
    log_validation_error_message,
    log_hedge_message,
    log_error_message,
    log_message,
)
import traceback
from exchange import get_exchange, log_message, db, settings, get_bot, pocket
import ipaddress
import os
import sys
from devtools import debug
import jwt
from datetime import datetime, timedelta
import hashlib
from typing import Optional

VERSION = "0.1.8"
app = FastAPI(default_response_class=ORJSONResponse)

# 템플릿 및 정적 파일 설정
templates = Jinja2Templates(directory="templates")

# static 폴더가 없으면 생성
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

# JWT 설정
SECRET_KEY = "your-secret-key-here-change-in-production"  # 실제 배포시 환경변수로 관리
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

def get_error(e):
    tb = traceback.extract_tb(e.__traceback__)
    target_folder = os.path.abspath(os.path.dirname(tb[0].filename))
    error_msg = []

    for tb_info in tb:
        error_msg.append(
            f"File {tb_info.filename}, line {tb_info.lineno}, in {tb_info.name}"
        )
        error_msg.append(f"  {tb_info.line}")

    error_msg.append(str(e))
    return error_msg

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.on_event("startup")
async def startup():
    # 관리자 인터페이스용 데이터베이스 테이블 생성
    init_admin_db()
    log_message(f"POABOT 실행 완료! - 버전:{VERSION}")

@app.on_event("shutdown")
async def shutdown():
    db.close()

def init_admin_db():
    """관리자 인터페이스용 데이터베이스 테이블 초기화"""
    try:
        # API 키 관리 테이블
        query = """
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exchange TEXT NOT NULL,
            api_key TEXT NOT NULL,
            secret_key TEXT NOT NULL,
            passphrase TEXT,
            account_number TEXT,
            account_code TEXT,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        db.excute(query, {})
        
        # 사용자 관리 테이블
        query = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        db.excute(query, {})
        
        # 기본 관리자 계정 생성 (비밀번호: admin123)
        admin_password_hash = hashlib.sha256("admin123".encode()).hexdigest()
        query = """
        INSERT OR IGNORE INTO users (username, password_hash, is_admin)
        VALUES (?, ?, ?)
        """
        db.excute(query, ("admin", admin_password_hash, 1))
        
    except Exception as e:
        log_error_message(traceback.format_exc(), "데이터베이스 초기화 에러")

whitelist = [
    "52.89.214.238",
    "34.212.75.30",
    "54.218.53.128",
    "52.32.178.7",
    "127.0.0.1",
]
whitelist = whitelist + settings.WHITELIST

@app.middleware("http")
async def whitelist_middleware(request: Request, call_next):
    try:
        # 관리자 페이지는 화이트리스트 체크에서 제외
        if request.url.path.startswith("/admin") or request.url.path.startswith("/static"):
            response = await call_next(request)
            return response
            
        if (
            request.client.host not in whitelist
            and not ipaddress.ip_address(request.client.host).is_private
        ):
            msg = f"{request.client.host}는 안됩니다"
            print(msg)
            return ORJSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content=f"{request.client.host}는 허용되지 않습니다",
            )
    except:
        log_error_message(traceback.format_exc(), "미들웨어 에러")
    else:
        response = await call_next(request)
        return response

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    msgs = [
        f"[에러{index+1}] " + f"{error.get('msg')} \n{error.get('loc')}"
        for index, error in enumerate(exc.errors())
    ]
    message = "[Error]\n"
    for msg in msgs:
        message = message + msg + "\n"

    log_validation_error_message(f"{message}\n {exc.body}")
    return await request_validation_exception_handler(request, exc)

# ========== 기존 API 엔드포인트들 ==========

@app.get("/ip")
async def get_ip():
    data = httpx.get("https://ipv4.jsonip.com").json()["ip"]
    log_message(data)

@app.get("/hi")
async def welcome():
    return "hi!!"

@app.post("/price")
async def price(price_req: PriceRequest, background_tasks: BackgroundTasks):
    exchange = get_exchange(price_req.exchange)
    price = exchange.dict()[price_req.exchange].fetch_price(
        price_req.base, price_req.quote
    )
    return price

def log(exchange_name, result, order_info):
    log_order_message(exchange_name, result, order_info)
    print_alert_message(order_info)

def log_error(error_message, order_info):
    log_order_error_message(error_message, order_info)
    log_alert_message(order_info, "실패")

@app.post("/order")
@app.post("/")
async def order(order_info: MarketOrder, background_tasks: BackgroundTasks):
    order_result = None
    try:
        exchange_name = order_info.exchange
        bot = get_bot(exchange_name, order_info.kis_number)
        bot.init_info(order_info)

        if bot.order_info.is_crypto:
            if bot.order_info.is_entry:
                order_result = bot.market_entry(bot.order_info)
            elif bot.order_info.is_close:
                order_result = bot.market_close(bot.order_info)
            elif bot.order_info.is_buy:
                order_result = bot.market_buy(bot.order_info)
            elif bot.order_info.is_sell:
                order_result = bot.market_sell(bot.order_info)
            background_tasks.add_task(log, exchange_name, order_result, order_info)
        elif bot.order_info.is_stock:
            order_result = bot.create_order(
                bot.order_info.exchange,
                bot.order_info.base,
                order_info.type.lower(),
                order_info.side.lower(),
                order_info.amount,
            )
            background_tasks.add_task(log, exchange_name, order_result, order_info)

    except TypeError as e:
        error_msg = get_error(e)
        background_tasks.add_task(
            log_order_error_message, "\n".join(error_msg), order_info
        )

    except Exception as e:
        error_msg = get_error(e)
        background_tasks.add_task(log_error, "\n".join(error_msg), order_info)

    else:
        return {"result": "success"}

    finally:
        pass

def get_hedge_records(base):
    records = pocket.get_full_list("kimp", query_params={"filter": f'base = "{base}"'})
    binance_amount = 0.0
    binance_records_id = []
    upbit_amount = 0.0
    upbit_records_id = []
    for record in records:
        if record.exchange == "BINANCE":
            binance_amount += record.amount
            binance_records_id.append(record.id)
        elif record.exchange == "UPBIT":
            upbit_amount += record.amount
            upbit_records_id.append(record.id)

    return {
        "BINANCE": {"amount": binance_amount, "records_id": binance_records_id},
        "UPBIT": {"amount": upbit_amount, "records_id": upbit_records_id},
    }

@app.post("/hedge")
async def hedge(hedge_data: HedgeData, background_tasks: BackgroundTasks):
    exchange_name = hedge_data.exchange.upper()
    bot = get_bot(exchange_name)
    upbit = get_bot("UPBIT")

    base = hedge_data.base
    quote = hedge_data.quote
    amount = hedge_data.amount
    leverage = hedge_data.leverage
    hedge = hedge_data.hedge

    foreign_order_info = OrderRequest(
        exchange=exchange_name,
        base=base,
        quote=quote,
        side="entry/sell",
        type="market",
        amount=amount,
        leverage=leverage,
    )
    bot.init_info(foreign_order_info)
    if hedge == "ON":
        try:
            if amount is None:
                raise Exception("헷지할 수량을 요청하세요")
            binance_order_result = bot.market_entry(foreign_order_info)
            binance_order_amount = binance_order_result["amount"]
            pocket.create(
                "kimp",
                {
                    "exchange": "BINANCE",
                    "base": base,
                    "quote": quote,
                    "amount": binance_order_amount,
                },
            )
            if leverage is None:
                leverage = 1
            try:
                korea_order_info = OrderRequest(
                    exchange="UPBIT",
                    base=base,
                    quote="KRW",
                    side="buy",
                    type="market",
                    amount=binance_order_amount,
                )
                upbit.init_info(korea_order_info)
                upbit_order_result = upbit.market_buy(korea_order_info)
            except Exception as e:
                hedge_records = get_hedge_records(base)
                binance_records_id = hedge_records["BINANCE"]["records_id"]
                binance_amount = hedge_records["BINANCE"]["amount"]
                binance_order_result = bot.market_close(
                    OrderRequest(
                        exchange=exchange_name,
                        base=base,
                        quote=quote,
                        side="close/buy",
                        amount=binance_amount,
                    )
                )
                for binance_record_id in binance_records_id:
                    pocket.delete("kimp", binance_record_id)
                log_message(
                    "[헷지 실패] 업비트에서 에러가 발생하여 바이낸스 포지션을 종료합니다"
                )
            else:
                upbit_order_info = upbit.get_order(upbit_order_result["id"])
                upbit_order_amount = upbit_order_info["filled"]
                pocket.create(
                    "kimp",
                    {
                        "exchange": "UPBIT",
                        "base": base,
                        "quote": "KRW",
                        "amount": upbit_order_amount,
                    },
                )
                log_hedge_message(
                    exchange_name,
                    base,
                    quote,
                    binance_order_amount,
                    upbit_order_amount,
                    hedge,
                )

        except Exception as e:
            background_tasks.add_task(
                log_error_message, traceback.format_exc(), "헷지 에러"
            )
            return {"result": "error"}
        else:
            return {"result": "success"}

    elif hedge == "OFF":
        try:
            records = pocket.get_full_list(
                "kimp", query_params={"filter": f'base = "{base}"'}
            )
            binance_amount = 0.0
            binance_records_id = []
            upbit_amount = 0.0
            upbit_records_id = []
            for record in records:
                if record.exchange == "BINANCE":
                    binance_amount += record.amount
                    binance_records_id.append(record.id)
                elif record.exchange == "UPBIT":
                    upbit_amount += record.amount
                    upbit_records_id.append(record.id)

            if binance_amount > 0 and upbit_amount > 0:
                # 바이낸스
                order_info = OrderRequest(
                    exchange="BINANCE",
                    base=base,
                    quote=quote,
                    side="close/buy",
                    amount=binance_amount,
                )
                binance_order_result = bot.market_close(order_info)
                for binance_record_id in binance_records_id:
                    pocket.delete("kimp", binance_record_id)
                # 업비트
                order_info = OrderRequest(
                    exchange="UPBIT",
                    base=base,
                    quote="KRW",
                    side="sell",
                    amount=upbit_amount,
                )
                upbit_order_result = upbit.market_sell(order_info)
                for upbit_record_id in upbit_records_id:
                    pocket.delete("kimp", upbit_record_id)

                log_hedge_message(
                    exchange_name, base, quote, binance_amount, upbit_amount, hedge
                )
            elif binance_amount == 0 and upbit_amount == 0:
                log_message(f"{exchange_name}, UPBIT에 종료할 수량이 없습니다")
            elif binance_amount == 0:
                log_message(f"{exchange_name}에 종료할 수량이 없습니다")
            elif upbit_amount == 0:
                log_message("UPBIT에 종료할 수량이 없습니다")
        except Exception as e:
            background_tasks.add_task(
                log_error_message, traceback.format_exc(), "헷지종료 에러"
            )
            return {"result": "error"}
        else:
            return {"result": "success"}

# ========== 관리자 인터페이스 엔드포인트들 ==========

@app.get("/admin", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """관리자 로그인 페이지"""
    return templates.TemplateResponse("admin_login.html", {"request": request})

@app.post("/admin/login")
async def admin_login(request: Request, username: str = Form(...), password: str = Form(...)):
    """관리자 로그인 처리"""
    try:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        query = "SELECT * FROM users WHERE username = ? AND password_hash = ? AND is_admin = 1"
        user = db.fetch_one(query, (username, password_hash))
        
        if user:
            access_token = create_access_token(data={"sub": username})
            response = RedirectResponse(url="/admin/dashboard", status_code=302)
            response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=1800)
            return response
        else:
            return templates.TemplateResponse("admin_login.html", {
                "request": request, 
                "error": "잘못된 사용자명 또는 비밀번호입니다."
            })
    except Exception as e:
        log_error_message(traceback.format_exc(), "로그인 에러")
        return templates.TemplateResponse("admin_login.html", {
            "request": request, 
            "error": "로그인 중 오류가 발생했습니다."
        })

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """관리자 대시보드"""
    try:
        # 쿠키에서 토큰 확인
        token = request.cookies.get("access_token")
        if not token:
            return RedirectResponse(url="/admin")
        
        # API 키 목록 조회
        query = "SELECT * FROM api_keys ORDER BY exchange, created_at DESC"
        api_keys = db.fetch_all(query, {})
        
        return templates.TemplateResponse("admin_dashboard.html", {
            "request": request,
            "api_keys": api_keys
        })
    except Exception as e:
        log_error_message(traceback.format_exc(), "대시보드 로딩 에러")
        return RedirectResponse(url="/admin")

@app.post("/admin/api-key")
async def add_api_key(
    request: Request,
    exchange: str = Form(...),
    api_key: str = Form(...),
    secret_key: str = Form(...),
    passphrase: str = Form(""),
    account_number: str = Form(""),
    account_code: str = Form("")
):
    """API 키 추가"""
    try:
        # 쿠키에서 토큰 확인
        token = request.cookies.get("access_token")
        if not token:
            return RedirectResponse(url="/admin")
        
        query = """
        INSERT INTO api_keys (exchange, api_key, secret_key, passphrase, account_number, account_code)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        db.excute(query, (exchange, api_key, secret_key, passphrase, account_number, account_code))
        
        return RedirectResponse(url="/admin/dashboard", status_code=302)
    except Exception as e:
        log_error_message(traceback.format_exc(), "API 키 추가 에러")
        return RedirectResponse(url="/admin/dashboard")

@app.post("/admin/api-key/{key_id}/delete")
async def delete_api_key(request: Request, key_id: int):
    """API 키 삭제"""
    try:
        # 쿠키에서 토큰 확인
        token = request.cookies.get("access_token")
        if not token:
            return RedirectResponse(url="/admin")
        
        query = "DELETE FROM api_keys WHERE id = ?"
        db.excute(query, (key_id,))
        
        return RedirectResponse(url="/admin/dashboard", status_code=302)
    except Exception as e:
        log_error_message(traceback.format_exc(), "API 키 삭제 에러")
        return RedirectResponse(url="/admin/dashboard")

@app.post("/admin/api-key/{key_id}/toggle")
async def toggle_api_key(request: Request, key_id: int):
    """API 키 활성화/비활성화 토글"""
    try:
        # 쿠키에서 토큰 확인
        token = request.cookies.get("access_token")
        if not token:
            return RedirectResponse(url="/admin")
        
        query = "UPDATE api_keys SET is_active = NOT is_active WHERE id = ?"
        db.excute(query, (key_id,))
        
        return RedirectResponse(url="/admin/dashboard", status_code=302)
    except Exception as e:
        log_error_message(traceback.format_exc(), "API 키 토글 에러")
        return RedirectResponse(url="/admin/dashboard")

@app.get("/admin/api-key/{key_id}/edit", response_class=HTMLResponse)
async def edit_api_key_page(request: Request, key_id: int):
    """API 키 수정 페이지"""
    try:
        # 쿠키에서 토큰 확인
        token = request.cookies.get("access_token")
        if not token:
            return RedirectResponse(url="/admin")
        
        query = "SELECT * FROM api_keys WHERE id = ?"
        api_key = db.fetch_one(query, (key_id,))
        
        if not api_key:
            return RedirectResponse(url="/admin/dashboard")
        
        # 컬럼명으로 접근할 수 있도록 딕셔너리로 변환
        api_key_dict = {
            'id': api_key[0],
            'exchange': api_key[1],
            'api_key': api_key[2],
            'secret_key': api_key[3],
            'passphrase': api_key[4],
            'account_number': api_key[5],
            'account_code': api_key[6],
            'is_active': api_key[7]
        }
        
        return templates.TemplateResponse("edit_api_key.html", {
            "request": request,
            "api_key": api_key_dict
        })
    except Exception as e:
        log_error_message(traceback.format_exc(), "API 키 수정 페이지 로딩 에러")
        return RedirectResponse(url="/admin/dashboard")

@app.post("/admin/api-key/{key_id}/update")
async def update_api_key(
    request: Request,
    key_id: int,
    exchange: str = Form(...),
    api_key: str = Form(...),
    secret_key: str = Form(...),
    passphrase: str = Form(""),
    account_number: str = Form(""),
    account_code: str = Form("")
):
    """API 키 업데이트"""
    try:
        # 쿠키에서 토큰 확인
        token = request.cookies.get("access_token")
        if not token:
            return RedirectResponse(url="/admin")
        
        query = """
        UPDATE api_keys 
        SET exchange = ?, api_key = ?, secret_key = ?, passphrase = ?, 
            account_number = ?, account_code = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """
        db.excute(query, (exchange, api_key, secret_key, passphrase, account_number, account_code, key_id))
        
        return RedirectResponse(url="/admin/dashboard", status_code=302)
    except Exception as e:
        log_error_message(traceback.format_exc(), "API 키 업데이트 에러")
        return RedirectResponse(url="/admin/dashboard")

@app.get("/admin/logout")
async def admin_logout():
    """관리자 로그아웃"""
    response = RedirectResponse(url="/admin", status_code=302)
    response.delete_cookie(key="access_token")
    return response

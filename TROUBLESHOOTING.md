# 비트겟 데모 트레이딩 문제 해결 가이드

## 🚨 **심볼 에러 해결 (BTC/USDT:USDT 에러)**

### **❌ 에러 메시지**
```
bitget does not have market symbol BTC/USDT:USDT
```

### **✅ 해결책**

#### **1️⃣ 올바른 웹훅 메시지 형태**

**🔴 잘못된 방법:**
```json
{
  "exchange": "BITGET",
  "base": "BTC",
  "quote": "USDT.P",  // ❌ .P 사용하면 에러
  "side": "entry/buy"
}
```

**✅ 올바른 방법:**
```json
{
  "exchange": "BITGET", 
  "base": "BTC",
  "quote": "USDT",  // ✅ .P 제거
  "side": "entry/buy"
}
```

#### **2️⃣ 거래 타입별 올바른 메시지**

**선물 거래 (entry/close 사용):**
```json
// 롱 진입
{
  "password": "dldnjsgud",
  "exchange": "BITGET",
  "base": "BTC",
  "quote": "USDT", 
  "side": "entry/buy",
  "amount": "0.01",
  "leverage": "2"
}

// 롱 청산
{
  "password": "dldnjsgud", 
  "exchange": "BITGET",
  "base": "BTC",
  "quote": "USDT",
  "side": "close/sell",
  "percent": "100"
}
```

**현물 거래 (buy/sell 사용):**
```json
// 매수
{
  "password": "dldnjsgud",
  "exchange": "BITGET", 
  "base": "BTC",
  "quote": "USDT",
  "side": "buy",
  "amount": "0.001"
}

// 매도
{
  "password": "dldnjsgud",
  "exchange": "BITGET",
  "base": "BTC", 
  "quote": "USDT",
  "side": "sell",
  "percent": "100"
}
```

## 🔧 **기타 문제 해결**

### **에러: 40099 - exchange environment is incorrect**
**해결**: 서버에서 `BITGET_DEMO_MODE="true"` 설정 확인

### **에러: 거래량 부족**
**해결**: 데모 계정에서 가상 자금 충전

### **에러: API 권한 없음**
**해결**: 비트겟 데모 계정에서 선물 거래 권한 활성화

## 📋 **지원 거래 페어**

### **✅ 올바른 페어 형태**
- `BTC/USDT` - 비트코인
- `ETH/USDT` - 이더리움  
- `SOL/USDT` - 솔라나
- `ADA/USDT` - 카르다노
- `DOGE/USDT` - 도지코인

### **❌ 사용하면 안되는 형태**
- `BTC/USDT.P` - ❌
- `BTC/USDTPERP` - ❌  
- `BTCUSDT` - ❌

## 🔍 **서버 로그 확인 방법**

```bash
# SSH 접속
ssh ubuntu@서버IP

# POA 로그 확인
pm2 logs POA --lines 50

# 실시간 로그 모니터링
pm2 logs POA --follow
```

### **정상 로그 예시**
```
비트겟 데모 트레이딩 모드로 실행됩니다
비트겟 데모 트레이딩 모드 활성화됨
데모롱진입 주문 완료
```

### **에러 로그 예시**
```
bitget does not have market symbol BTC/USDT:USDT
```

## 🚀 **빠른 테스트 방법**

### **1️⃣ 간단한 테스트 메시지**
웹훅 URL에 다음 JSON 전송:
```json
{
  "password": "dldnjsgud",
  "exchange": "BITGET",
  "base": "BTC", 
  "quote": "USDT",
  "side": "buy",
  "amount": "0.001",
  "order_name": "테스트주문"
}
```

### **2️⃣ curl 명령어로 테스트**
```bash
curl -X POST http://서버IP/ \
  -H "Content-Type: application/json" \
  -d '{
    "password": "dldnjsgud",
    "exchange": "BITGET", 
    "base": "BTC",
    "quote": "USDT",
    "side": "buy", 
    "amount": "0.001"
  }'
```

## 📞 **추가 지원**

문제가 계속 발생하면:
1. 서버 로그 전체 복사
2. 사용한 웹훅 메시지 공유
3. 비트겟 데모 계정 설정 확인

**핵심**: `.P` 접미사 제거하고 올바른 `side` 값 사용!

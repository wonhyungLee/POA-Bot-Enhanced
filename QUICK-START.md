# 빠른 시작 가이드

## 🚀 5분만에 비트겟 데모 트레이딩 시작하기

### 1️⃣ 비트겟 데모 계정 준비
1. [Bitget 데모 트레이딩](https://www.bitget.com/futures-activity/demo-trading) 방문
2. 데모 계정 생성 및 로그인
3. API 관리 → 새 API 키 생성
   - API Key 복사
   - Secret Key 복사  
   - Passphrase 설정 및 복사
4. 선물 거래 권한 활성화 ✅

### 2️⃣ Oracle Cloud 서버 생성

#### 📋 필요한 정보 준비
```
BITGET_DEMO_KEY="여기에_복사한_API_키"
BITGET_DEMO_SECRET="여기에_복사한_Secret_키"  
BITGET_DEMO_PASSPHRASE="여기에_설정한_Passphrase"
```

#### 🔧 Oracle Cloud 설정
1. Oracle Cloud 콘솔 → Compute → Instances
2. "Create Instance" 클릭
3. **Advanced Options** → **Management** → **Cloud-init script** 선택
4. `cloud-init-demo.yaml` 내용 복사/붙여넣기
5. **⚠️ 중요**: 다음 줄들을 수정:
   ```yaml
   BITGET_DEMO_KEY="실제_API_키로_변경"
   BITGET_DEMO_SECRET="실제_Secret_키로_변경"
   BITGET_DEMO_PASSPHRASE="실제_Passphrase로_변경"
   ```
6. Create 클릭

### 3️⃣ 서버 확인 (5-10분 후)

#### SSH 접속
```bash
ssh ubuntu@서버_공인_IP
```

#### 상태 확인
```bash
# POA 서비스 상태
pm2 list

# 로그 확인 (데모 모드 메시지 확인)
pm2 logs POA

# 성공 메시지 예시:
# "비트겟 데모 트레이딩 모드로 실행됩니다"
# "비트겟 데모 트레이딩 모드 활성화됨"
```

### 4️⃣ TradingView 연결

#### 웹훅 URL 설정
```
http://서버_공인_IP/
```

#### 예제 전략 사용
1. `tradingview-demo-example.pine` 내용 복사
2. TradingView → Pine Editor에 붙여넣기
3. 차트에 적용
4. 알림 생성 → 웹훅 URL 입력

### 5️⃣ 테스트 확인

#### 서버 로그에서 확인
```bash
pm2 logs POA --lines 50
```

#### 예상 메시지:
- `데모롱진입` 또는 `데모숏진입` 주문 성공
- 에러 없이 정상 처리

---

## 🔧 문제 해결

### ❌ 에러 40099 발생 시
- **원인**: 데모 API 키 설정 문제
- **해결**: 환경변수 재확인 및 서버 재시작
  ```bash
  pm2 restart POA
  ```

### ❌ 웹훅 연결 안됨
- **원인**: 방화벽 또는 URL 오류
- **해결**: Oracle Cloud 보안 그룹에서 80포트 열기

### ❌ 주문 실패
- **원인**: 데모 계정 잔고 부족
- **해결**: 데모 계정에서 가상 자금 충전

---

## 🎯 다음 단계

### 라이브 모드로 전환 (충분한 테스트 후)
1. `.env` 파일에서 `BITGET_DEMO_MODE="false"` 변경
2. 실제 API 키로 교체
3. 서버 재시작: `pm2 restart POA`

### 전략 최적화
- 백테스팅 결과 검토
- 리스크 관리 설정 조정
- 수익률 목표 설정

**⚠️ 주의: 라이브 모드에서는 실제 자금이 사용됩니다!**

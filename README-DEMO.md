# POA Bot - 비트겟 데모 트레이딩 지원 버전

기존 POA Bot에 **비트겟 데모 트레이딩** 기능을 추가한 버전입니다.

## 🚀 새로운 기능

- ✅ 비트겟 데모 트레이딩 지원
- ✅ 라이브/데모 모드 자동 전환
- ✅ 기존 기능 모두 보존

## 📋 설정 방법

### 1. 비트겟 데모 계정 준비
1. [Bitget 데모 트레이딩](https://www.bitget.com/futures-activity/demo-trading) 페이지에서 데모 계정 생성
2. 데모 계정에서 API 키 발급:
   - API Key
   - Secret Key  
   - Passphrase
3. 선물 거래 권한 활성화

### 2. 환경변수 설정
`.env` 파일에 다음 변수들을 추가/수정:

```bash
# 데모 모드 활성화 (true: 데모, false 또는 주석: 라이브)
BITGET_DEMO_MODE="true"

# 데모용 API 키 (데모 계정에서 발급받은 키)
BITGET_DEMO_KEY="비트겟_데모_API_키"
BITGET_DEMO_SECRET="비트겟_데모_시크릿_키"  
BITGET_DEMO_PASSPHRASE="패스프레이즈"

# 기존 라이브 키 (그대로 유지)
BITGET_KEY="bg_bc9f50ce52ad58a9cd7c821fbc5ded1c"
BITGET_SECRET="d8843c00e3ef03cce41a14eaf326f7a86e3335f053be984b92f3e47ae0a20b82"
BITGET_PASSPHRASE="dldnjsgud"
```

### 3. 모드 전환 방법

#### 데모 모드로 실행
```bash
BITGET_DEMO_MODE="true"
```

#### 라이브 모드로 실행  
```bash
BITGET_DEMO_MODE="false"
# 또는 BITGET_DEMO_MODE 변수 주석 처리
```

## 🔧 Cloud-init 스크립트 사용법

### Oracle Cloud에서 인스턴스 생성 시
1. `cloud-init-demo.yaml` 파일 내용 복사
2. **환경변수 수정 필수**: 
   ```yaml
   BITGET_DEMO_KEY="여기에_실제_데모_API_키_입력"
   BITGET_DEMO_SECRET="여기에_실제_데모_시크릿_키_입력"
   ```
3. GitHub 저장소 URL 수정:
   ```yaml
   git clone "https://github.com/사용자명/POA-with-demo.git" /root/POA
   ```

## ⚠️ 중요 사항

### 데모 모드 확인 방법
서버 로그에서 다음 메시지 확인:
```
비트겟 데모 트레이딩 모드로 실행됩니다
비트겟 데모 트레이딩 모드 활성화됨
```

### 주의사항
1. **데모 모드에서는 실제 자금이 사용되지 않습니다**
2. 데모 계정 잔고는 가상 자금입니다
3. 데모 API 키는 실제 거래에 사용할 수 없습니다
4. 라이브 모드로 전환 시 실제 자금이 사용되므로 주의하세요

## 🐛 문제 해결

### 에러 40099 해결됨
- ✅ "exchange environment is incorrect" 에러 수정
- ✅ PAPTRADING 헤더 자동 추가
- ✅ ccxt sandbox 모드 활성화

### 로그 확인 방법
```bash
pm2 logs POA
```

### 재시작 방법
```bash
pm2 restart POA
```

## 📞 지원

문제 발생 시:
1. 환경변수 설정 재확인
2. 데모 API 키 유효성 확인  
3. 서버 로그 확인
4. POA Bot 재시작

---
**기존 POA Bot의 모든 기능을 그대로 지원하면서 비트겟 데모 트레이딩이 추가되었습니다.**

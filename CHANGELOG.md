# 변경 이력 (CHANGELOG)

## [1.1.0] - 2025-06-21 (비트겟 데모 트레이딩 지원)

### 🆕 새로운 기능
- **비트겟 데모 트레이딩 지원** - 가상 자금으로 안전한 전략 테스트
- 라이브/데모 모드 간편 전환 기능
- 데모 전용 환경변수 지원 (`BITGET_DEMO_MODE`, `BITGET_DEMO_KEY` 등)
- ccxt sandbox 모드 자동 활성화
- PAPTRADING 헤더 자동 추가

### 🔧 수정사항
- **에러 40099 완전 해결** - "exchange environment is incorrect" 
- `schemas.py`: 비트겟 데모 환경변수 추가
- `pexchange.py`: 데모 키 체크 로직 추가  
- `bitget.py`: sandbox 모드 및 데모 헤더 지원
- 로그 메시지 개선 (데모 모드 활성화 알림)

### 📁 새로운 파일들
- `README-DEMO.md`: 상세 설정 가이드
- `QUICK-START.md`: 빠른 시작 가이드
- `tradingview-demo-example.pine`: 데모용 TradingView 스크립트
- `cloud-init-demo.yaml`: 데모 지원 Oracle Cloud 배포 스크립트
- `.env.template`: 환경변수 설정 템플릿
- `CHANGELOG.md`: 변경 이력

### 🎯 기존 기능 보존
- ✅ 모든 기존 거래소 지원 유지
- ✅ 기존 라이브 트레이딩 기능 완전 보존
- ✅ 기존 API 호환성 유지
- ✅ 한국투자증권, 업비트, 바이낸스, 바이비트, OKX 정상 동작

### 🔒 보안 개선
- 데모/라이브 API 키 분리 관리
- 민감 정보 .gitignore 추가
- 환경변수 템플릿 제공

### 📖 문서화
- README.md 업데이트 (비트겟 데모 기능 안내)
- 설정 가이드 추가
- TradingView 연동 예제 제공
- 문제 해결 가이드 추가

---

## [1.0.x] - 이전 버전

### 지원 거래소
- 업비트 KRW 마켓
- 바이낸스 현물/선물 USDT,BUSD 마켓  
- 바이비트 현물/선물 USDT 마켓
- 비트겟 현물/선물 USDT 마켓 (라이브만)
- OKX 현물/선물 USDT 마켓
- 한국투자증권 한국/미국 주식 마켓

### 기본 기능
- TradingView 웹훅 처리
- 자동 매매 실행
- 포지션 관리
- 손익 관리
- 로그 및 알림

---

## 🔮 향후 계획

### v1.2.0 (예정)
- [ ] 다른 거래소 데모 모드 지원 확장
- [ ] 백테스팅 결과 비교 기능
- [ ] 위험 관리 고도화
- [ ] 성능 모니터링 대시보드

### v1.3.0 (예정)  
- [ ] 포트폴리오 관리 기능
- [ ] 다중 전략 동시 실행
- [ ] 텔레그램 봇 연동

---

## 📞 지원 및 기여

- **이슈 리포트**: GitHub Issues 활용
- **기능 제안**: GitHub Discussions 
- **기여 방법**: Pull Request 환영
- **라이선스**: GNU General Public License v3.0

**⚠️ 면책조항**: 본 소프트웨어 사용으로 인한 모든 손실에 대해 개발자는 책임지지 않습니다.

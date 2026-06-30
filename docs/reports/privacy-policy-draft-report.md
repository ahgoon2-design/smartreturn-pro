# SmartReturn-platform 개인정보처리방침 초안 작성 보고서

## 1. 수행한 지시문 ID

- `SRP-2026-06-23-PRIVACY-POLICY-DRAFT`

## 2. 조사한 파일 목록

### 필수 선행 문서

- `AGENTS.md`
- `ai-harness/memory/000-read-this-first.md`
- `ai-harness/handoff/latest-handoff.md`

### 저장소 내부 업무·보안·권한 기준 문서

- `docs/skills/smartreturn-platform-business-architecture.md`
- `docs/skills/naver-cloud-saas-architecture.md`
- `docs/skills/channel-return-auto-collection.md`
- `docs/skills/git-security-check.md`
- `docs/business/smartreturn-pro-return-mvp-flow.md`
- `docs/business/smartreturn-pro-return-api-schema.md`
- `docs/business/smartreturn-pro-return-api-policy.md`
- `docs/business/smartreturn-pro-return-policy.md`
- `docs/business/smartreturn-pro-auth-client-scope-api-policy.md`
- `docs/business/smartreturn-pro-auth-password-policy.md`
- `docs/business/smartreturn-pro-master-data-policy.md`
- `docs/business/smartreturn-pro-inbound-outbound-policy.md`
- `docs/business/agency-return-outsourcing-business-model.md`

### 저장소 내부 참고 원문 확인 문서

- `docs/reference/cj-logistics-privacy-policy-source-2026-06-08.md`
- `docs/reference/cj-logistics-parcel-terms-source-2026-06-23.md`
- `docs/reference/cj-logistics-the-fulfill-privacy-policy-source-2026-06-08.md`
- `docs/reference/cj-logistics-the-fulfill-terms-source-2026-06-23.md`
- `docs/reference/sabangnet-privacy-policy-source-2026-05-06.md`
- `docs/reference/sabangnet-terms-source-2026-06-23.md`
- `docs/reference/ezadmin-privacy-policy-source-2009-08-01.md`
- `docs/reference/ezadmin-terms-source-2025-08-01.md`
- `docs/reference/poomgo-privacy-policy-source-2026-06-08.md`
- `docs/reference/poomgo-terms-source-unconfirmed-2026-06-23.md`
- `docs/reference/naver-business-fulfillment-privacy-policy-source-2025-05-29.md`
- `docs/reference/returnall-privacy-policy-source-2026-06-23.md`
- `docs/reference/returnall-privacy-policy-and-terms-source-2026-06-23.md`
- `docs/reference/v3.5_sabangnet_policy_privacy.pdf`

### 공식 기준

- 개인정보보호위원회 안내서 목록의 `개인정보 처리방침 작성지침(2026.4. 개정)`
- 개인정보 보호법 제30조 개인정보 처리방침 수립·공개 항목

## 3. 참고한 회사/문서 유형 요약

- 택배·풀필먼트 계열 개인정보처리방침과 택배 이용약관: 운송장번호, 배송조회, 수취인 정보, 사고·분쟁 처리, 위탁·제3자 제공 구조를 참고했다.
- 쇼핑몰 통합관리/OMS 계열 개인정보처리방침과 이용약관: 주문·클레임·송장·API 인증키·알림 발송·계정 관리·국외 이전 항목을 비교했다.
- 풀필먼트/반품대행 계열 개인정보처리방침과 이용약관: 반품 사진, 첨부파일, 고객사별 업무 데이터, 보관·출고·반품·정산 흐름을 비교했다.
- 개인정보보호위원회 작성지침: 처리 목적, 처리 항목, 보유기간, 파기, 제3자 제공, 위탁, 국외 이전, 정보주체 권리, 안전성 확보조치, 자동 수집 장치, 행태정보, 가명정보, 아동 개인정보, 보호책임자, 권익침해 구제, 방침 변경 목차를 기준으로 삼았다.

외부 회사 문구는 초안에 복사하지 않고, 항목 구조와 위험 포인트만 SmartReturn-platform 업무 흐름에 맞게 재구성했다.

## 4. 생성 파일

- `docs/legal/privacy-policy-draft.md`
- `docs/reports/privacy-policy-draft-report.md`

## 5. SmartReturn-platform에 맞게 반영한 핵심 항목

- 회원가입 중심 방침이 아니라 반품 접수, 택배 수거·배송조회, 센터 입고, 검수·판정, 사진·첨부파일, 재고 반영, 폐기/제조사반품/외부반출, 고객 문의, 사고·분쟁, 정산, 관리자 계정, 감사로그·보안로그 흐름 중심으로 작성했다.
- 운송장번호, 이름, 전화번호, 주소, 이메일, 상품정보, 사진, 처리 이력은 개인정보 또는 개인정보와 결합 가능한 정보로 명시했다.
- 최종 고객/수취인, 쇼핑몰/고객사, 택배 대리점, 직영센터, 플랫폼 운영자, 외부 API·알림·클라우드·문자 발송 위탁사 사이의 정보 흐름을 구분했다.
- 고객사, 대리점, 센터, 창고 scope는 프론트 표시가 아니라 백엔드 권한·테넌시 격리로 차단해야 한다는 기준을 반영했다.
- 업로드 원본, API 원본 이벤트, 사진·첨부파일, export 파일, 로그 파일까지 개인정보 파기·보관·접근권한 대상에 포함했다.
- 개인정보처리방침 초안과 별도로 보안 구현 체크리스트 메모를 포함했다.

## 6. 🔴 빨강 고위험 항목 목록

- 주민등록번호, 민감정보, 불필요한 개인통관고유부호 수집 여부
- 실제 고객 주소/전화번호/운송장번호/사진 테스트 데이터 사용 금지
- 고객사 간 개인정보 열람 가능성
- 대리점/직영센터 간 데이터 접근 범위
- 운송장번호 기반 외부 조회 권한
- 반품 사진에 개인정보가 포함될 가능성
- 위탁사/제3자 제공 구분
- 보유기간 미확정 개인정보
- 파기 정책 미확정 개인정보
- 정산·분쟁·사고 처리 목적 장기보관 정보

## 7. 🟠 주황 법무/개인정보보호 책임자 검토 항목 목록

- 문자/카카오/이메일 알림 발송 위탁
- 클라우드/서버/DB/로그 보관 위탁
- 택배사 API 연동
- 고객사 관리자와 대리점 관리자의 열람 범위
- 외부 AI, 분석 도구, 고객지원 도구 사용 시 국외 이전과 행태정보 처리
- 개인통관고유부호가 필요한 해외 반품·통관 업무의 별도 처리 기준
- 최종 고객/수취인의 권리 행사 요청 접수·처리 주체
- 아동 개인정보가 반품 접수자료에 포함되는 경우의 처리 기준

## 8. 🟡 노랑 운영정책 확정 필요 항목 목록

- 마스킹 기준
- 다운로드/엑셀 내보내기 제한
- 감사로그 보관 기간
- 휴면계정/탈퇴계정 처리
- 고객문의 녹취/첨부파일이 있는 경우 처리
- 쿠키와 접속 로그의 보관기간 및 거부 방법
- 업로드 원본, 검증 row, export 파일의 저장 위치와 자동 삭제 정책
- 방침 버전, 최초 시행일, 변경 공지 기간, 이전 방침 보관 방식
- 개인정보 보호책임자, 담당부서, 열람청구 접수부서, 문의 채널

## 9. 확인하지 못한 항목

- SmartReturn-platform의 실제 개인정보처리자/수탁자/공동처리자 계약 구조
- 실제 수탁사명, 재위탁 여부, 처리 항목, 보유기간, 국외 이전 여부
- 실제 클라우드 리전, 로그·백업·모니터링 도구, 고객지원 도구의 저장 위치
- 실제 문자/메신저/이메일 발송 사업자와 알림 발송 항목
- 실제 택배사 API 계약상 개인정보 제공 또는 위탁 구조
- 고객문의 녹취 사용 여부와 녹취 파일 보관 정책
- 개인통관고유부호가 필요한 해외 반품 또는 통관 업무 지원 여부
- 정보주체 권리 행사 요청의 접수 창구와 처리 책임자
- 정산·분쟁·사고 처리 목적 장기보관 정보의 법령·계약상 근거

## 10. 검증 결과

| 검증 항목 | 결과 | 비고 |
| --- | --- | --- |
| `git status --short` 확인 | 완료 | 신규 `docs/legal/`, 신규 `docs/reports/privacy-policy-draft-report.md`, 기존 미추적 `docs/reference/` 확인 |
| 생성/수정 파일 범위 확인 | 완료 | 이번 작업의 신규 작성 대상은 `docs/legal/privacy-policy-draft.md`, `docs/reports/privacy-policy-draft-report.md` |
| 개인정보 원문 복붙 여부 점검 | 완료 | 외부 원문 전문 복사 없이 항목 구조와 위험 포인트를 재구성 |
| 실제 개인정보/전화번호/주소/운송장번호 노출 여부 점검 | 완료 | 초안에서 실제 전화번호·주민등록번호·장문 숫자 식별자 패턴 미검출 |
| 회사명 잔류 여부 점검 | 완료 | 초안에서 외부 회사명 패턴 미검출 |
| 색상 태그가 고위험 항목에 붙었는지 확인 | 완료 | 🔴, 🟠, 🟡, 🟢 태그 적용 확인 |
| `git diff --check` 실행 | 완료 | 공백 오류 없음 |

## 11. 커밋 여부 판단용 변경 파일 목록

커밋은 수행하지 않았다.

이번 지시문 기준 커밋 후보:

- `docs/legal/privacy-policy-draft.md`
- `docs/reports/privacy-policy-draft-report.md`

주의:

- `docs/reference/`는 작업 시작 시점부터 미추적 상태로 확인된 참고 원문 확인 문서 묶음이다. 이번 초안 작성에서는 읽기와 비교 목적으로만 사용했다.

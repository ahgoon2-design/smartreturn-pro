# Codex 코드/권한/보안 검수 템플릿

실행대상: Codex (backend/코드 검수 레인)
선행: Fable 제작 + 똘망이 브라우저 검증 완료

> `<PROJECT_ROOT>/AGENTS.md`, `CODEX.md`를 먼저 읽는다. 브랜치 `smartreturn-pro` 기준. main 병합/동기화 제안 금지, push 금지. 검수 결과만 보고(임의 수정 금지, 수정 필요 시 항목별 보고).

## 1. 변경 파일 검토
- [ ] `git diff` 전수 확인 — 지시 범위 밖 파일 변경 없는지(무관 cleanup/리팩터 혼입 금지)
- [ ] 거대 diff/의도 불명 변경은 사유 요구

## 2. 기존 컴포넌트 재사용 여부
- [ ] SmartDataGrid/SmartPage 계열 사용 확인(antd Table/AG Grid 직접 사용 없음)
- [ ] 화면별 중복 구현(고객사 선택/저장 모달/에러 표기) 신규 발생 여부 — 발생 시 공통화 후보로 기록

## 3. 권한/role/permission/seed 정합성 (R1/R2 유형)
- [ ] BE `require_roles` 목록 ↔ FE `hasPermission` 가드 모순 없음("버튼 활성인데 403" 불가)
- [ ] `require_permission` 코드가 seed(`roles_permissions.py`)에서 대상 role에 실제 부여되어 있음
- [ ] role 목록에 있으나 permission이 없는 role(또는 반대) 발견 시 의도 확인 요청

## 4. scope 확인
- [ ] 모든 업무 쿼리/저장에 `resolve_effective_client_id`(또는 동등) 적용
- [ ] 고객 사용자가 타 client_id 요청 시 차단되는지(테스트 또는 코드 확인)
- [ ] agency_id 직접 저장 원칙(핵심 운영 테이블) 준수, request의 agency_id 무신뢰
- [ ] client_unit_id는 null 허용 유지(임의 컬럼/권한 테이블 추가 없음)

## 5. API payload ↔ backend schema 일치
- [ ] FE types(`frontend/src/types/*.ts`) ↔ BE schemas(`backend/app/schemas/*.py`) 필드명/타입 일치
- [ ] 신규/변경 필드가 양쪽 모두 반영되었는지

## 6. 테스트 추가/수정 여부
- [ ] 저장/상태 전이/권한 분기 변경에 대응하는 pytest 존재(없으면 보강 요구)
- [ ] 재고 정책 회귀 테스트: 처리완료 시 미반영, 마감 시 반영, idempotency

## 7. build/test 결과
- [ ] `python -m pytest`(영향 범위) 결과 확인 — 미실행은 "미실행"으로
- [ ] `npm --prefix frontend run build` 결과 확인
- [ ] `git diff --check`

## 8. 보안 파일/secret 커밋 방지
- [ ] staged/변경에 `.env`/`local.secret.json`/key/token/dist/__pycache__/tmp 미포함
- [ ] 코드/로그에 비밀번호·토큰 평문 없음(테스트 비번은 dev 명시 + 값 비출력)

## 9. 회귀 위험
- [ ] 공통 컴포넌트(SmartDataGrid 등) 변경 시 다른 사용 화면 영향 검토
- [ ] 재고 반영 시점/외부반출 후보/판정 enum 정본(REFURB_A/B/C·DEFECTIVE 정책) 불변 확인
- [ ] 기존 로그인/포털 분기(RouteGuard area) 미파손

## 10. 커밋 가능 여부 (보고 양식)
```
[검수 대상 커밋/변경] [변경 파일 수]
정합성: role-permission-seed / scope / payload (각 OK/문제)
테스트: (실행 결과 또는 미실행 사유)
보안: (OK/발견 항목)
회귀 위험: (없음/항목)
판정: 커밋 가능 / 수정 후 재검수 / 반려(사유)
※ 커밋·push는 사용자 승인 후에만.
```

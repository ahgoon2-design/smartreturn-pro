# 검증 보고서: SPEC-NNN <슬라이스명>
> 게이트 ④ 산출물. 검수자(Codex)가 작성한다. 파일명: `docs/reports/SPEC-NNN-verify.md` (스펙과 같은 NNN).
> 빌드 보고서(`docs/reports/SPEC-NNN-build.md`)가 없으면 검증을 시작하지 않는다.

## 1. 결과
통과 / 부분통과 / 실패 / 보류 (빨간불은 구현자에게 되돌린다)

## 2. 검증 대상
- 스펙: `docs/specs/SPEC-NNN-<영문슬러그>.md`
- 빌드 보고서: `docs/reports/SPEC-NNN-build.md`

## 3. 스펙 완료기준 항목별 충족/미충족
| # | 완료기준 | 충족/미충족 | 근거 |
| --- | --- | --- | --- |
| 1 | | | |

## 4. 실행한 검증과 결과
- `git status --short` / `git diff --check`:
- backend test:
- frontend build:
- 권한/테넌시/격리 작업이면 DB 실제 상태 확인:

## 5. 빨간 테스트 분류 (base-comparison)
| 테스트 | 의도된 차단 / 기존 실패 / 신규 회귀 | 근거 |
| --- | --- | --- |

## 6. 미실행 / 확인 필요
-

## 7. 판정 사유 / 구현자에게 되돌릴 항목
-

## 8. 검증 원칙 확인
- [ ] 검수 중 코드 수정 안 함
- [ ] 실패한 검증을 통과라고 쓰지 않음
- [ ] `git add` / commit 하지 않음

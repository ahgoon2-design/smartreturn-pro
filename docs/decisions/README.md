# docs/decisions — SmartReturn Pro
> 확정된 정책·설계 결정과 그 근거를 모은다. "왜 이렇게 했나"를 여기서 찾는다.

- `decision-log.md` — 결정 1건 = 한 줄 결정 + 근거 + 날짜. 미정 항목은 [미정]으로 표시.
- `tenancy-and-permission-model.md` — 권한/테넌시/격리 북극성. 권한·인증·격리 작업 전 필독.

## 규칙
- 새 정책을 확정하면 `decision-log.md`에 D-NNN으로 추가한다.
- 결정이 코드/스펙과 충돌하면 결정을 먼저 갱신한 뒤 구현한다.
- 모든 경로는 `<PROJECT_ROOT>` 기준 상대경로로 쓴다.

```text
신호등: 🟡 보완 후 통과

A1 red_gate 스위트는 구현·실행 통과했습니다.
다만 첫 pytest 실행이 만든 pytest-cache-files-284r3s_c 임시 디렉터리 접근 경고가 git status에 남아 있어, 정리 승인 전까지는 보완 후 통과로 봅니다.

1. 결과
- red_gate 마커 등록 완료
- 기존 테스트 함수에 마커만 추가
- 테스트 로직/assertion 변경 없음
- gap map 작성 완료: C:/smartreturn-pro/docs/reports/red-gate-a1-coverage-gap.md

2. 변경 파일
- C:/smartreturn-pro/pytest.ini
- C:/smartreturn-pro/backend/tests/test_auth_context.py
- C:/smartreturn-pro/backend/tests/test_auth_error_responses.py
- C:/smartreturn-pro/backend/tests/test_channel_api.py
- C:/smartreturn-pro/backend/tests/test_master_api_manage_warehouses.py
- C:/smartreturn-pro/backend/tests/test_master_api_readonly.py
- C:/smartreturn-pro/backend/tests/test_permissions.py
- C:/smartreturn-pro/backend/tests/test_return_intake_api.py
- C:/smartreturn-pro/backend/tests/test_seed_roles_permissions.py
- C:/smartreturn-pro/docs/reports/red-gate-a1-coverage-gap.md

3. 검증 결과
- 실행: backend\.venv\Scripts\python.exe -m pytest -m red_gate -p no:cacheprovider
- 결과: 60 passed, 377 deselected
- git diff --check: whitespace error 없음, CRLF 정규화 안내만 있음
- staged 파일 없음
- .env / backend/local.secret.json / config.json tracked 없음
- secret/token/password/password_hash 실값 기록 없음

4. 남은 주의
- 첫 pytest 실행 중 pytest-cache-files-284r3s_c 임시 디렉터리가 생성됨
- 승인 없이 삭제하지 않았음
- git status에 해당 디렉터리 접근 경고가 남음
- 다음 실행부터는 -p no:cacheprovider를 붙이면 재발 방지 가능

5. 최종 git status --short
 M backend/tests/test_auth_context.py
 M backend/tests/test_auth_error_responses.py
 M backend/tests/test_channel_api.py
 M backend/tests/test_master_api_manage_warehouses.py
 M backend/tests/test_master_api_readonly.py
 M backend/tests/test_permissions.py
 M backend/tests/test_return_intake_api.py
 M backend/tests/test_seed_roles_permissions.py
?? docs/reports/red-gate-a1-coverage-gap.md
?? pytest.ini
warning: could not open directory 'pytest-cache-files-284r3s_c/': Permission denied

6. 커밋/push
- 커밋하지 않음
- push하지 않음

7. 다음 1수
- pytest-cache-files-284r3s_c 정리 승인 후 클코 독립검수로 넘기는 것이 좋습니다.
```

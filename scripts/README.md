# scripts

이 폴더는 SmartReturn Pro 개발 보조 스크립트 후보 위치다.

운영 DB를 직접 수정하는 스크립트는 신중하게 관리한다. DB schema 변경은 임시 스크립트가 아니라 Alembic migration 기준으로 처리한다.

임시 스크립트는 커밋 전 제거하거나, 필요하면 `docs/reference`에 목적과 사용 조건을 기록한다.

## 개발 서버 실행 helper

- `scripts/run_backend_dev.bat`: backend dev server를 `127.0.0.1:8000`에서 실행한다.
- `scripts/run_frontend_dev.bat`: frontend dev server를 `127.0.0.1:5173`에서 실행한다.

두 helper 모두 secret/local 설정 파일 내용을 출력하지 않는다. 종료는 실행 창에서 `Ctrl+C`를 사용한다.
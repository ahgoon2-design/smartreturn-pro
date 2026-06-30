---
name: document-style
description: >-
  문서 작성, closeout, 문서 인덱스 수정, 완료 보고 작성 시 적용하는 문서 스타일 스킬.
  SmartReturn Pro 문서의 한글 작성 기준, 코드 식별자·DB 컬럼명·API path·enum 영문 유지
  기준, closeout 구성과 표현 방식을 정리하므로 문서 산출물이 생기는 작업 시 반드시 이
  스킬을 적용한다.
---

# Document Style Skill

## 목적

SmartReturn Pro 문서 작성, closeout 작성, 문서 인덱스 수정 시 따르는 언어와 구조 기준이다.

## 언어 기준

- 문서 본문은 한글로 작성한다.
- 완료 보고도 한글로 작성한다.
- 파일명은 영어와 케밥 케이스를 사용할 수 있다.
- 코드 식별자, DB 컬럼명, API path, enum 값, 함수명은 영어를 유지할 수 있다.
- 영어 요약본은 사용자가 별도로 요청할 때만 작성한다.

## 보안 기준

문서에는 아래 값을 쓰지 않는다.

- 실제 secret
- 실제 token 전체값
- 실제 password
- DB password
- password_hash
- `.env` 내용
- `backend/local.secret.json` 내용

## closeout 문서 기본 구성

closeout 문서는 작업 성격에 따라 아래 항목을 짧게 포함한다.

- 문서 목적
- 구현 또는 검증 범위
- 환경 또는 전제
- 수행한 작업
- 검증 결과
- 보안 확인
- 미구현 또는 제외 범위
- 후속 작업

수동 검증 closeout에는 실제 확인한 HTTP status, result_code, 핵심 상태값만 기록한다. token, password, stack trace는 쓰지 않는다.

## 문서 인덱스 연결

새 기준 문서 또는 closeout 문서를 만들면 가능한 경우 `docs/smartreturn-pro-doc-index.md`에 링크를 추가한다.

인덱스 구조가 명확하지 않으면 무리하게 재구성하지 않고 자연스럽게 추가 가능한 위치에만 추가한다.

## 문서 작성 주의

- 기존 SmartReturn 문서를 그대로 복사하지 않는다.
- SmartReturn Pro 기준으로 재정리한다.
- 기존 문서와 충돌하면 `AGENTS.md`와 최신 Pro 기준 문서를 우선한다.
- 문서에 추정 내용을 단정적으로 쓰지 않는다.
- API 응답 필드가 부족하거나 애매하면 “추가 검토 필요”로 표시한다.

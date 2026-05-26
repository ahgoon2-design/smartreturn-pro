# local_agent

이 폴더는 SmartReturn Pro Local Agent 후보가 들어갈 위치다.

Local Agent는 사운드, 라벨, 프린터, 장치 제어를 담당한다. 재고를 직접 변경하지 않으며 서버 DB에 직접 접근하지 않는다. 재고 반영은 서버 업무 확정 흐름과 `inventory_events` 기준을 따른다.

## 설정 파일 원칙

- `config.json`은 실제 로컬 설정 파일이므로 커밋 금지다.
- `config.example.json`만 커밋 가능하다.
- 실제 프린터명, 실제 서버 주소, 실제 로컬 경로는 예시 파일에 넣지 않는다.

## 현재 단계

이번 단계에서는 실제 Local Agent 구현, 패키징, 프린터 연동, 사운드 재생, 장치 제어 코드를 만들지 않았다. 실제 구현은 후속 단계에서 진행한다.

⚠ ARCHIVE — 과거 검토 기록, 운영 기준 아님.

# Local Agent 라벨 출력 연동 기준

## 1. 문서 목적

이 문서는 기존 SmartReturn Local Agent를 SmartReturn Pro 반품처리 라벨 출력에 재사용하기 위한 1차 연동 기준을 정리한다.

브라우저는 프린터를 직접 제어하지 않는다. 프린터, 라벨, 사운드, 카메라 같은 로컬 장치는 Local Agent를 통해 처리한다. Local Agent가 미연결이거나 출력에 실패해도 판정 저장은 롤백하지 않고, 라벨 상태만 `LOCAL_AGENT_NOT_CONNECTED`, `PRINT_FAILED`, `PRINT_PENDING` 같은 상태로 표시한다.

## 2. 기존 Local Agent 확인 결과

확인한 SmartReturn Pro 경로:

- `C:\smartreturn-pro\local_agent`

확인한 SmartReturn Pro 파일:

- `local_agent/README.md`
- `local_agent/config.example.json`

확인한 기존 SmartReturn 후보 경로:

- `C:\donghyun-logistics-platform`
- `C:\donghyun-logistics-platform\local_tools\smartreturn_local_agent`
- `C:\SmartReturn`
- `C:\smartreturn`

확인 결과:

- `C:\donghyun-logistics-platform` 저장소는 존재한다.
- 지정 후보인 `C:\donghyun-logistics-platform\local_tools\smartreturn_local_agent`는 현재 PC에서 확인되지 않았다.
- `main.py`, `api_server.py`, `agent_service.py`, `printer_service.py`, `label_renderer.py`, `sound_service.py`, `diagnostics_service.py`, `run_agent.bat`, `build_windows.bat`, `version.json` 파일은 확인한 후보 경로에서 발견되지 않았다.
- `C:\smartreturn-pro\local_agent`는 현재 placeholder 성격이며 실제 API 서버 구현은 없다.
- `config.example.json`에는 `printer.enabled`, `printer.dry_run`, `printer.printer_name`, `label.output_dir`, 라벨 크기 후보 설정이 있다.
- 실제 `config.json` 내용은 확인하지 않았고 문서에 기록하지 않는다.

확인된 기존 Local Agent API:

- 없음

따라서 다음 구현에서는 존재가 확인되지 않은 `/health`, `/printers`, `/labels/print` 같은 endpoint를 임의로 호출하지 않는다. 기존 SmartReturn Local Agent 구현 경로가 추가로 제공되면 해당 코드의 실제 endpoint와 payload를 다시 확인한 뒤 연결한다.

## 3. SmartReturn Pro에서 재사용할 API

현재 PC에서 재사용 가능한 기존 Local Agent API는 확인되지 않았다. SmartReturn Pro에는 `local_agent_base_url = "http://127.0.0.1:8765"` 설정 후보가 있으나, 이 값은 호출 가능한 API 계약을 보장하지 않는다.

다음 구현의 기본 원칙:

- 실제 Local Agent endpoint가 확인되기 전까지는 라벨 출력 버튼을 비활성 또는 미연결 상태로 표시한다.
- 브라우저 `window.print` 방식은 사용하지 않는다.
- Local Agent 구현체가 확인되면 기존 endpoint 이름과 payload를 그대로 우선한다.
- Pro와 기존 payload가 다르면 프론트 또는 별도 adapter 계층에서 변환한다.

## 4. Health API 연동 기준

기존 Health endpoint는 아직 확인되지 않았다. 구현체가 확인되면 실제 endpoint 기준으로 다음 값을 표시한다.

- 연결됨/미연결
- Local Agent version
- printer enabled 여부
- dry-run 여부
- 기본 프린터 설정 여부
- 오류 메시지

표시 원칙:

- 실제 프린터명, 로컬 경로, 설정 파일 내용은 과도하게 노출하지 않는다.
- 연결 실패는 작업자가 바로 알 수 있게 표시하되 판정 저장을 막지 않는다.
- Health 응답 구조가 없으면 새 계약을 상상하지 않고 미연결 상태로 둔다.

## 5. 라벨 출력 payload 매핑

현재 SmartReturn Pro 반품처리 task에는 다음 필드가 있다.

| SmartReturn Pro 필드 | 용도 | 기존 Local Agent 매핑 |
| --- | --- | --- |
| `return_management_no` | 반품관리번호 | 기존 payload 확인 후 adapter 필요 |
| `return_label_no` | 라벨번호 | 기존 payload 확인 후 adapter 필요 |
| `judgement_status` | 판정 상태 | 기존 payload 확인 후 adapter 필요 |
| `product_code` | 상품코드 | 기존 payload 확인 후 adapter 필요 |
| `barcode` | 바코드 | 기존 payload 확인 후 adapter 필요 |
| `product_name` | 상품명 | 기존 payload 확인 후 adapter 필요 |
| `return_tracking_no` | 반품 운송장번호 | 기존 payload 확인 후 adapter 필요 |
| `client_name` | 고객사명 표시 후보 | 선택 전달 후보 |
| `print_copies` | 출력 매수 | 기존 payload 확인 후 adapter 필요 |

현재 기존 Local Agent의 라벨 payload 구조가 확인되지 않았으므로 위 매핑은 Pro 쪽 후보 필드 목록이다. 실제 구현 시에는 기존 Local Agent가 요구하는 필드명을 우선하고, Pro 필드를 그 구조에 맞게 변환한다.

## 6. 실패 처리 정책

라벨 출력 실패 후보 상태:

- `LOCAL_AGENT_NOT_CONNECTED`
- `PRINTER_DISABLED`
- `LABEL_PRINT_FAILED`
- `LABEL_PRINT_TIMEOUT`
- `LABEL_PRINT_BAD_REQUEST`

정책:

- 출력 실패는 판정 저장을 롤백하지 않는다.
- 라벨 출력 대상 row는 재출력할 수 있어야 한다.
- 실패 상태는 그리드와 상세 패널에 명확히 표시한다.
- Local Agent 응답의 내부 예외나 stack trace는 화면에 표시하지 않는다.
- 실제 token, secret, password, config 내용은 로그와 화면에 출력하지 않는다.

## 7. 백엔드 라벨 상태와의 관계

현재 SmartReturn Pro 백엔드는 판정 저장 시 다음 필드를 사용한다.

- `return_management_no`
- `return_label_no`
- `label_print_required`
- `label_print_status`
- `label_printed_at`

현재 정책:

- `REFURB`, `SAMPLE`, `MANUFACTURER_RETURN`, `HOLD`는 기본 라벨 출력 대상이다.
- `GOOD`은 기본 라벨 미출력 대상이다.
- `DISPOSAL`은 1차 기본 미출력이며 후속 선택 출력 후보이다.
- 라벨 출력 대상이면 `RTN-{YYYYMMDD}-{row_id}` 형식의 번호가 생성된다.
- Local Agent 실연동 전에는 라벨 상태가 `LOCAL_AGENT_NOT_CONNECTED`로 표시된다.

후속 API 후보:

- `POST /api/returns/processing/tasks/{task_id}/label-print-status`

이 API는 Local Agent 출력 성공/실패 후 `label_print_status`, `label_printed_at`을 갱신하기 위한 후보이다. 이번 문서 작업에서는 구현하지 않는다.

## 8. 프론트 다음 구현 범위

다음 목표추진 작업의 권장 범위:

- Local Agent 구현체 경로 재확인
- 실제 health endpoint가 있으면 연결 상태 표시
- 실제 라벨 출력 endpoint가 있으면 라벨 출력 요청 연결
- 라벨 출력 대상 row에서 출력/재출력 버튼 표시
- Local Agent 미연결 또는 프린터 비활성 상태 안내
- 출력 성공/실패 메시지 표시
- 필요 시 backend 라벨 상태 업데이트 API 설계 및 구현

기존 endpoint가 끝내 확인되지 않으면 다음 구현은 미연결 상태 표시와 재출력 버튼 비활성까지만 진행한다.

## 9. 구현하지 않을 것

- 새 Local Agent 서버 구현
- 브라우저 `window.print`
- 라벨 디자인 고도화
- 카메라 연동
- 복잡한 프린터 선택 UI
- 클라우드 프린팅
- DB schema/migration 변경
- 실제 `config.json` 내용 노출

## 10. 결론

SmartReturn Pro는 브라우저 직접 출력이 아니라 Local Agent를 통해 라벨 출력 흐름을 연결한다. 다만 현재 PC에서 지정된 기존 SmartReturn Local Agent 구현체와 실제 endpoint는 확인되지 않았다.

따라서 다음 작업은 기존 Local Agent 구현체 경로를 다시 확보한 뒤 진행하는 것이 가장 안전하다. 구현체가 확인되면 실제 endpoint와 payload를 기준으로 adapter를 만들고, 확인되지 않으면 `/returns/processing` 화면에는 Local Agent 미연결 상태와 재출력 비활성 UI만 연결한다.

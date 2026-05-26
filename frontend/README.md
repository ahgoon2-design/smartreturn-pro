# frontend

이 폴더는 SmartReturn Pro 프론트엔드 코드가 들어갈 예정 위치다.

향후 React + TypeScript + Vite 앱은 `frontend/src` 아래에 구성한다. 이번 단계에서는 React 앱, `package.json`, 설치된 패키지, 실행 코드를 만들지 않았다.

## 예정 구조

- `src/components/common`
- `src/components/layout`
- `src/components/grid`
- `src/components/modal`
- `src/components/lookup`
- `src/components/scan`
- `src/pages`
- `src/services`
- `src/hooks`
- `src/types`
- `src/utils`
- `src/styles`

## 공통 UI 원칙

- 업무 화면에서 `AgGridReact`를 직접 사용하지 않는다.
- `SmartDataGrid`, `SmartEditableDataGrid`, `SmartExcelPreviewGrid`를 사용한다.
- `SmartWorkLayout`, `SmartActionBar`, `SmartInfoPanel`, `SmartModalShell`을 우선한다.
- 화면별 임시 table, input, button, modal, select를 만들지 않는다.

## 구현 전 확인

실제 구현 전에는 [공통 UI 컴포넌트 props/상태 설계](../docs/ui/smartreturn-pro-common-component-props.md)를 먼저 읽는다.

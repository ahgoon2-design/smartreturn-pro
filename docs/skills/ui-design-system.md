---
name: ui-design-system
description: >-
  Ant Design 기반 공통 컴포넌트 조합과 업무 화면 밀도·톤을 다루는 작업 시 적용하는 공통 UI 스킬.
  SmartPage·SmartToolbar·SmartDataSection 등 공통 컴포넌트 조합 순서, 새 화면을 공통 컴포넌트로
  조립하는 기준, 화면 밀도와 모달/폼/버튼 통일 기준을 정리한다. 색상·아이콘·레이아웃 철학은
  smartreturn-screen-design-system을 따른다. 공통 컴포넌트 조합과 화면 밀도를 결정하는 작업 시
  반드시 이 스킬을 적용한다.
---

# UI Design System Skill

## 목적

SmartReturn Pro의 화면 디자인과 공통 UI 컴포넌트 기준을 정리한다.

## 기본 방향

- Ant Design을 기능성 UI의 기본으로 사용한다.
- SmartReturn 공통 CSS와 공통 컴포넌트로 업무 화면의 밀도와 톤을 맞춘다.
- Mantine은 당장 설치하지 않는다.
- Mantine 스타일의 부드러운 카드, 간격, 작업 패널 느낌은 공통 CSS와 컴포넌트로 흡수한다.
- 화면별 임시 CSS 남발을 피한다.
- 새 화면을 만들기 전 기존 공통 컴포넌트로 조합 가능한지 먼저 확인한다.

## 공통 레이아웃 후보

- `SmartPage`
- `SmartPageHeader`
- `SmartToolbar`
- `SmartDataSection`
- `SmartActionBar`
- `SmartSummaryCard`
- `SmartStatusBadge`
- `SmartModalShell`
- `SmartErrorNotice`
- `SmartFormSection`

반복되는 UI 문제는 화면별 튜닝보다 공통 컴포넌트 개선으로 해결한다.

## 새 화면 구성 순서

새 업무 화면은 화면별 임시 레이아웃으로 시작하지 않는다.

관리 화면은 아래 순서로 먼저 조합한다.

1. `SmartPage`
2. `SmartPageHeader`
3. `SmartToolbar` 또는 간단 필터 영역
4. `SmartDataSection`
5. `SmartDataGrid`
6. `SmartModalShell`
7. `SmartActionBar` 또는 화면 하단 action 영역

작업자 스캔 화면은 `SmartScanPanel`, 큰 입력, 큰 피드백, 작업 대상 grid, 상세/action 영역 순서로 구성한다.

화면별 CSS를 늘리기 전에 공통 `smart-*` class 또는 공통 컴포넌트로 해결할 수 있는지 먼저 확인한다. 같은 문제가 두 화면 이상에서 반복되면 개별 화면을 고치지 말고 공통 컴포넌트를 보정한다.

## 색상 기준

- 정상/성공: 초록 계열
- 경고: 노랑 또는 주황 계열
- 오류: 빨강 계열
- 대기: 회색 또는 파랑 계열
- 비활성: 낮은 대비의 회색
- 처리중: 파랑 계열과 loading indicator

색상만으로 의미를 전달하지 않고, 한글 문구와 badge를 함께 사용한다.

## 버튼 기준

- 주요 버튼은 화면 목적 기준으로 하나만 강하게 표시한다.
- 보조 버튼은 과하게 강조하지 않는다.
- 위험 버튼은 색상과 문구를 명확히 구분한다.
- 반복 작업 화면에서는 작업자가 매번 판단해야 하는 버튼 수를 줄인다.

## 카드 기준

- 과한 카드 남발을 금지한다.
- 화면을 너무 조각내지 않는다.
- 요약, 상태, 작업 영역처럼 구분이 필요한 곳만 카드화한다.
- 그리드가 주인공인 화면에서 안내 카드가 그리드를 밀어내면 실패다.

## 모달 기준

- `SmartModalShell` 기준으로 크기, 버튼 위치, footer, spacing을 통일한다.
- 화면마다 제각각 modal을 만들지 않는다.
- 위험 작업은 확인 단계를 두되 반복 업무 속도를 해치지 않는다.
- 단순 확인 대화상자는 `Modal.confirm`을 사용할 수 있으나, 입력/수정/등록 모달은 `SmartModalShell`을 우선 사용한다.

## 폼 기준

- label, input width, 필수값 표시, 오류 메시지 위치를 통일한다.
- 고객사, 상품, 창고, 공통코드 선택은 화면별 단순 select를 남발하지 않는다.
- 향후 `SmartLookupModal`, `SmartCommonCodeSelect`로 전환 가능하게 설계한다.
- 기존 공통 lookup/input이 없어서 임시 Select를 쓰는 경우에도 API scope, active 여부, 고객사/창고 scope 검증을 유지하고 후속 전환 후보로 보고한다.

## 화면 밀도

- 1366x768 기준에서 주요 조회, 작업, 버튼이 보여야 한다.
- 너무 큰 안내문이나 배너를 남발하지 않는다.
- 관리자 화면은 필터, 그리드, 상세 패널 중심으로 만든다.
- 작업자 화면은 큰 입력, 큰 피드백, 빠른 focus 이동을 우선한다.

## 아이콘 기준

- 작은 UI 아이콘은 Ant Design icon 같은 SVG icon library를 사용한다.
- 이미지 파일은 로고, 상품사진, 샘플이미지처럼 실제 이미지가 필요한 경우에만 사용한다.

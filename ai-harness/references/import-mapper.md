# Import Mapper Reference

## Read First

- `docs/skills/import-preview.md`
- `docs/db/smart-import-mapper-pipeline.md`
- `docs/db/smartreturn-pro-db-and-import-policy.md`
- `docs/skills/channel-return-auto-collection.md`

## Rules

- Excel/Google Sheet/CSV/API import는 공용 import pipeline을 우선 재사용한다.
- used range를 그대로 신뢰하지 않는다.
- 공백, "-", 수식 결과 빈값, 의미 없는 잔여 행은 제외한다.
- 원본 row order와 row_no를 보존한다.
- 운송장번호, 날짜, 전화번호, 사업자번호, 바코드, 상품코드는 canonical 값으로 정규화한다.
- 저장 가능, 제외, 검토 필요를 분리한다.
- 고객사 선택 전 업로드/저장을 막는다.

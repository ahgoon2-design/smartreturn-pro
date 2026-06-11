# 008 보고 - 외부반출 반출확정(쓰기) 검증

- 화면: `/returns/external-outbound` + outbound confirm API / ahgoon / 브랜치 smartreturn-pro
- 대상: `V3WRITE-RTN-002` (row#12, REFURB_A, rmn RTN-20260611-12) 단건만

## 결과: 통과 (PASS)

| 항목 | 결과 |
|---|---|
| 외부반출 후보에 테스트 건 표시 | ✅ row#12 READY |
| REFURB_A/B/C·MANUFACTURER_RETURN 후보 포함 | ✅ 전체 후보 judgeSet=[REFURB_A, MANUFACTURER_RETURN] |
| GOOD/DISPOSAL/HOLD/DEFECTIVE 오포함 없음 | ✅ badIncluded=0 |
| 반품관리번호 1:1 스캔/확정 | ✅ scanned_numbers=[RTN-20260611-12] |
| 반출확정 성공 | ✅ CONFIRMED, batch EXOB-20260611-6F28B76D |
| 확정 후 결과 안내 명확 | ✅ "외부반출을 확정했습니다. 현재고는 변경하지 않았습니다." |
| 동일 건 중복 반출 방지 | ✅ 반출 후 외부반출 후보(client_id=8)=0건, ob=CONFIRMED |

## 참고(정책 관찰)
- REFURB_A는 일마감(007)에서 이미 재고 반영(refurb 라우팅 창고)되었고, 외부반출 확정은 "현재고 미변경"으로 명시 처리됨. 결과 안내가 명확하므로 결함 아님(재고차감 정책은 판정/창고 모델에 따른 것으로, 무음 변경 없음).

## 안전 격리
- row_ids=[12] + scanned_numbers 단건. 기존 후보(타 고객사) 무영향. 다건/일괄 없음.

## 실제 버그 vs 데이터/위험
- 버그 없음.

## 수정 파일
- 없음.

## 실행 조작
- Playwright: /returns/external-outbound 진입 → candidates 정합 확인 → external-outbound/confirm {row_ids:[12], scanned_numbers:[RTN-20260611-12]} → 후보/history 재확인. (백엔드 절대주소 API)

## 다음
- 성공 → `009-write-flow-final-report.md` 종합.

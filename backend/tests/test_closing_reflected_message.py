"""일마감 재고반영 완료 메시지 문구가 판정/재고상태에 맞게 표시되는지 검증(표시 전용)."""

from app.services.return_intake_service import _closing_reflected_message


def test_closing_reflected_message_per_judgement():
    assert _closing_reflected_message("GOOD") == "정상재고에 반영했습니다."
    assert _closing_reflected_message("REFURB_A") == "리퍼A 재고에 반영했습니다."
    assert _closing_reflected_message("REFURB_B") == "리퍼B 재고에 반영했습니다."
    assert _closing_reflected_message("REFURB_C") == "리퍼C 재고에 반영했습니다."
    assert _closing_reflected_message("REFURB") == "리퍼 재고에 반영했습니다."
    assert _closing_reflected_message("MANUFACTURER_RETURN") == "제조사반품 재고에 반영했습니다."
    assert _closing_reflected_message("SAMPLE") == "샘플 재고에 반영했습니다."
    assert _closing_reflected_message("DISPOSAL") == "폐기 재고에 반영했습니다."


def test_closing_reflected_message_fallback():
    # 판정값이 없으면 정상재고, 알 수 없는 값이면 후속 처리 문구로 오해 없게 표시
    assert _closing_reflected_message(None) == "정상재고에 반영했습니다."
    assert _closing_reflected_message("UNKNOWN_X") == "후속 처리 대상으로 반영했습니다."

"""consensus.py mock 스모크 테스트 (API 키 불필요).

pytest로 실행하거나, 직접 `python test_consensus.py`로도 실행 가능.
"""
from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent))

import consensus  # noqa: E402


SAMPLE_DRAFT = """# 샘플 지시문

## 목적
재고 화면 한 줄 설명.

## 금지
- git add . 금지
"""


def _make_temp_dir() -> Path:
    root = Path(__file__).resolve().parent / "consensus-runs" / "test-temp"
    root.mkdir(parents=True, exist_ok=True)
    path = root / uuid4().hex
    path.mkdir()
    return path


def _write_draft(tmp: Path) -> Path:
    p = tmp / "draft.md"
    p.write_text(SAMPLE_DRAFT, encoding="utf-8")
    return p


def test_mock_converge_approves_round2():
    tmp = _make_temp_dir()
    draft = _write_draft(tmp)
    result = consensus.run_consensus(draft, rounds=3, out_dir=tmp / "runs", reviser="claude", mock="converge")
    assert result["status"] == "APPROVED", result["status"]
    assert result["rounds_run"] == 2, result["rounds_run"]
    run_dir = tmp / "runs" / result["run_id"]
    assert (run_dir / "final-instruction.md").is_file(), "final-instruction.md 가 생성돼야 함"
    # 라운드1 개정 diff가 남아야 함(개정이 실제로 일어났는지)
    assert (run_dir / "round-01" / "diff-to-next.patch").is_file()


def test_mock_stubborn_needs_user_decision():
    tmp = _make_temp_dir()
    draft = _write_draft(tmp)
    result = consensus.run_consensus(draft, rounds=3, out_dir=tmp / "runs", reviser="claude", mock="stubborn")
    assert result["status"] == "NEEDS_USER_DECISION", result["status"]
    assert result["rounds_run"] == 3, result["rounds_run"]
    run_dir = tmp / "runs" / result["run_id"]
    assert not (run_dir / "final-instruction.md").exists(), "미합의 시 final 미생성이어야 함"
    assert (run_dir / "review-summary.md").is_file()


def test_canonical_hash_ignores_newline_and_trailing_ws():
    a = "line one\nline two\n"
    b = "line one  \r\nline two\r\n\r\n"  # 끝공백/CRLF/끝빈줄만 다름
    assert consensus.canonical_hash(a) == consensus.canonical_hash(b)
    # 실제 내용이 다르면 해시도 달라야 함
    assert consensus.canonical_hash(a) != consensus.canonical_hash("line one\nline THREE\n")


def test_run_id_unique_same_second():
    ids = {consensus.make_run_id() for _ in range(50)}
    assert len(ids) == 50, "같은 초에 만들어도 run-id가 겹치면 안 됨"


def test_run_dirs_do_not_collide():
    tmp = _make_temp_dir()
    draft = _write_draft(tmp)
    r1 = consensus.run_consensus(draft, rounds=2, out_dir=tmp / "runs", reviser="claude", mock="stubborn")
    r2 = consensus.run_consensus(draft, rounds=2, out_dir=tmp / "runs", reviser="claude", mock="stubborn")
    assert r1["run_id"] != r2["run_id"]


def test_generator_mock_work_instruction_is_single_text_block():
    result = consensus.generate_prompt_document(consensus.GEN_MODE_WORK, "반품 화면 개선", mock="converge")
    assert result.startswith("```text\n")
    assert result.endswith("\n```")
    assert "C:\\smartreturn-pro" in result
    assert "AGENTS.md" in result
    assert "git add . 금지" in result
    assert "commit/push 금지" in result


def test_generator_mock_review_instruction_blocks_file_edits():
    result = consensus.generate_prompt_document(consensus.GEN_MODE_REVIEW, "완료보고서", mock="converge")
    assert result.startswith("```text\n")
    assert "작업 보고서를 그대로 믿지 말고" in result
    assert "파일 수정 금지" in result
    assert "git add/commit/push 금지" in result


def test_generator_mock_decision_instruction_does_not_auto_run_next_task():
    result = consensus.generate_prompt_document(consensus.GEN_MODE_DECISION, "검수보고서", mock="converge")
    assert result.startswith("```text\n")
    assert "커밋 가능 여부" in result
    assert "자동 실행하지 않는다" in result


def test_as_text_code_block_removes_nested_fences():
    result = consensus.as_text_code_block("```markdown\nhello\n```\n\n```bad\nx\n```")
    assert result.startswith("```text\n")
    assert result.endswith("\n```")
    assert "~~~bad" in result


def _run_all() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())

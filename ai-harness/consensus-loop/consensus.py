#!/usr/bin/env python3
"""지시문 생성·합의 엔진 (SmartReturn Pro 똘망이).

== 주 사용법: GUI ==
consensus_gui.py 가 주 인터페이스다.
  - 사용자가 초안/보고서를 화면에 붙여넣는다.
  - 버튼 1회 클릭으로 지시문 생성 1회를 수행한다.
  - 결과를 사람이 복사해 Claude Code/Codex에 붙여넣는다.
  - 자동 실행, 자동 커밋, 자동 푸시는 하지 않는다.
  - 파일 기반 자동 루프가 주 목적이 아니다.

== 레거시 CLI: 합의 루프 ==
이 모듈의 run_consensus() / main()은 ChatGPT·Claude가 지시문 초안을
최대 N라운드 상호검토해 final-instruction.md를 확정하는 CLI 합의 루프다.
필요 시 --mock 옵션으로 로직만 확인할 수 있다.

핵심 설계(레거시 CLI):
- API 직접 호출: 이 스크립트가 양쪽 API를 직접 호출한다.
- 단일 draft 소유: 오케스트레이터가 draft를 하나만 들고 양쪽에 같은 바이트를 준다.
- 정규화 해시: 줄바꿈/끝공백/인코딩을 통일(canonical)한 뒤 sha256 한다.
- 수렴 보장: must_fix(차단성)와 should_fix(권고)를 분리한다.
- 개정 최소화: 개정자는 must_fix만 최소 수정하고 나머지는 원문 그대로 둔다.

키는 환경변수에서만 읽는다(ANTHROPIC_API_KEY, OPENAI_API_KEY). 코드/파일에 하드코딩하지 않는다.
이 도구는 지시문을 '검토'할 뿐 실행하지 않는다.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

# 프로바이더 모델 상수(교체 쉽게 한 곳에 모음).
ANTHROPIC_MODEL = "claude-opus-4-8"
OPENAI_MODEL = "gpt-4o"

VERDICT_APPROVE = "APPROVE"
VERDICT_CHANGES = "CHANGES_REQUIRED"
VERDICT_BLOCKED = "BLOCKED"

GEN_MODE_WORK = "work"
GEN_MODE_REVIEW = "review"
GEN_MODE_DECISION = "decision"

GENERATION_MODES = {
    GEN_MODE_WORK: "작업지시문 생성",
    GEN_MODE_REVIEW: "검수지시문 생성",
    GEN_MODE_DECISION: "최종판단/다음작업 생성",
}

SMARTRETURN_PRO_ROOT = r"C:\smartreturn-pro"


# ---------------------------------------------------------------------------
# 정규화 / 해시
# ---------------------------------------------------------------------------
def canonical(text: str) -> str:
    """줄바꿈/끝공백/끝빈줄을 통일한 canonical 형태로 만든다."""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip() for ln in t.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


def canonical_hash(text: str) -> str:
    """canonical 형태의 sha256 16진 해시."""
    return hashlib.sha256(canonical(text).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# JSON 방어적 파싱
# ---------------------------------------------------------------------------
def extract_json(text: str) -> dict:
    """모델 출력에서 첫 '{' ~ 마지막 '}' 구간을 잘라 JSON으로 파싱한다."""
    if not text:
        raise ValueError("빈 응답에서 JSON을 추출할 수 없습니다.")
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("응답에서 JSON 객체를 찾지 못했습니다.")
    return json.loads(text[start : end + 1])


def normalize_review(raw: dict, reviewer: str, round_no: int, draft_hash: str) -> dict:
    """리뷰 JSON을 표준 형태로 정규화한다(누락 필드 보정)."""
    def as_list(value):
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        if value:
            return [str(value).strip()]
        return []

    verdict = str(raw.get("verdict", VERDICT_CHANGES)).strip().upper()
    if verdict not in {VERDICT_APPROVE, VERDICT_CHANGES, VERDICT_BLOCKED}:
        verdict = VERDICT_CHANGES
    return {
        "reviewer": reviewer,
        "round": round_no,
        "draft_hash": str(raw.get("draft_hash", "")).strip(),
        "verdict": verdict,
        "risk_level": str(raw.get("risk_level", "MEDIUM")).strip().upper(),
        "must_fix": as_list(raw.get("must_fix")),
        "should_fix": as_list(raw.get("should_fix")),
        "approved": bool(raw.get("approved", False)),
        "summary": str(raw.get("summary", "")).strip(),
    }


# ---------------------------------------------------------------------------
# 리뷰어 점검 기준 분담 (지시문 §5)
# ---------------------------------------------------------------------------
CLAUDE_FOCUS = (
    "구조 타당성, 정책/리스크 누락(특히 데이터 누수), UX/흐름 충돌, "
    "범위 과다, 스펙 완성도, 모호한 결정점"
)
CHATGPT_FOCUS = (
    "역할/실행대상 충돌, AGENTS.md 위반, git/secret 위험, 금지사항 누락, "
    "보안 1등급 표시 누락, 완료 조건 모호성"
)


def _review_prompt(draft: str, draft_hash: str, round_no: int, focus: str, prev_must_fix: list[str]) -> str:
    prev_block = ""
    if round_no >= 2 and prev_must_fix:
        joined = "\n".join(f"- {m}" for m in prev_must_fix)
        prev_block = (
            "\n\n[이전 라운드 미해결 must_fix]\n"
            f"{joined}\n"
            "2라운드부터는 위 미해결 항목과 새로 생긴 '퇴행(regression)'만 must_fix로 올린다. "
            "새로운 사소한 트집을 must_fix로 넣지 않는다(should_fix로 분류)."
        )
    return (
        "너는 지시문(업무 지시 문서) 상호검토자다. 아래 초안을 점검하라.\n"
        f"너의 1차 점검 책임 영역: {focus}\n"
        f"현재 라운드: {round_no}\n"
        f"draft_hash(그대로 echo 할 값): {draft_hash}\n"
        "must_fix = 통과를 막아야 하는 차단성 결함만. should_fix = 권고(차단 아님).\n"
        f"{prev_block}\n\n"
        "반드시 아래 키만 가진 JSON 객체 하나만 출력하라(설명/마크다운 금지):\n"
        '{"reviewer": "<이름>", "round": <정수>, "draft_hash": "<위 값 그대로>", '
        '"verdict": "APPROVE|CHANGES_REQUIRED|BLOCKED", "risk_level": "LOW|MEDIUM|HIGH", '
        '"must_fix": ["..."], "should_fix": ["..."], "approved": true|false, "summary": "한 줄"}\n\n'
        "차단성 결함이 없으면 verdict=APPROVE, must_fix=[] 로 한다.\n"
        "----- 초안 시작 -----\n"
        f"{draft}\n"
        "----- 초안 끝 -----\n"
    )


# ---------------------------------------------------------------------------
# 실제 프로바이더 호출 (SDK는 lazy import → mock 모드는 SDK 없이도 동작)
# ---------------------------------------------------------------------------
def call_claude_review(draft: str, draft_hash: str, round_no: int, prev_must_fix: list[str]) -> dict:
    import anthropic  # lazy

    client = anthropic.Anthropic()  # ANTHROPIC_API_KEY 환경변수에서 읽음
    prompt = _review_prompt(draft, draft_hash, round_no, CLAUDE_FOCUS, prev_must_fix)
    resp = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    return normalize_review(extract_json(text), "claude", round_no, draft_hash)


def call_chatgpt_review(draft: str, draft_hash: str, round_no: int, prev_must_fix: list[str]) -> dict:
    from openai import OpenAI  # lazy

    client = OpenAI()  # OPENAI_API_KEY 환경변수에서 읽음
    prompt = _review_prompt(draft, draft_hash, round_no, CHATGPT_FOCUS, prev_must_fix)
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You output only a single valid JSON object."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},  # JSON 모드로 구조적 출력 강제
    )
    text = resp.choices[0].message.content or ""
    return normalize_review(extract_json(text), "chatgpt", round_no, draft_hash)


def _revise_prompt(draft: str, must_fix: list[str], should_fix: list[str]) -> str:
    must_block = "\n".join(f"- {m}" for m in must_fix) or "(없음)"
    should_block = "\n".join(f"- {s}" for s in should_fix) or "(없음)"
    return (
        "너는 지시문 개정자다. 아래 초안에서 must_fix 항목만 최소 수정하고, "
        "나머지 문장/구조/표현은 원문 그대로 보존하라. should_fix는 무해할 때만 반영한다.\n"
        "출력은 개정된 지시문 전문(마크다운)만. 설명/주석/코드펜스 금지.\n\n"
        f"[must_fix - 반드시 해결]\n{must_block}\n\n"
        f"[should_fix - 권고]\n{should_block}\n\n"
        "----- 초안 시작 -----\n"
        f"{draft}\n"
        "----- 초안 끝 -----\n"
    )


def revise_with_claude(draft: str, must_fix: list[str], should_fix: list[str]) -> str:
    import anthropic  # lazy

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=8000,
        messages=[{"role": "user", "content": _revise_prompt(draft, must_fix, should_fix)}],
    )
    return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")


def revise_with_chatgpt(draft: str, must_fix: list[str], should_fix: list[str]) -> str:
    from openai import OpenAI  # lazy

    client = OpenAI()
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You output only the revised instruction document."},
            {"role": "user", "content": _revise_prompt(draft, must_fix, should_fix)},
        ],
    )
    return resp.choices[0].message.content or draft


# ---------------------------------------------------------------------------
# Mock (API 키 없이 로직만 검증)
# ---------------------------------------------------------------------------
def mock_review(mode: str, reviewer: str, round_no: int, draft_hash: str) -> dict:
    """mock 리뷰. converge=2라운드에 수렴, stubborn=계속 미수렴."""
    approve = mode == "converge" and round_no >= 2
    if approve:
        return normalize_review(
            {
                "reviewer": reviewer,
                "round": round_no,
                "draft_hash": draft_hash,
                "verdict": VERDICT_APPROVE,
                "risk_level": "LOW",
                "must_fix": [],
                "should_fix": [],
                "approved": True,
                "summary": f"[mock] {reviewer} 차단성 결함 없음(round {round_no}).",
            },
            reviewer,
            round_no,
            draft_hash,
        )
    return normalize_review(
        {
            "reviewer": reviewer,
            "round": round_no,
            "draft_hash": draft_hash,
            "verdict": VERDICT_CHANGES,
            "risk_level": "MEDIUM",
            "must_fix": [f"[mock] {reviewer}: round {round_no} 미해결 차단 항목"],
            "should_fix": [f"[mock] {reviewer}: 권고 항목"],
            "approved": False,
            "summary": f"[mock] {reviewer} 수정 필요(round {round_no}).",
        },
        reviewer,
        round_no,
        draft_hash,
    )


def mock_revise(draft: str, must_fix: list[str], should_fix: list[str], round_no: int) -> str:
    """mock 개정: draft가 실제로 바뀌도록 해소 표시 한 줄을 덧붙인다(해시/diff 변화 확인용)."""
    marker = f"\n<!-- consensus(mock): round {round_no} must_fix {len(must_fix)}건 해소 -->\n"
    return draft + marker


# ---------------------------------------------------------------------------
# 판정
# ---------------------------------------------------------------------------
def recompute_approved(review: dict, current_hash: str) -> bool:
    """approved는 모델 자기보고를 믿지 않고 오케스트레이터가 재계산한다.

    (verdict==APPROVE) and (must_fix 비어있음) and (echo한 draft_hash == 현재 dhash)
    """
    return (
        review["verdict"] == VERDICT_APPROVE
        and not review["must_fix"]
        and review["draft_hash"] == current_hash
    )


def union_must_fix(*reviews: dict) -> list[str]:
    seen: list[str] = []
    for r in reviews:
        for m in r["must_fix"]:
            if m not in seen:
                seen.append(m)
    return seen


def union_should_fix(*reviews: dict) -> list[str]:
    seen: list[str] = []
    for r in reviews:
        for s in r["should_fix"]:
            if s not in seen:
                seen.append(s)
    return seen


# ---------------------------------------------------------------------------
# run-id / 출력
# ---------------------------------------------------------------------------
def make_run_id() -> str:
    """충돌 방지: 마이크로초 + 짧은 uuid 접미사."""
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f") + "-" + uuid4().hex[:6]


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# 3버튼 지시문 생성기 (화면 입력/출력 전용)
# ---------------------------------------------------------------------------
def _strip_code_fences(text: str) -> str:
    """모델이 실수로 코드펜스를 넣어도 최종 결과는 한 개 text 코드블록으로 다시 감싼다."""
    lines = text.strip().splitlines()
    if len(lines) >= 2 and lines[0].strip().startswith("```") and lines[-1].strip() == "```":
        lines = lines[1:-1]
    return "\n".join(lines).strip()


def as_text_code_block(text: str) -> str:
    """항상 하나의 ```text 코드블록으로 복사 가능한 결과를 만든다."""
    body = _strip_code_fences(text)
    body = body.replace("```", "~~~")
    return f"```text\n{body}\n```"


def safe_error_message(exc: BaseException) -> str:
    """API 오류를 화면에 보여주되 키/토큰처럼 보이는 값은 가린다."""
    msg = f"{type(exc).__name__}: {exc}"
    patterns = [
        r"sk-[A-Za-z0-9_\-]{8,}",
        r"sk-proj-[A-Za-z0-9_\-]{8,}",
        r"anthropic-[A-Za-z0-9_\-]{8,}",
        r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^'\"\s]+",
    ]
    for pattern in patterns:
        msg = re.sub(pattern, r"\1=[redacted]" if "(" in pattern else "[redacted]", msg)
    return msg


def _generator_system_prompt(mode: str) -> str:
    common = (
        "너는 SmartReturn Pro 똘망이 운영 구조용 지시문 생성기다. "
        "사용자가 붙여넣은 초안/보고서를 바탕으로 바로 복사 가능한 최종 본문만 작성한다. "
        "코드펜스는 쓰지 말고 본문만 출력한다. 화면 프로그램이 최종적으로 하나의 text 코드블록으로 감싼다. "
        "모든 본문 설명과 보고는 한글로 쓴다. "
        f"대상 저장소는 {SMARTRETURN_PRO_ROOT}이며 SmartReturn 본체 C:\\donghyun-logistics-platform와 혼동하지 않는다. "
        "자동 실행, 자동 커밋, 자동 푸시는 절대 지시하지 않는다. "
        "secret, .env, local.secret, token, key, password 값은 출력하지 않는다."
    )
    if mode == GEN_MODE_WORK:
        return common + (
            "\n\n[작업지시문 생성 규칙]\n"
            "- 맨 위에 [실행 정보]를 둔다.\n"
            "- 실행대상은 입력 내용을 보고 Claude Code / Codex 5.5 / ChatGPT 지시 기반 통합 검수 중 제안한다.\n"
            "- 대상 저장소: C:\\smartreturn-pro 를 명시한다.\n"
            "- 작업 구조: 똘망이 팀 운영 구조를 명시한다.\n"
            "- Agent Teams는 기본 OFF, 고위험 보안/권한/테넌시/격리 작업만 ON 제안으로 쓴다.\n"
            "- 작업 시작 전 AGENTS.md, ai-harness/memory/000-read-this-first.md, ai-harness/handoff/latest-handoff.md 확인을 포함한다.\n"
            "- SmartReturn Pro와 SmartReturn 본체 혼동 금지, git add . 금지, 사용자 승인 전 commit/push 금지를 포함한다.\n"
            "- secret/.env/local.secret/token/key 출력 금지를 포함한다.\n"
            "- 같은 오류 또는 같은 명령 3회 반복 시 중단 보고를 포함한다.\n"
            "- 브라우저 검증 10~15분 이상 막히면 중단 보고를 포함한다.\n"
            "- 목표/범위/완료조건/중단조건/검증/보고형식을 구체화한다.\n"
            "- 최종 보고는 하나의 text 코드블록으로 작성하라고 지시한다.\n"
            "- Claude Code에 바로 붙여넣을 수 있는 작업지시문 형태로 만든다."
        )
    if mode == GEN_MODE_REVIEW:
        return common + (
            "\n\n[검수지시문 생성 규칙]\n"
            "- 입력된 완료보고서를 그대로 믿지 말라고 맨 앞에 강하게 적는다.\n"
            "- 실제 git status, git diff, 테스트/build, 변경파일, secret 여부를 확인하게 한다.\n"
            "- 작업 범위 밖 파일 포함 여부를 확인하게 한다.\n"
            "- 커밋 후보와 제외 파일을 분리하게 한다.\n"
            "- 권한/테넌시/재고/마감/데이터 범위 같은 SmartReturn Pro 핵심 원칙 위반을 확인하게 한다.\n"
            "- PASS / 부분통과 / FAIL 판단을 요구한다.\n"
            "- 수정 필요 항목만 짧게 보고하게 한다.\n"
            "- 검수 중 파일 수정 금지, git add/commit/push 금지를 포함한다.\n"
            "- 최종 보고는 하나의 text 코드블록으로 작성하라고 지시한다.\n"
            "- Codex에 바로 붙여넣을 수 있는 검수지시문 형태로 만든다."
        )
    if mode == GEN_MODE_DECISION:
        return common + (
            "\n\n[최종판단/다음작업 생성 규칙]\n"
            "- Codex 검수보고서를 기준으로 최종 판단을 내린다.\n"
            "- PASS면 커밋 가능 여부와 커밋 대상 파일만 분리한다.\n"
            "- 부분통과면 보강 지시 초안을 생성한다.\n"
            "- FAIL이면 중단 사유와 재작업 지시 초안을 생성한다.\n"
            "- 다음 작업 초안을 생성하되 자동 실행하지 않는다고 명시한다.\n"
            "- 사용자가 다시 확인 후 작업지시문 생성 버튼에 넣는 구조라고 명시한다.\n"
            "- 출력 항목은 최종 판단, 커밋 가능 여부, 커밋 후보, 커밋 제외, 남은 위험, 다음 작업 초안, 필요 시 다음 작업지시문 생성용 초안이다.\n"
            "- 최종 보고는 하나의 text 코드블록으로 작성하라고 지시한다."
        )
    raise ValueError(f"지원하지 않는 생성 모드입니다: {mode}")


def _generator_user_prompt(mode: str, user_text: str) -> str:
    return (
        f"[생성 모드]\n{GENERATION_MODES[mode]}\n\n"
        "[사용자 입력]\n"
        f"{user_text.strip()}\n\n"
        "[출력 요구]\n"
        "바로 복사해 사용할 최종 본문만 출력한다. 설명, 머리말, 코드펜스, 별도 주석은 쓰지 않는다."
    )


def _mock_generation(mode: str, user_text: str) -> str:
    title = GENERATION_MODES[mode]
    if mode == GEN_MODE_WORK:
        return (
            "[실행 정보]\n"
            "- 실행대상: Claude Code\n"
            "- 대상 저장소: C:\\smartreturn-pro\n"
            "- 작업 구조: 똘망이 팀 운영 구조\n"
            "- Agent Teams: OFF\n\n"
            "작업 시작 전 AGENTS.md, ai-harness/memory/000-read-this-first.md, ai-harness/handoff/latest-handoff.md를 확인한다.\n"
            "SmartReturn Pro와 SmartReturn 본체 C:\\donghyun-logistics-platform를 혼동하지 않는다.\n\n"
            f"[작업명]\n{title} mock 결과\n\n"
            "[사용자 초안]\n"
            f"{user_text.strip()}\n\n"
            "[금지]\n"
            "- git add . 금지\n- 사용자 승인 전 commit/push 금지\n- secret/.env/local.secret/token/key 출력 금지\n\n"
            "[중단 조건]\n"
            "- 같은 오류 또는 같은 명령 3회 반복 시 중단 보고\n- 브라우저 검증 10~15분 이상 막히면 중단 보고\n\n"
            "[보고 형식]\n보고는 하나의 text 코드블록으로만 작성한다."
        )
    if mode == GEN_MODE_REVIEW:
        return (
            "[실행 정보]\n"
            "- 실행대상: Codex 5.5\n"
            "- 대상 저장소: C:\\smartreturn-pro\n"
            "- 작업 구조: 똘망이 팀 운영 구조\n"
            "- 실행 모드: 읽기전용 검수 모드\n\n"
            "작업 보고서를 그대로 믿지 말고 실제 파일/git/test/build/secret/범위를 확인한다.\n\n"
            f"[검수 대상 보고]\n{user_text.strip()}\n\n"
            "[금지]\n- 검수 중 파일 수정 금지\n- git add/commit/push 금지\n\n"
            "[보고 형식]\nPASS / 부분통과 / FAIL 판단을 하나의 text 코드블록으로만 작성한다."
        )
    return (
        "[최종 판단]\n"
        "부분통과\n\n"
        "[커밋 가능 여부]\n"
        "사용자 확인 전 커밋 금지\n\n"
        "[커밋 후보]\n"
        "- 검수보고서 기준으로 선별 필요\n\n"
        "[커밋 제외]\n"
        "- secret/.env/local.secret/token/key/password\n- build/dist/cache/__pycache__/node_modules/.venv\n\n"
        "[남은 위험]\n"
        "- 실제 git 상태 확인 필요\n\n"
        "[다음 작업 초안]\n"
        f"{user_text.strip()}\n\n"
        "[주의]\n"
        "다음 작업 초안은 자동 실행하지 않는다. 사용자가 확인 후 작업지시문 생성 버튼에 다시 넣는다."
    )


def _call_openai_generation(system_prompt: str, user_prompt: str) -> str:
    from openai import OpenAI  # lazy

    client = OpenAI()
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return resp.choices[0].message.content or ""


def _call_claude_generation(system_prompt: str, user_prompt: str) -> str:
    import anthropic  # lazy

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=8000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")


def generate_prompt_document(
    mode: str,
    user_text: str,
    *,
    provider: str = "auto",
    mock: str | None = None,
) -> str:
    """화면 버튼 1회 클릭당 1회 생성한다. 파일 루프/자동 재호출은 하지 않는다."""
    if mode not in GENERATION_MODES:
        raise ValueError(f"지원하지 않는 생성 모드입니다: {mode}")
    if not user_text.strip():
        raise ValueError("입력 텍스트가 비어 있습니다.")

    if mock:
        return as_text_code_block(_mock_generation(mode, user_text))

    system_prompt = _generator_system_prompt(mode)
    user_prompt = _generator_user_prompt(mode, user_text)
    selected = provider
    if selected == "auto":
        if os.environ.get("OPENAI_API_KEY"):
            selected = "openai"
        elif os.environ.get("ANTHROPIC_API_KEY"):
            selected = "claude"
        else:
            raise ValueError("OPENAI_API_KEY 또는 ANTHROPIC_API_KEY 환경변수가 필요합니다.")

    if selected == "openai":
        result = _call_openai_generation(system_prompt, user_prompt)
    elif selected == "claude":
        result = _call_claude_generation(system_prompt, user_prompt)
    else:
        raise ValueError(f"지원하지 않는 provider입니다: {provider}")
    return as_text_code_block(result)


# ---------------------------------------------------------------------------
# 메인 루프
# ---------------------------------------------------------------------------
def run_consensus(
    draft_path: Path | None,
    rounds: int,
    out_dir: Path,
    reviser: str,
    mock: str | None,
    *,
    draft_text: str | None = None,
    progress_callback=None,
    cancel_check=None,
) -> dict:
    """합의 루프 실행.

    progress_callback(event: dict): None이면 기존 동작 유지. 주어지면 라운드/리뷰/개정/완료
    이벤트를 dict로 전달한다(엔진은 tkinter 등 GUI를 import 하지 않는다).
    cancel_check(): True를 반환하면 다음 라운드 진입 전에 중단한다.
    draft_text: 화면 입력 등으로 draft를 직접 줄 때 사용(파일 대신).
    """

    def _emit(event: dict) -> None:
        if progress_callback is not None:
            try:
                progress_callback(event)
            except Exception:
                pass  # GUI 콜백 오류가 엔진을 멈추지 않게 한다.

    def _cancelled() -> bool:
        return bool(cancel_check and cancel_check())

    if draft_text is not None:
        draft = draft_text
    elif draft_path is not None:
        draft = draft_path.read_text(encoding="utf-8")
    else:
        raise ValueError("draft_path 또는 draft_text 중 하나는 필요합니다.")
    run_id = make_run_id()
    run_dir = out_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    status = "NEEDS_USER_DECISION"
    approved_hash = None
    rounds_record: list[dict] = []
    prev_must_fix: list[str] = []

    for round_no in range(1, rounds + 1):
        if _cancelled():
            status = "STOPPED"
            break
        dhash = canonical_hash(draft)
        round_dir = run_dir / f"round-{round_no:02d}"
        round_dir.mkdir(parents=True, exist_ok=True)
        write_text(round_dir / "draft.md", canonical(draft))
        _emit({"type": "round_start", "round": round_no, "hash": dhash})

        if mock:
            claude_review = mock_review(mock, "claude", round_no, dhash)
        else:
            claude_review = call_claude_review(draft, dhash, round_no, prev_must_fix)
        _emit({
            "type": "review", "reviewer": "claude", "round": round_no,
            "verdict": claude_review["verdict"], "must_fix": len(claude_review["must_fix"]),
            "approved": recompute_approved(claude_review, dhash),
        })

        if mock:
            chatgpt_review = mock_review(mock, "chatgpt", round_no, dhash)
        else:
            chatgpt_review = call_chatgpt_review(draft, dhash, round_no, prev_must_fix)
        _emit({
            "type": "review", "reviewer": "chatgpt", "round": round_no,
            "verdict": chatgpt_review["verdict"], "must_fix": len(chatgpt_review["must_fix"]),
            "approved": recompute_approved(chatgpt_review, dhash),
        })

        # 해시 echo 검증: 리뷰가 다른 draft를 본 것 같으면 경고 표시.
        for rv in (claude_review, chatgpt_review):
            if rv["draft_hash"] != dhash:
                rv["summary"] = f"[경고] draft_hash 불일치(무효 처리). {rv['summary']}"

        write_text(round_dir / "claude-review.json", json.dumps(claude_review, ensure_ascii=False, indent=2))
        write_text(round_dir / "chatgpt-review.json", json.dumps(chatgpt_review, ensure_ascii=False, indent=2))

        claude_ok = recompute_approved(claude_review, dhash)
        chatgpt_ok = recompute_approved(chatgpt_review, dhash)
        open_must_fix = union_must_fix(claude_review, chatgpt_review)
        open_should_fix = union_should_fix(claude_review, chatgpt_review)

        rounds_record.append(
            {
                "round": round_no,
                "draft_hash": dhash,
                "claude_approved": claude_ok,
                "chatgpt_approved": chatgpt_ok,
                "open_must_fix": open_must_fix,
                "claude_review": claude_review,
                "chatgpt_review": chatgpt_review,
            }
        )

        if claude_ok and chatgpt_ok and not open_must_fix:
            status = "APPROVED"
            approved_hash = dhash
            break

        if round_no == rounds:
            break  # 마지막 라운드면 개정하지 않고 종료

        # 개정(개정 최소화). 개정 후 다음 라운드 draft 갱신 + diff 저장.
        _emit({"type": "revise", "round": round_no})
        prev_draft = draft
        if mock:
            draft = mock_revise(draft, open_must_fix, open_should_fix, round_no)
        elif reviser == "chatgpt":
            draft = revise_with_chatgpt(draft, open_must_fix, open_should_fix)
        else:
            draft = revise_with_claude(draft, open_must_fix, open_should_fix)

        diff = "".join(
            difflib.unified_diff(
                canonical(prev_draft).splitlines(keepends=True),
                canonical(draft).splitlines(keepends=True),
                fromfile=f"round-{round_no:02d}/draft.md",
                tofile=f"round-{round_no + 1:02d}/draft.md",
            )
        )
        write_text(round_dir / "diff-to-next.patch", diff or "(변경 없음)\n")
        prev_must_fix = open_must_fix

    # consensus.json 기록
    consensus = {
        "run_id": run_id,
        "draft_path": str(draft_path) if draft_path else None,
        "rounds_allowed": rounds,
        "rounds_run": len(rounds_record),
        "reviser": reviser,
        "mock": mock,
        "status": status,
        "approved_hash": approved_hash,
        "rounds": rounds_record,
        "anthropic_model": ANTHROPIC_MODEL,
        "openai_model": OPENAI_MODEL,
    }
    write_text(run_dir / "consensus.json", json.dumps(consensus, ensure_ascii=False, indent=2))

    # final-instruction.md (APPROVED 시에만)
    if status == "APPROVED":
        write_text(run_dir / "final-instruction.md", canonical(draft))

    # review-summary.md (사람용 요약)
    summary_path = run_dir / "review-summary.md"
    write_text(summary_path, _summary_md(consensus))

    final_path = run_dir / "final-instruction.md" if status == "APPROVED" else None
    _emit({
        "type": "done",
        "status": status,
        "run_dir": str(run_dir),
        "final_path": str(final_path) if final_path else None,
        "summary_path": str(summary_path),
    })

    return consensus


def _summary_md(c: dict) -> str:
    lines = [
        "# 합의 루프 결과 요약",
        "",
        f"- run_id: {c['run_id']}",
        f"- 상태: {c['status']}",
        f"- 진행 라운드: {c['rounds_run']} / 최대 {c['rounds_allowed']}",
        f"- 개정자(reviser): {c['reviser']}" + (f" / mock={c['mock']}" if c["mock"] else ""),
        "",
        "## 라운드별 판정",
    ]
    for r in c["rounds"]:
        lines.append(
            f"- round {r['round']}: claude={'APPROVE' if r['claude_approved'] else 'CHANGES'} / "
            f"chatgpt={'APPROVE' if r['chatgpt_approved'] else 'CHANGES'} / "
            f"미해결 must_fix {len(r['open_must_fix'])}건"
        )
    if c["status"] == "APPROVED":
        lines += ["", "## 결과", "- 양측 APPROVE + must_fix 0 → final-instruction.md 생성됨."]
    else:
        last = c["rounds"][-1]["open_must_fix"] if c["rounds"] else []
        lines += ["", "## 남은 쟁점(미합의)"]
        lines += [f"- {m}" for m in last] or ["- (기록된 must_fix 없음)"]
        lines += ["", "→ 사용자 결정 필요(NEEDS_USER_DECISION). final-instruction.md 미생성."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="지시문 합의 루프 오케스트레이터")
    parser.add_argument("draft", type=Path, help="검토할 초안 지시문 경로(.md)")
    parser.add_argument("--rounds", type=int, default=3, help="최대 라운드(기본 3)")
    parser.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "consensus-runs", help="산출물 디렉터리")
    parser.add_argument("--reviser", choices=["claude", "chatgpt"], default="claude", help="개정문 작성 모델(기본 claude)")
    parser.add_argument("--mock", choices=["converge", "stubborn"], default=None, help="API 키 없이 로직만 테스트")
    args = parser.parse_args(argv)

    if not args.draft.is_file():
        print(f"[오류] 초안 파일을 찾을 수 없습니다: {args.draft}", file=sys.stderr)
        return 2

    consensus = run_consensus(args.draft, args.rounds, args.out, args.reviser, args.mock)
    run_dir = args.out / consensus["run_id"]
    print(f"상태: {consensus['status']}")
    print(f"산출물: {run_dir}")
    if consensus["status"] == "APPROVED":
        print(f"최종 지시문: {run_dir / 'final-instruction.md'}")
    else:
        print("최종 지시문 미생성(미합의). review-summary.md 의 남은 쟁점 확인.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

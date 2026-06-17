#!/usr/bin/env python3
"""SmartReturn Pro consensus-loop GUI.

화면에 초안/보고서를 붙여넣고 버튼 1회당 API 생성 1회를 수행한다.
파일 기반 자동 루프, Claude Code/Codex 자동 실행, 자동 커밋/푸시는 하지 않는다.
API 키는 환경변수 또는 이 실행 세션 메모리에만 둔다.
"""
from __future__ import annotations

import os
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

import consensus

try:
    from tkinterdnd2 import TkinterDnD  # type: ignore

    BaseTk = TkinterDnD.Tk
except Exception:  # noqa: BLE001
    BaseTk = tk.Tk


WINDOW_TITLE = "SmartReturn Pro consensus-loop"
WINDOW_DESCRIPTION = "초안/보고서를 붙여넣고 최종 지시문을 생성합니다. 자동 실행/자동 커밋은 하지 않습니다."
SETTINGS_FILENAME = "settings.json"
MONO_FONT = ("Consolas", 10)

MODE_LABELS = {
    consensus.GEN_MODE_WORK: "작업지시문",
    consensus.GEN_MODE_REVIEW: "검수지시문",
    consensus.GEN_MODE_DECISION: "최종판단",
}

MODE_BUTTONS = {
    consensus.GEN_MODE_WORK: "작업지시문 생성",
    consensus.GEN_MODE_REVIEW: "검수지시문 생성",
    consensus.GEN_MODE_DECISION: "최종판단/다음작업 생성",
}

MODE_HINTS = {
    consensus.GEN_MODE_WORK: "초기 작업 초안을 붙여넣으세요.",
    consensus.GEN_MODE_REVIEW: "Claude Code 또는 작업자의 완료보고서를 붙여넣으세요.",
    consensus.GEN_MODE_DECISION: "Codex 검수보고서를 붙여넣으세요.",
}


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = app_dir()
SETTINGS_PATH = APP_DIR / SETTINGS_FILENAME


def load_settings() -> dict:
    import json

    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if "key" not in k.lower()}
    except Exception:
        pass
    return {}


def save_settings(data: dict) -> None:
    import json

    safe = {k: v for k, v in data.items() if "key" not in k.lower()}
    try:
        SETTINGS_PATH.write_text(json.dumps(safe, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def detect_mock() -> str | None:
    val = os.environ.get("CONSENSUS_GUI_MOCK")
    if "--mock" in sys.argv:
        i = sys.argv.index("--mock")
        if i + 1 < len(sys.argv):
            val = sys.argv[i + 1]
    return val if val in ("converge", "stubborn") else None


class PromptGeneratorGUI(BaseTk):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.mock = detect_mock()
        self.event_queue: "queue.Queue[dict]" = queue.Queue()
        self.worker: threading.Thread | None = None
        self.failure_counts: dict[tuple[str, str], int] = {}
        self.current_mode = tk.StringVar(value=consensus.GEN_MODE_WORK)

        suffix = f"  [MOCK: {self.mock}]" if self.mock else ""
        self.title(WINDOW_TITLE + suffix)
        self.geometry(self.settings.get("win_geometry", "1180x760"))
        self.minsize(900, 620)

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(150, self._drain_queue)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        header = ttk.Frame(self, padding=(12, 10, 12, 4))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text=WINDOW_TITLE, font=("", 16, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(header, text=WINDOW_DESCRIPTION).grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.key_status = ttk.Label(header, text="")
        self.key_status.grid(row=0, column=1, sticky="e")
        ttk.Button(header, text="키 입력", command=self._enter_keys).grid(row=1, column=1, sticky="e", pady=(4, 0))

        mode_bar = ttk.Frame(self, padding=(12, 4, 12, 4))
        mode_bar.grid(row=1, column=0, sticky="ew")
        for mode, label in MODE_LABELS.items():
            ttk.Radiobutton(
                mode_bar,
                text=label,
                value=mode,
                variable=self.current_mode,
                command=self._refresh_mode_hint,
            ).pack(side="left", padx=(0, 12))
        ttk.Button(mode_bar, text="입력 비우기", command=self._clear_input).pack(side="right")
        ttk.Button(mode_bar, text="붙여넣기", command=self._paste_input).pack(side="right", padx=(0, 6))

        self.hint_label = ttk.Label(self, text=MODE_HINTS[self.current_mode.get()], padding=(12, 0, 12, 0))
        self.hint_label.grid(row=2, column=0, sticky="ew")

        body = ttk.PanedWindow(self, orient="vertical")
        body.grid(row=3, column=0, sticky="nsew", padx=12, pady=8)

        input_frame = ttk.LabelFrame(body, text="입력")
        input_frame.columnconfigure(0, weight=1)
        input_frame.rowconfigure(0, weight=1)
        self.input_text = tk.Text(input_frame, wrap="word", font=MONO_FONT, undo=True, height=12)
        self.input_text.grid(row=0, column=0, sticky="nsew")
        input_scroll = ttk.Scrollbar(input_frame, command=self.input_text.yview)
        input_scroll.grid(row=0, column=1, sticky="ns")
        self.input_text.configure(yscrollcommand=input_scroll.set)

        output_frame = ttk.LabelFrame(body, text="결과")
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        self.output_text = tk.Text(output_frame, wrap="word", font=MONO_FONT, state="disabled", height=14)
        self.output_text.grid(row=0, column=0, sticky="nsew")
        output_scroll = ttk.Scrollbar(output_frame, command=self.output_text.yview)
        output_scroll.grid(row=0, column=1, sticky="ns")
        self.output_text.configure(yscrollcommand=output_scroll.set)

        body.add(input_frame, weight=1)
        body.add(output_frame, weight=1)

        action_bar = ttk.Frame(self, padding=(12, 0, 12, 10))
        action_bar.grid(row=4, column=0, sticky="ew")
        for mode, label in MODE_BUTTONS.items():
            ttk.Button(action_bar, text=label, command=lambda m=mode: self._generate(m)).pack(side="left", padx=(0, 6))
        self.copy_btn = ttk.Button(action_bar, text="복사", command=self._copy_output)
        self.copy_btn.pack(side="right")
        self.status_label = ttk.Label(action_bar, text="")
        self.status_label.pack(side="right", padx=(0, 12))

        warning = ttk.Frame(self, padding=(12, 0, 12, 10))
        warning.grid(row=5, column=0, sticky="ew")
        self.warning_label = ttk.Label(warning, text="", foreground="#9b2c20")
        self.warning_label.pack(side="left")
        self._refresh_key_status()

    def _refresh_mode_hint(self) -> None:
        self.hint_label.configure(text=MODE_HINTS[self.current_mode.get()])

    def _keys_present(self) -> bool:
        return bool(os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"))

    def _refresh_key_status(self) -> None:
        if self.mock:
            self.key_status.configure(text="키 불필요 (MOCK)")
        elif os.environ.get("OPENAI_API_KEY"):
            self.key_status.configure(text="OpenAI 키 등록됨")
        elif os.environ.get("ANTHROPIC_API_KEY"):
            self.key_status.configure(text="Anthropic 키 등록됨")
        else:
            self.key_status.configure(text="키 없음")

    def _enter_keys(self) -> None:
        if self.mock:
            self._refresh_key_status()
            return
        opn = simpledialog.askstring("OPENAI_API_KEY", "OpenAI API 키(이 실행에서만 사용):", show="*", parent=self)
        if opn:
            os.environ["OPENAI_API_KEY"] = opn.strip()
        if not os.environ.get("OPENAI_API_KEY"):
            ant = simpledialog.askstring("ANTHROPIC_API_KEY", "Anthropic API 키(이 실행에서만 사용):", show="*", parent=self)
            if ant:
                os.environ["ANTHROPIC_API_KEY"] = ant.strip()
        self._refresh_key_status()

    def _clear_input(self) -> None:
        self.input_text.delete("1.0", "end")

    def _paste_input(self) -> None:
        try:
            data = self.clipboard_get()
        except tk.TclError:
            data = ""
        if data:
            self.input_text.insert("insert", data)

    def _set_output(self, text: str) -> None:
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", text)
        self.output_text.configure(state="disabled")

    def _set_busy(self, busy: bool, status: str = "") -> None:
        self.status_label.configure(text=status)
        cursor = "watch" if busy else ""
        self.configure(cursor=cursor)
        self.update_idletasks()

    def _generate(self, mode: str) -> None:
        if self.worker and self.worker.is_alive():
            messagebox.showwarning("진행 중", "현재 생성이 끝난 뒤 다시 눌러주세요.")
            return
        source = self.input_text.get("1.0", "end").strip()
        if not source:
            messagebox.showwarning("입력 없음", "먼저 초안 또는 보고서를 붙여넣으세요.")
            return
        if not self.mock and not self._keys_present():
            self._enter_keys()
            if not self._keys_present():
                messagebox.showwarning("키 필요", "OPENAI_API_KEY 또는 ANTHROPIC_API_KEY가 필요합니다.")
                return

        self.current_mode.set(mode)
        self._refresh_mode_hint()
        self.warning_label.configure(text="")
        self._set_busy(True, f"{MODE_BUTTONS[mode]} 중...")

        def worker() -> None:
            try:
                result = consensus.generate_prompt_document(mode, source, mock=self.mock)
                self.event_queue.put({"type": "done", "mode": mode, "result": result})
            except Exception as exc:  # noqa: BLE001
                self.event_queue.put({"type": "error", "mode": mode, "message": consensus.safe_error_message(exc)})

        self.worker = threading.Thread(target=worker, daemon=True)
        self.worker.start()

    def _drain_queue(self) -> None:
        try:
            while True:
                ev = self.event_queue.get_nowait()
                if ev["type"] == "done":
                    self._set_output(ev["result"])
                    self._set_busy(False, "생성 완료")
                    self.failure_counts.clear()
                elif ev["type"] == "error":
                    self._set_busy(False, "생성 실패")
                    key = (ev["mode"], ev["message"])
                    self.failure_counts[key] = self.failure_counts.get(key, 0) + 1
                    warning = ev["message"]
                    if self.failure_counts[key] >= 3:
                        warning += "\n같은 실패가 3회 반복되어 중단합니다. API 연결 방식 또는 입력을 확인하세요."
                    self.warning_label.configure(text=warning)
                    self._set_output(consensus.as_text_code_block(f"[오류]\n{warning}"))
        except queue.Empty:
            pass
        self.after(150, self._drain_queue)

    def _copy_output(self) -> None:
        text = self.output_text.get("1.0", "end").rstrip("\n")
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update_idletasks()
        self.status_label.configure(text="복사 완료")

    def _on_close(self) -> None:
        save_settings({"win_geometry": self.geometry()})
        self.destroy()


def main() -> int:
    PromptGeneratorGUI().mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

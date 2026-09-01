"""File-only application logging with no terminal handlers."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from threading import Lock


DEFAULT_LOG_PATH = Path(__file__).resolve().parent / "logs" / "simulation.log"


class SimulationFileLogger:
    """Append simulation events to a human-readable UTF-8 log file."""

    def __init__(self, path: Path = DEFAULT_LOG_PATH) -> None:
        self.path = path
        self._lock = Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    @staticmethod
    def _timestamp() -> str:
        return datetime.now().astimezone().isoformat(timespec="seconds")

    def _append(self, content: str) -> None:
        with self._lock:
            with self.path.open("a", encoding="utf-8") as log_file:
                log_file.write(content.rstrip() + "\n")

    def log_message(self, message: str) -> None:
        self._append(f"[{self._timestamp()}] {message}")

    @staticmethod
    def _llm_response_fields(
        raw_response: str | None,
    ) -> tuple[str, str, str, str, str]:
        """Extract the useful Gemini fields without logging the entire payload."""
        if raw_response is None:
            return ("N/A",) * 5
        try:
            payload = json.loads(raw_response)
        except (json.JSONDecodeError, TypeError):
            return raw_response, "N/A", "N/A", "N/A", "N/A"

        candidates = payload.get("candidates") or []
        try:
            content_part_text = candidates[0]["content"]["parts"][0]["text"]
        except (IndexError, KeyError, TypeError):
            content_part_text = "N/A"

        usage = payload.get("usage_metadata") or {}

        def display(value: object) -> str:
            return "N/A" if value is None else str(value)

        return (
            display(content_part_text),
            display(payload.get("response_id")),
            display(usage.get("prompt_token_count")),
            display(usage.get("candidates_token_count")),
            display(usage.get("total_token_count")),
        )

    def log_decision(
        self,
        *,
        framework: str,
        implementation: str,
        model: str | None,
        current_lane_count: int,
        other_lane_count: int,
        framework_action: str,
        applied_action: str,
        reason: str,
        lane_change_blocked: bool,
        llm_request: str | None,
        llm_response: str | None,
        llm_raw_response: str | None,
        latency_ms: int | float | None = None,
        attempts: int | None = None,
    ) -> None:
        request_text = llm_request if llm_request is not None else "N/A"
        parsed_response = llm_response if llm_response is not None else "N/A"
        model_text = model if model else "N/A"
        latency_text = (
            f"{latency_ms:g} ms" if isinstance(latency_ms, (int, float)) else "N/A"
        )
        attempts_text = str(attempts) if isinstance(attempts, int) else "N/A"
        (
            content_part_text,
            response_id,
            prompt_tokens,
            answer_tokens,
            total_tokens,
        ) = self._llm_response_fields(llm_raw_response)
        lines = [
            "",
            f"================== {self._timestamp()} ======================",
            "",
            "[ORDERED DECISION]",
            f"[ETHICAL DECISION] Framework: {framework}",
            f"  Implementation: {implementation}",
            f"  Model: {model_text}",
            f"  Latency: {latency_text}",
            f"  Attempts: {attempts_text}",
            f"  Current lane entities: {current_lane_count}",
            f"  Other lane entities: {other_lane_count}",
            f"  Framework action: {framework_action}",
            f"  Applied action: {applied_action}",
            f"  Reason: {reason}",
        ]
        if lane_change_blocked:
            lines.append("  Lane change unavailable: max_spostamenti reached.")
        lines.extend(
            (
                "",
                "[RAW LLM EXCHANGE]",
                f'- LLM-Request : "{request_text}"',
                f'- content-part-text : "{content_part_text}"',
                f'- response_id : "{response_id}"',
                f'- prompt_token : "{prompt_tokens}"',
                f'- answer_token : "{answer_tokens}"',
                f'- total-token : "{total_tokens}"',
                f'- LLM-Respond (parsed text) : "{parsed_response}"',
                "",
                "============================================",
                "",
            )
        )
        self._append("\n".join(lines))


application_logger = SimulationFileLogger()

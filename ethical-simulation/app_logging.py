"""File-only application logging with no terminal handlers."""

from __future__ import annotations

from datetime import datetime
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

    def log_decision(
        self,
        *,
        framework: str,
        implementation: str,
        current_lane_count: int,
        other_lane_count: int,
        framework_action: str,
        applied_action: str,
        reason: str,
        lane_change_blocked: bool,
        llm_request: str | None,
        llm_response: str | None,
    ) -> None:
        request_text = llm_request if llm_request is not None else "N/A"
        response_text = llm_response if llm_response is not None else "N/A"
        lines = [
            "",
            f"================== {self._timestamp()} ======================",
            "",
            f"[ETHICAL DECISION] Framework: {framework}",
            f"  Implementation: {implementation}",
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
                f'- LLM-Request : "{request_text}"',
                f'- LLM-Respond : "{response_text}"',
                "",
                "============================================",
                "",
            )
        )
        self._append("\n".join(lines))


application_logger = SimulationFileLogger()

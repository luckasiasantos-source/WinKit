"""Log do Agente: texto legível (pt-BR) + eventos JSONL (PLANO.md §11.7)."""

from __future__ import annotations

import json
import logging
import re
import shutil
import traceback
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from winkit.core.layout import LOGS

Clock = Callable[[], datetime]
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


class _Forward(logging.Handler):
    def __init__(self, sink: EventLog) -> None:
        super().__init__(logging.DEBUG)
        self._sink = sink

    def emit(self, record: logging.LogRecord) -> None:
        self._sink.event(record.levelname.lower(), record.getMessage(), source=record.name)


class EventLog:
    def __init__(self, logs_dir: Path, clock: Clock) -> None:
        self.dir = logs_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self._clock = clock
        self._text = self.dir / "agente.log"
        self._jsonl = self.dir / "eventos.jsonl"
        self._handler: _Forward | None = None

    # ---- integração com o logging da plataforma
    def attach_python_logging(self) -> None:
        if self._handler is None:
            self._handler = _Forward(self)
            root = logging.getLogger("winkit")
            root.addHandler(self._handler)
            root.setLevel(logging.INFO)

    def detach_python_logging(self) -> None:
        if self._handler is not None:
            logging.getLogger("winkit").removeHandler(self._handler)
            self._handler = None

    # ---- eventos
    def event(self, level: str, message: str, *, step: str | None = None, **data: Any) -> None:
        now = self._clock()
        record: dict[str, Any] = {
            "time": now.isoformat(),
            "level": level,
            "step": step,
            "message": message,
        }
        if data:
            record["data"] = {k: str(v) for k, v in data.items()}
        with self._jsonl.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        prefix = f"[{step}] " if step else ""
        with self._text.open("a", encoding="utf-8") as fh:
            fh.write(f"{now:%Y-%m-%d %H:%M:%S} {level.upper():7} {prefix}{message}\n")

    def info(self, message: str, **kw: Any) -> None:
        self.event("info", message, **kw)

    def warning(self, message: str, **kw: Any) -> None:
        self.event("warning", message, **kw)

    def error(self, message: str, *, exc: BaseException | None = None, **kw: Any) -> None:
        if exc is not None:
            kw["traceback"] = "".join(traceback.format_exception(exc)).strip()
        self.event("error", message, **kw)

    def step_log(self, step_id: str) -> Path:
        path = self.dir / "steps" / (_SAFE.sub("_", step_id) + ".log")
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    # ---- cópia para o pendrive (item 26)
    def mirror_to(self, pendrive_root: Path, folder_name: str) -> Path | None:
        dest = pendrive_root / LOGS / _SAFE.sub("_", folder_name)
        try:
            shutil.copytree(self.dir, dest, dirs_exist_ok=True)
        except OSError as exc:
            self.warning(f"não foi possível copiar os logs para o pendrive: {exc}")
            return None
        return dest

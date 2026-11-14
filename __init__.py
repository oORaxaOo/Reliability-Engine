"""Hermes Agent plugin adapter for the Reliability Engine repository."""

from pathlib import Path
import sys

_SOURCE_ROOT = Path(__file__).resolve().parent / "src"
_source_text = str(_SOURCE_ROOT)
if _source_text not in sys.path:
    sys.path.insert(0, _source_text)

from reliability_engine.plugin import register  # noqa: E402

__all__ = ["register"]

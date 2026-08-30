"""Auditra backend package."""

from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

__all__ = ["__version__"]

__version__ = "0.1.0"

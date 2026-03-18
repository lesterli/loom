"""Sentra trading agent demo package."""

from .env import load_dotenv

load_dotenv()

from .graph import build_app

__all__ = ["build_app"]

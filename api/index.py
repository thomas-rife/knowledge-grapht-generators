"""Vercel entry point: every path is rewritten here (see vercel.json).

Vercel's Python runtime serves a BaseHTTPRequestHandler subclass named `handler`.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from generators.api import Handler as handler  # noqa: E402,F401

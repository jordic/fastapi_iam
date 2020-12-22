from __future__ import annotations

current_app = None


def set_provider(app):
    global current_app
    current_app = app


def IAMProvider():
    return current_app

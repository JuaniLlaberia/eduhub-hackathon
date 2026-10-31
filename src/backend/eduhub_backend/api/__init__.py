"""
HTTP routes of contract C4, one module per resource. Routes read their dependencies from app.state.
"""
from fastapi import Request
from eduhub_backend.deps import Deps
from eduhub_backend.jobs import JobRunner
from eduhub_backend.settings import Settings

def get_deps(request: Request) -> Deps:
    """
    Return the dependencies the app was created with.
    """
    return request.app.state.deps

def get_settings(request: Request) -> Settings:
    """
    Return the settings the app was created with.
    """
    return request.app.state.settings

def get_runner(request: Request) -> JobRunner:
    """
    Return the app's analysis job runner.
    """
    return request.app.state.runner

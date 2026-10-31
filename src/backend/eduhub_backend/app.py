"""
FastAPI application factory. Run with: uvicorn eduhub_backend.app:main --factory
"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from eduhub_backend.api import analyses, drafts, health, publications, reports, simulations, trends
from eduhub_backend.deps import Deps, build_deps
from eduhub_backend.errors import install_error_handlers
from eduhub_backend.jobs import JobRunner
from eduhub_backend.settings import Settings
from eduhub_backend.sources.fixture import load_demo_reports
from eduhub_shared.version import CONTRACT_VERSION

ROUTERS = (health, analyses, reports, trends, drafts, publications, simulations)

async def seed_demo_reports(settings: Settings, deps: Deps) -> None:
    """
    Store the pre-computed reports of FIXTURES_DIR so they are served right away in DEMO_MODE.
    """
    for report in await load_demo_reports(settings.fixtures_dir):
        await deps.store.save_report(report)

def create_app(settings: Settings, deps: Deps) -> FastAPI:
    """
    Build the API with injected dependencies; the lifespan opens the store and seeds demo reports.
    """
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """
        Open the store (and seed it in DEMO_MODE) on startup; wait for jobs and close it on shutdown.
        """
        await deps.store.init()
        if settings.demo_mode:
            await seed_demo_reports(settings, deps)
        try:
            yield
        finally:
            await app.state.runner.wait_all()
            await deps.store.close()

    app = FastAPI(title="EduHub API", version=CONTRACT_VERSION, lifespan=lifespan)
    app.state.settings = settings
    app.state.deps = deps
    app.state.runner = JobRunner(deps.store, deps.source, deps.analyzer)
    app.add_middleware(
        CORSMiddleware, allow_origins=settings.frontend_origins, allow_methods=["*"], allow_headers=["*"]
    )
    install_error_handlers(app)
    for module in ROUTERS:
        module.register(app)
    return app

def main() -> FastAPI:
    """
    Build the app from environment settings (entry point for uvicorn --factory).
    """
    settings = Settings()
    return create_app(settings, build_deps(settings))

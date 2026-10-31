"""
AI package entry points (contract C3). The backend only imports these three factories.

create_analyzer() returns the real HybridAnalyzer (template mode without OPENROUTER_API_KEY or with
AI_ENABLE_LLM=0). create_generator() returns the shared fake generator until stage 08, so the backend can start
with EDUHUB_FAKE_AI=0. create_simulator() returns None (sandbox disabled) until stage 09.
"""
import logging
from eduhub_ai.analyzer import HybridAnalyzer
from eduhub_ai.config import load_settings
from eduhub_ai.llm.openrouter import OpenRouterClient
from eduhub_shared.fakes import FakeDraftGenerator
from eduhub_shared.interfaces import Analyzer, AudienceSimulator, DraftGenerator

logger = logging.getLogger(__name__)

def create_analyzer() -> Analyzer:
    """
    Return the Analyzer used by the backend (MUST). Builds no network connection.
    """
    settings = load_settings()
    client = None
    if not settings.enable_llm:
        logger.info("AI_ENABLE_LLM=0: analyzer runs in template mode")
    elif not settings.openrouter_api_key:
        logger.warning("OPENROUTER_API_KEY is not set: analyzer runs in template mode (no LLM labels or texts)")
    else:
        client = OpenRouterClient(settings)
    return HybridAnalyzer(settings, client)

def create_generator() -> DraftGenerator:
    """
    Return the DraftGenerator used by the backend (WANTED). The shared fake until stage 08.
    """
    return FakeDraftGenerator()

def create_simulator() -> AudienceSimulator | None:
    """
    Return the AudienceSimulator used by the backend, or None while the sandbox is disabled (STRETCH).
    """
    return None

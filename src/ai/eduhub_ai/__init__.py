"""
AI package entry points (contract C3). The backend only imports these three factories.

create_analyzer() returns the real HybridAnalyzer (template mode without OPENROUTER_API_KEY or with
AI_ENABLE_LLM=0). create_generator() returns the LLM draft generator, or the shared fake one when the LLM is
unavailable (drafts need the LLM; the fake keeps the endpoint working). create_simulator() returns the
ENCC audience sandbox when the LLM is available and personas.json exists, else None (feature disabled).
"""
import logging
from eduhub_ai.analyzer import HybridAnalyzer
from eduhub_ai.config import AISettings, load_settings
from eduhub_ai.generation import LLMDraftGenerator
from eduhub_ai.llm.openrouter import OpenRouterClient
from eduhub_ai.sandbox import personas as sandbox_personas
from eduhub_ai.sandbox.simulator import LLMAudienceSimulator
from eduhub_shared.fakes import FakeDraftGenerator
from eduhub_shared.interfaces import Analyzer, AudienceSimulator, DraftGenerator

logger = logging.getLogger(__name__)

def llm_client(settings: AISettings, role: str) -> OpenRouterClient | None:
    """
    The OpenRouter client, or None (with a log line saying why) when the LLM is disabled or has no key.
    """
    if not settings.enable_llm:
        logger.info("AI_ENABLE_LLM=0: %s runs without the LLM", role)
        return None
    if not settings.openrouter_api_key:
        logger.warning("OPENROUTER_API_KEY is not set: %s runs without the LLM", role)
        return None
    return OpenRouterClient(settings)

def create_analyzer() -> Analyzer:
    """
    Return the Analyzer used by the backend (MUST). Builds no network connection.
    """
    settings = load_settings()
    return HybridAnalyzer(settings, llm_client(settings, "analyzer (template texts)"))

def create_generator() -> DraftGenerator:
    """
    Return the DraftGenerator used by the backend (WANTED): the LLM generator, or the fake without the LLM.
    """
    settings = load_settings()
    client = llm_client(settings, "draft generator (fake templates)")
    return LLMDraftGenerator(settings, client) if client is not None else FakeDraftGenerator()

def create_simulator() -> AudienceSimulator | None:
    """
    Return the AudienceSimulator used by the backend (STRETCH), or None (feature disabled) without the LLM or
    without the personas file.
    """
    if not sandbox_personas.personas_available():
        logger.info("personas.json not found: audience sandbox disabled")
        return None
    settings = load_settings()
    client = llm_client(settings, "audience sandbox (disabled)")
    return LLMAudienceSimulator(settings, client) if client is not None else None

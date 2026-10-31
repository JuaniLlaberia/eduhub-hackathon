"""
AI package entry points (contract C3). The backend only imports these three factories.

Replace the NotImplementedError bodies with the real implementations. Until then the backend uses the fakes
from eduhub_shared.fakes (EDUHUB_FAKE_AI=1).
"""
from eduhub_shared.interfaces import Analyzer, AudienceSimulator, DraftGenerator

def create_analyzer() -> Analyzer:
    """
    Return the Analyzer used by the backend (MUST).
    """
    raise NotImplementedError("AI team: implement create_analyzer()")

def create_generator() -> DraftGenerator:
    """
    Return the DraftGenerator used by the backend (WANTED).
    """
    raise NotImplementedError("AI team: implement create_generator()")

def create_simulator() -> AudienceSimulator | None:
    """
    Return the AudienceSimulator used by the backend, or None while the sandbox is disabled (STRETCH).
    """
    return None

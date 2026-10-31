"""
ScriptedLLMClient: a no-network LLMClient for tests, replaying queued responses in order.
"""
from collections.abc import Callable
from pydantic import BaseModel
from eduhub_ai.llm.client import LLMCall, LLMError, complete_with_retry

type ScriptedResponse = str | Exception | Callable[[LLMCall], str]

class ScriptedLLMClient:
    """
    Return or raise the queued items in order, and record every call. Output goes through the same parsing
    and retry path as the real client.
    """
    def __init__(self, responses: list[ScriptedResponse]) -> None:
        """
        Queue the responses: a JSON string, an exception to raise, or a callable that receives the LLMCall.
        """
        self.responses = list(responses)
        self.calls: list[LLMCall] = []

    async def complete_json[T: BaseModel](
        self, *, model: str, system: str, user: str, schema: type[T], temperature: float | None = None
    ) -> T:
        """
        Replay the next queued responses for this prompt, validated as schema.
        """
        return await complete_with_retry(LLMCall(model, system, user, schema, temperature), self._send)

    async def _send(self, call: LLMCall) -> str:
        """
        Record the call and pop the next queued response.
        """
        self.calls.append(call)
        if not self.responses:
            raise LLMError("ScriptedLLMClient has no responses left.")
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        if callable(item):
            return item(call)
        return item

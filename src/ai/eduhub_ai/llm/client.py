"""
The LLM layer every AI step depends on: one complete_json call that returns a validated pydantic object.
"""
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from typing import Protocol
from pydantic import BaseModel, ValidationError

class LLMError(Exception):
    """
    An LLM call failed. retryable=True means trying again (or with other input) may succeed.
    """
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        """
        Store the message and whether the failure is retryable.
        """
        super().__init__(message)
        self.retryable = retryable

@dataclass(frozen=True)
class LLMCall:
    """
    One request sent to an LLM, as recorded by clients for logging and test assertions.
    """
    model: str
    system: str
    user: str
    schema: type[BaseModel]
    temperature: float | None = None
    reasoning: str | None = None

class LLMClient(Protocol):
    """
    Anything that can turn a prompt into a validated pydantic object.
    """
    async def complete_json[T: BaseModel](
        self, *, model: str, system: str, user: str, schema: type[T], temperature: float | None = None,
        reasoning: str | None = None,
    ) -> T:
        """
        Send the prompt and return the response parsed and validated as schema. reasoning is an effort level
        from config.REASONING_LEVELS ("off" disables thinking; None or "default" leaves the provider's default).
        """
        ...

def parse_or_raise[T: BaseModel](text: str | None, schema: type[T]) -> T:
    """
    Validate the raw response text as schema, or raise a retryable LLMError describing what was wrong.
    """
    if not text or not text.strip():
        raise LLMError("The model returned an empty response.", retryable=True)
    try:
        return schema.model_validate_json(text)
    except ValidationError as error:
        raise LLMError(f"The response does not match the schema:\n{error}", retryable=True) from error

def retry_prompt(user: str, error: LLMError) -> str:
    """
    Build the user message for the single retry: the original prompt plus the validation error.
    """
    return (
        f"{user}\n\nYour previous answer was invalid.\n{error}\n\n"
        "Answer again with only a JSON object that matches the schema."
    )

async def complete_with_retry[T: BaseModel](call: LLMCall, send: Callable[[LLMCall], Awaitable[str | None]]) -> T:
    """
    Send call and parse the reply; on invalid output, retry once with the validation error appended.
    Errors raised by send itself (transport, rate limits) propagate without a retry here.
    """
    text = await send(call)
    try:
        return parse_or_raise(text, call.schema)
    except LLMError as error:
        retry = replace(call, user=retry_prompt(call.user, error))
    text = await send(retry)
    try:
        return parse_or_raise(text, call.schema)
    except LLMError as error:
        raise LLMError(f"Invalid output after one retry: {error}", retryable=False) from error

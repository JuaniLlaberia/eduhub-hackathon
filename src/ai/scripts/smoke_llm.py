"""
Manual smoke test (not run in CI): one real OpenRouter call with a 2-field schema.
Usage: OPENROUTER_API_KEY=... python src/ai/scripts/smoke_llm.py [model]
"""
import asyncio
import logging
import sys
import time
from pydantic import BaseModel
from eduhub_ai.config import load_settings
from eduhub_ai.llm.openrouter import OpenRouterClient

class Greeting(BaseModel):
    """
    Tiny schema for the smoke call.
    """
    saludo: str
    largo: int

async def main(model: str | None) -> None:
    """
    Make one call and print the model, latency and validated output.
    """
    settings = load_settings()
    client = OpenRouterClient(settings)
    model = model or settings.label_model
    started = time.perf_counter()
    result = await client.complete_json(
        model=model,
        system="Respondés solo con JSON válido.",
        user="Escribí un saludo corto en español rioplatense y su cantidad de caracteres.",
        schema=Greeting,
        temperature=0.2,
    )
    print(f"model={model} latency={time.perf_counter() - started:.2f}s output={result.model_dump()}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else None))

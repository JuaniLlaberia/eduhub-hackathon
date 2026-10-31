"""
Manual check (not run in CI): simulate the ENCC audience on two or three post variants with the real model and
print the results, sample comments, time and cost. Needs OPENROUTER_API_KEY.
Usage: python src/ai/scripts/simulate.py [audience_size] "variant 1" "variant 2" ["variant 3"]
"""
import asyncio
import logging
import sys
import time
from eduhub_ai import create_simulator
from eduhub_shared.models import AudienceDimension, SimulationRequest

DEFAULT_VARIANTS = [
    "¿Cuánto gastás por mes en delivery? Hice la cuenta y me asusté 😳",
    "Armé una planilla gratis para controlar tus gastos del mes. Te la dejo acá 👇",
]

async def main(size: int, variants: list[str]) -> None:
    """
    Run one simulation and print variant rates, age segments, a few comments and the cost.
    """
    simulator = create_simulator()
    if simulator is None:
        print("Sandbox disabled: needs OPENROUTER_API_KEY and personas.json.")
        return
    started = time.perf_counter()
    result = await simulator.simulate(SimulationRequest(variants=variants, audience_size=size))
    elapsed = time.perf_counter() - started
    usage = simulator.client.usage
    print(f"{len(result.personas)} personas × {len(variants)} variants in {elapsed:.1f}s, "
          f"{usage.calls} calls ({usage.failures} failed), cost ${usage.cost:.4f}\n")
    for variant in result.variants:
        active = {k.value: v for k, v in variant.reaction_counts.items() if v}
        print(f"[{variant.variant_index + 1}] {variant.interaction_rate:.1%} interacción · {active}")
        print(f"    {variant.text}")
    print("\nPor edad:")
    for segment in result.segments:
        if segment.dimension == AudienceDimension.AGE_GROUP:
            print(f"  v{segment.variant_index + 1} {segment.value:14} n={segment.persona_count:2} "
                  f"{segment.interaction_rate:.1%}")
    print("\nComentarios:")
    for reaction in [r for r in result.reactions if r.comment][:6]:
        print(f"  v{reaction.variant_index + 1} {reaction.reaction.value:8} {reaction.comment}")
    print(f"\n{result.summary}\n{result.disclaimer}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    args = sys.argv[1:]
    size = int(args[0]) if args and args[0].isdigit() else 30
    given = args[1:] if args and args[0].isdigit() else args
    asyncio.run(main(size, given or DEFAULT_VARIANTS))

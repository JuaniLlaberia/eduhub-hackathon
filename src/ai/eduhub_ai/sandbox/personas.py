"""
Synthetic audience personas: the ENCC 2022-23 respondents who use X (OpenARG), built offline by
scripts/build_personas.py into data/personas.json.

Sampling is simple random (seeded) within the filters, and results are aggregated with the survey weights
(Persona.weight = expansor). Sampling proportional to the weight *and* weighting the results would count the
weights twice.
"""
import json
import random
from pathlib import Path
from eduhub_shared.models import AudienceFilters, Persona

PERSONAS_PATH = Path(__file__).resolve().parent / "data" / "personas.json"

def personas_available() -> bool:
    """
    True when the personas file has been built.
    """
    return PERSONAS_PATH.is_file()

def load_personas(path: Path | None = None) -> list[Persona]:
    """
    Read and validate the personas (default: the packaged personas.json).
    """
    source = path or PERSONAS_PATH
    return [Persona.model_validate(item) for item in json.loads(source.read_text(encoding="utf-8"))]

def matches(persona: Persona, filters: AudienceFilters) -> bool:
    """
    True when the persona passes every non-empty filter.
    """
    return ((not filters.age_groups or persona.age_group in filters.age_groups)
            and (not filters.genders or persona.gender in filters.genders)
            and (not filters.provinces or persona.province in filters.provinces))

def sample_personas(personas: list[Persona], filters: AudienceFilters, n: int, seed: int) -> list[Persona]:
    """
    Up to n distinct personas matching filters, a seeded simple random sample (all of them if fewer match).
    """
    pool = [p for p in personas if matches(p, filters)]
    if len(pool) <= n:
        return pool
    return random.Random(seed).sample(pool, n)

"""
One-off data prep for the audience sandbox: turn the ENCC 2022-23 respondents who use X into Persona objects
(eduhub_ai/sandbox/data/personas.json). Standard library only. Survey ids are dropped; personas get new ids
in a shuffled order, so rows can't be matched back to the survey file by position.

Download the CSV (git-ignored) first:
  https://datos.cultura.gob.ar/dataset/251c2ac2-e670-451c-9dbf-a4212af225b5 → base-datos-encc-2022-2023.csv
Usage: python src/ai/scripts/build_personas.py data/raw/base-datos-encc-2022-2023.csv
"""
import csv
import json
import random
import sys
from pathlib import Path
from eduhub_shared.models import Persona

OUTPUT = Path(__file__).resolve().parents[1] / "eduhub_ai" / "sandbox" / "data" / "personas.json"
SHUFFLE_SEED = 2026
DAILY = "Todos o casi todos los días"
WEEKLY = "Algunas veces a la semana"
MONTHLY = "Algunas veces al mes"
PLATFORMS = {
    "int11_1": "youtube", "int11_2": "instagram", "int11_3": "facebook", "int11_4": "tiktok", "int11_5": "twitch",
    "int11_6": "x", "int11_8": "whatsapp", "int11_10": "linkedin",
}
SOCIOECONOMIC = {"ABC1": "Alto", "C2+C3": "Medio", "D1+D2+E": "Bajo"}
UPLOADS = {
    DAILY: "publica contenido casi todos los días",
    WEEKLY: "publica contenido todas las semanas",
    MONTHLY: "publica contenido de vez en cuando",
}

def traits_of(row: dict[str, str]) -> list[str]:
    """
    es-AR descriptors from documented consumption answers: posting frequency, influencer viewing, news habits.
    """
    traits = [UPLOADS.get(row.get("int12.1", ""), "casi nunca publica")]
    if row.get("int12.4") == DAILY:
        traits.append("mira posts de influencers todos los días")
    if row.get("noti1") == "SI":
        traits.append("se informa por el celular" if row.get("noti4") == "Celular" else "sigue las noticias")
    elif row.get("noti1") == "NO":
        traits.append("no sigue las noticias")
    return traits

def persona_of(row: dict[str, str], index: int) -> Persona:
    """
    One Persona from one survey row (new id, expansion weight kept).
    """
    return Persona(
        id=f"persona-{index:03d}",
        age_group=row["grupos_edad"],
        gender=row["genero"],
        province=row["provincia"],
        socioeconomic_level=SOCIOECONOMIC.get(row.get("nse_3", "")),
        platforms=[name for column, name in PLATFORMS.items() if row.get(column) == "1"],
        traits=traits_of(row),
        weight=float(row["expansor"]),
    )

def main(csv_path: Path) -> None:
    """
    Read the survey, keep X users with a positive weight, shuffle them and write personas.json.
    """
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = [r for r in csv.DictReader(handle) if r.get("int11_6") == "1" and float(r.get("expansor") or 0) > 0]
    random.Random(SHUFFLE_SEED).shuffle(rows)
    personas = [persona_of(row, index) for index, row in enumerate(rows, start=1)]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    payload = [p.model_dump(mode="json") for p in personas]
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(personas)} personas written to {OUTPUT}")

if __name__ == "__main__":
    main(Path(sys.argv[1]))

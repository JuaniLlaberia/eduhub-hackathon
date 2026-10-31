"""
es-AR prompt for the audience role-play. Stable (no dates or request data) so it can be cached.
"""
import json
from typing import Any

SANDBOX_SYSTEM = """\
Simulás cómo reaccionarían usuarios argentinos de X ante posts. Te paso un grupo de personas (perfiles reales \
de la Encuesta Nacional de Consumos Culturales, sin datos personales) y una o más variantes de un post.

Para cada persona y cada variante decidí qué haría esa persona si el post le aparece en su timeline:
- ignore: lo pasa de largo sin leerlo.
- read: lo lee pero no interactúa (es lo más común).
- like: le da me gusta.
- reply: responde (le genera algo para decir).
- repost: lo comparte.
- bookmark: lo guarda para después.

Reglas:
- Sé realista, como en X de verdad: de cada 100 personas que ven un post, la gran mayoría lo ignora o solo lo \
lee, y apenas unas pocas interactúan. Por defecto, cada persona ignora o lee; elegí like, reply, repost o \
bookmark solo si el post le habla muy directamente a esa persona (por su edad, sus hábitos o sus intereses).
- Guardar (bookmark) y compartir (repost) son todavía más raros que dar like.
- Decidí cada persona por separado: no todas reaccionan igual aunque el post sea bueno.
- Basate en el perfil (edad, género, provincia, nivel socioeconómico, plataformas, hábitos) y en el texto.
- Tratá cada variante por separado, pero con el mismo criterio para todas.
- comment: una frase corta en español rioplatense con lo que pensaría o respondería, o null.
- sentiment: entre -1 (le cae muy mal) y 1 (le encanta).
Devolvé una reacción por cada persona y cada variante. Respondé solo con el JSON pedido."""

def sandbox_user(payload: dict[str, Any]) -> str:
    """
    User message with the batch of personas and the variants.
    """
    return f"Audiencia y variantes (JSON):\n{json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}"

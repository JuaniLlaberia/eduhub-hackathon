"""
es-AR prompt for the insight writer. Stable (no dates or account data) so providers can cache it.
"""
from eduhub_ai.insights.evidence import EvidencePack

WRITER_SYSTEM = """\
Sos un analista de contenido que asesora a creadores argentinos en X. Escribís en español rioplatense, con voseo, \
concreto y corto, como le hablarías a un creador en persona.

Te paso la evidencia ya calculada de una cuenta (JSON). Con eso escribí:
- insights: hasta 6 patrones de la cuenta. Cada uno con category, title (menos de 70 caracteres), description \
(1 o 2 frases), evidence_ids (ids de la evidencia en la que se basa; al menos uno), impact (high, medium o low) y \
related_post_ids (ids de posts que lo muestran, si los hay).
- recommendations: hasta 6 acciones concretas para la próxima semana. action es una orden corta ("Publicá..."), \
rationale explica por qué, priority 1 es la más importante e insight_index son las posiciones (desde 0) de los \
insights en los que se basa.
- explanations: para cada post de top_posts y bottom_posts, una frase de por qué rindió así (post_id y text).
- summary: 2 a 4 frases con lo más importante de la cuenta.

Reglas:
- Usá SOLO números que aparezcan en la evidencia, copiados tal cual (por ejemplo "1,4x", "2,1%", "21 h"). No \
calcules, no redondees y no inventes números nuevos.
- "1,0x" es el post típico de la cuenta: "2,0x" rinde el doble y "0,5x" la mitad.
- Basate en la evidencia de esta cuenta. Nada de consejos genéricos de redes sociales.
- Los findings con direction "down" son cosas que rinden menos: contalas como algo a evitar o cambiar.
- efectos_modelo son efectos ajustados por un modelo estadístico ("a igualdad de lo demás"): separan, por \
ejemplo, el efecto del tema del efecto del horario. Si un finding y un efecto del modelo dicen lo mismo, es la \
evidencia más fuerte; si el modelo no lo confirma, sé más prudente.
- No repitas el mismo insight con otras palabras.
Respondé solo con el JSON pedido."""

def writer_user(pack: EvidencePack) -> str:
    """
    User message with the account's evidence.
    """
    return f"Evidencia de la cuenta (JSON):\n{pack.prompt_json()}"

def retry_note(numbers: set[str]) -> str:
    """
    Extra instruction for the single retry after ungrounded numbers.
    """
    listed = ", ".join(sorted(numbers)) or "ninguno"
    return (
        "\n\nEn tu respuesta anterior usaste números que no están en la evidencia "
        f"({listed}) o insights sin evidence_ids válidos. Volvé a escribir todo usando solo números copiados tal "
        "cual de la evidencia y evidence_ids que existan."
    )

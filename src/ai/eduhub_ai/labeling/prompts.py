"""
es-AR prompts for the labeling passes. Keep them stable (no dates, no per-call data in the system prompts) so
providers can cache them; everything account-specific goes in the user message.
"""
import json
from eduhub_shared.models import Post

TAXONOMY_SYSTEM = """\
Sos un analista de contenido de redes sociales en Argentina.
Te paso una muestra de posts de una sola cuenta de X. Proponé entre 5 y 8 temas que describan de qué habla \
esta cuenta.

Reglas:
- Cada tema es una etiqueta corta en español, de 1 a 3 palabras, en minúscula (por ejemplo "presupuesto", \
"inversiones", "recetas dulces").
- Los temas tienen que ser específicos de esta cuenta, no genéricos ("finanzas" es demasiado amplio si la \
cuenta solo habla de finanzas).
- Que no se superpongan entre sí y que cubran la mayoría de los posts.
- No incluyas "otros": lo agregamos nosotros.
Respondé solo con el JSON pedido."""

LABEL_SYSTEM = """\
Sos un analista de contenido de redes sociales en Argentina. Etiquetás posts de X de una sola cuenta.
Para cada post devolvé exactamente una etiqueta por campo, usando solo los valores permitidos.

topic: uno de los temas de la cuenta que te paso en el mensaje; si ninguno encaja, "otros".

tone (el registro dominante):
- informativo: explica o comparte información ("Cómo funciona el aguinaldo: ...").
- opinión: toma postura sobre algo ("Para mí el plazo fijo ya no conviene").
- humor: busca hacer reír, ironía, memes.
- personal: cuenta algo propio o una anécdota ("Hoy me pasó algo en el banco...").
- conversacional: charla con la audiencia, pregunta abierta ("¿Ustedes cómo ahorran?").
- promoción: vende o promociona algo propio o de una marca (curso, producto, evento).
- inspiracional: motiva o deja una enseñanza ("Empezá con poco, pero empezá").

sentiment: número entre -1 (muy negativo) y 1 (muy positivo); 0 es neutro.

hook (cómo arranca el post, en la primera frase):
- pregunta: abre con una pregunta ("¿Sabías que...?").
- dato: abre con un número o dato concreto ("El 70% de los argentinos...").
- afirmación fuerte: abre con una frase tajante o polémica ("Ahorrar en pesos es perder plata").
- historia: abre contando algo que pasó ("Ayer mi viejo me dijo...").
- lista: anuncia o arranca una lista o hilo ("5 errores que...", "Hilo 🧵").
- ninguno: no tiene un gancho claro.

cta (qué le pide al lector):
- guardar: pide guardar el post ("Guardalo para después").
- responder: pide comentar o responder ("Contame en los comentarios").
- compartir: pide compartir o retuitear ("Pasáselo a alguien que...").
- seguir: pide seguir la cuenta.
- link: manda a un link externo (web, newsletter, tienda). Un link "https://t.co/..." suelto al final suele ser la \
foto o el video adjunto: eso NO es un cta link.
- ninguno: no pide nada explícito.

Usá el "id" de cada post como post_id. Etiquetá todos los posts. Respondé solo con el JSON pedido."""

def taxonomy_user(posts: list[Post]) -> str:
    """
    User message for the taxonomy pass: the sample texts, one per line.
    """
    lines = "\n".join(f"- {_one_line(p.text)}" for p in posts)
    return f"Posts de la cuenta ({len(posts)}):\n{lines}"

def label_user(posts: list[Post], taxonomy: list[str]) -> str:
    """
    User message for one labeling batch: the allowed topics and the posts as JSON objects with id and text.
    """
    items = "\n".join(json.dumps({"id": p.id, "texto": p.text}, ensure_ascii=False) for p in posts)
    topics = ", ".join(f'"{t}"' for t in taxonomy)
    return f"Temas de la cuenta: {topics}\n\nPosts ({len(posts)}):\n{items}"

def _one_line(text: str) -> str:
    """
    Collapse whitespace so each post fits on one line.
    """
    return " ".join(text.split())

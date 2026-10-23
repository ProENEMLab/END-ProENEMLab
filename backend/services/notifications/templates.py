from html import escape

from services.notifications.catalog import LINKS

def reviews_sentence(count: int, overdue: int) -> str:
    noun = "revisão" if count == 1 else "revisões"
    late = "atrasada" if overdue == 1 else "atrasadas"
    return f"Você tem {count} {noun} hoje ({overdue} {late})."

def render(kind: str, base_url: str, unsubscribe_url: str, *, count: int = 0, overdue: int = 0):
    link = base_url.rstrip("/") + LINKS[kind]
    if kind == "reviews_due":
        title = "Revisões de hoje"
        body = reviews_sentence(count, overdue)
    elif kind == "streak_at_risk":
        title = "Sequência em risco"
        body = "Você ainda não estudou hoje e sua sequência pode acabar."
    elif kind == "study_block":
        title = "Bloco de estudo"
        body = "Um bloco do seu calendário começa em breve."
    else:
        title = "Meta de hoje"
        body = "Sua meta diária de hoje ainda não foi cumprida."
    text = f"{body}\n\nAbrir: {link}\n\nNão quero mais este e-mail: {unsubscribe_url}\n"
    html = (
        f"<p>{escape(body)}</p>"
        f'<p><a href="{escape(link, quote=True)}">Abrir no ProENEM Lab</a></p>'
        f'<p><a href="{escape(unsubscribe_url, quote=True)}">Cancelar este lembrete</a></p>'
    )
    return title, body, text, html

def unsubscribe_page(kind_label: str, channel_label: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Descadastro · ProENEM Lab</title>
</head>
<body>
  <p>Pronto. O lembrete de {escape(kind_label)} por {escape(channel_label)} foi desligado.</p>
</body>
</html>
"""

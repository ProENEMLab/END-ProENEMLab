DISCIPLINE_TO_SUBJECT = {
    "linguagens": "Linguagens",
    "humanas": "Ciências Humanas",
    "natureza": "Ciências da Natureza",
    "matematica": "Matemática",
}

SUBJECT_ALIASES = {
    "linguagens": "Linguagens",
    "humanas": "Ciências Humanas",
    "ciencias humanas": "Ciências Humanas",
    "ciências humanas": "Ciências Humanas",
    "natureza": "Ciências da Natureza",
    "ciencias da natureza": "Ciências da Natureza",
    "ciências da natureza": "Ciências da Natureza",
    "matematica": "Matemática",
    "matemática": "Matemática",
}

SUBJECT_AREA = {
    "Linguagens": "LC",
    "Ciências Humanas": "CH",
    "Ciências da Natureza": "CN",
    "Matemática": "MT",
}

AREA_LABEL = {area: subject for subject, area in SUBJECT_AREA.items()}

SUBJECT_COLOR = {
    "Linguagens": "#2FA8E8",
    "Ciências Humanas": "#F5A623",
    "Ciências da Natureza": "#3DD68C",
    "Matemática": "#C084FC",
}

DEFAULT_SUBJECT_COLOR = "#9AA8BC"

def normalize_subject(value: str | None) -> str | None:
    if not value:
        return None
    key = value.strip().lower()
    return SUBJECT_ALIASES.get(key, value.strip())

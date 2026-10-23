PLANS = [
    {
        "id": "gratuito",
        "name": "Gratuito",
        "price_label": "R$ 0",
        "period": "sempre",
        "badge": None,
        "badge_style": None,
        "highlight": False,
        "cta_label": "Criar conta para estudar",
        "cta_mode": "register",
        "includes_previous": None,
        "summary_features": [
            "Banco de questões oficiais do ENEM",
            "Filtros por ano, matéria e tópico",
            "Roadmap linear de tópicos",
            "Painel com dias até a prova",
            "Estatísticas das questões que você respondeu",
        ],
        "all_features": [
            "Banco de questões oficiais do ENEM (INEP, via enem-api)",
            "Filtros com busca, conjuntos salvos e contador ao vivo",
            "Roadmap linear com status e anotações",
            "Dashboard com meta do dia e sequência de estudo",
            "Estatísticas de acerto por tópico e tipo de erro",
            "Conta com e-mail, sem cartão",
        ],
    },
    {
        "id": "pro",
        "name": "Pro",
        "price_label": "Em breve",
        "period": None,
        "badge": "recomendado",
        "badge_style": "value",
        "highlight": True,
        "cta_label": "Avisar quando abrir",
        "cta_mode": "register",
        "includes_previous": "Tudo do Gratuito, mais:",
        "summary_features": [
            "Simulados montados por disciplina",
            "Relatório de desempenho por ano de prova",
            "Prioridade nos tópicos com menor acerto",
            "Histórico de filtros ilimitado",
            "Exportação dos conjuntos salvos",
        ],
        "all_features": [
            "Simulados por disciplina, dificuldade e quantidade",
            "Relatórios de desempenho por prova de referência",
            "Painel de prioridade nos tópicos mais fracos",
            "Histórico de filtros ilimitado",
            "Exportação dos conjuntos salvos",
            "Quando houver checkout: troca de plano pelo próprio painel",
        ],
    },
    {
        "id": "elite",
        "name": "Elite",
        "price_label": "Em breve",
        "period": None,
        "badge": "mais completo",
        "badge_style": "complete",
        "highlight": False,
        "cta_label": "Avisar quando abrir",
        "cta_mode": "register",
        "includes_previous": "Tudo do Pro, mais:",
        "summary_features": [
            "Teste gerado a partir do seu histórico",
            "Raio-X de pontos fracos por disciplina",
            "Desafio semanal automático",
            "Exclusão em lote de questões já feitas",
            "Suporte prioritário quando houver cobrança",
        ],
        "all_features": [
            "Geração automática de teste com parâmetros visíveis",
            "Raio-X de pontos fracos por disciplina",
            "Recorrência tipo desafio semanal com opt-out",
            "Exclusão de questões já respondidas em lote",
            "Suporte prioritário quando a cobrança existir",
            "Quando houver checkout: troca e cancelamento pelo próprio painel",
        ],
    },
]

PLAN_COMPARE = [
    {
        "label": "Banco oficial do ENEM (INEP)",
        "values": {"gratuito": "Inclui", "pro": "Inclui", "elite": "Inclui"},
    },
    {
        "label": "Roadmap, anotações e painel até a prova",
        "values": {"gratuito": "Inclui", "pro": "Inclui", "elite": "Inclui"},
    },
    {
        "label": "Estatísticas das suas respostas",
        "values": {"gratuito": "Inclui", "pro": "Inclui", "elite": "Inclui"},
    },
    {
        "label": "Simulados por disciplina",
        "values": {"gratuito": "—", "pro": "Quando abrir", "elite": "Quando abrir"},
    },
    {
        "label": "Relatório por ano de prova",
        "values": {"gratuito": "—", "pro": "Quando abrir", "elite": "Quando abrir"},
    },
    {
        "label": "Teste gerado do histórico",
        "values": {"gratuito": "—", "pro": "—", "elite": "Quando abrir"},
    },
    {
        "label": "Desafio semanal",
        "values": {"gratuito": "—", "pro": "—", "elite": "Quando abrir"},
    },
    {
        "label": "Preço nesta fase",
        "values": {"gratuito": "R$ 0", "pro": "Em breve", "elite": "Em breve"},
    },
]

PLANS_FAQ = [
    {
        "id": "pagamento",
        "question": "Como funciona o pagamento e o parcelamento?",
        "answer": (
            "Hoje a plataforma é gratuita: cadastro com e-mail, sem cartão. "
            "Quando os planos pagos forem liberados, as formas de pagamento e o "
            "parcelamento entram nesta página — não cobramos nada enquanto o rótulo for 'Em breve'."
        ),
    },
    {
        "id": "pro-elite",
        "question": "Qual a diferença entre Pro e Elite?",
        "answer": (
            "O Gratuito já abre o banco, o roadmap e as estatísticas. "
            "Pro e Elite são faixas pagas ainda sem checkout: Pro cobre simulados por disciplina, "
            "relatórios por ano e prioridade nos tópicos fracos; Elite acrescenta teste gerado do "
            "histórico, desafio semanal e suporte prioritário. Enquanto o rótulo for 'Em breve', "
            "nada disso é cobrado."
        ),
    },
    {
        "id": "reembolso",
        "question": "Qual é a política de reembolso?",
        "answer": (
            "Não há cobrança ativa, então não há reembolso a processar. "
            "A política de reembolso dos planos pagos será publicada aqui antes da primeira venda, "
            "não depois."
        ),
    },
    {
        "id": "troca",
        "question": "Como trocar ou cancelar um plano?",
        "answer": (
            "Não existe assinatura vigente. Sua conta gratuita continua valendo para o banco, "
            "o roadmap e as estatísticas. Troca e cancelamento de plano pago só passam a existir "
            "junto com o checkout — e serão descritos neste FAQ."
        ),
    },
]

def get_catalog() -> dict:
    highlights = [p["id"] for p in PLANS if p.get("highlight")]
    return {
        "plans": PLANS,
        "compare": PLAN_COMPARE,
        "faq": PLANS_FAQ,
        "primary_highlight_plan_id": highlights[0] if highlights else None,
    }

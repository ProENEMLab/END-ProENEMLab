from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app_factory import create_app
from container import points_service, streak_service
from extensions import db
from models import (
    Attempt,
    DailyGoal,
    Note,
    PointsTransaction,
    Question,
    QuestionOption,
    ReviewCycle,
    ReviewEvent,
    StreakRecord,
    Topic,
    User,
    UserTopicProgress,
)

TOPICS = [
    {
        "name": "Funções do 1º grau",
        "subject": "Matemática",
        "order_index": 1,
        "description": "Funções afins, gráfico e interpretação.",
        "inep_incidence": 8.5,
    },
    {
        "name": "Funções do 2º grau",
        "subject": "Matemática",
        "order_index": 2,
        "description": "Parábolas, vértices e discriminante.",
        "inep_incidence": 7.2,
    },
    {
        "name": "Porcentagem e juros",
        "subject": "Matemática",
        "order_index": 3,
        "description": "Variação percentual, juros simples e compostos.",
        "inep_incidence": 9.1,
    },
    {
        "name": "Geometria plana",
        "subject": "Matemática",
        "order_index": 4,
        "description": "Áreas, perímetros e relações métricas.",
        "inep_incidence": 6.8,
    },
    {
        "name": "Interpretação de texto",
        "subject": "Linguagens",
        "order_index": 5,
        "description": "Compreensão e inferência em textos verbais.",
        "inep_incidence": 12.0,
    },
    {
        "name": "Gêneros textuais",
        "subject": "Linguagens",
        "order_index": 6,
        "description": "Função social e estrutura de gêneros.",
        "inep_incidence": 5.4,
    },
    {
        "name": "Figuras de linguagem",
        "subject": "Linguagens",
        "order_index": 7,
        "description": "Metáfora, ironia, hipérbole e afins.",
        "inep_incidence": 4.2,
    },
    {
        "name": "Ecologia",
        "subject": "Ciências da Natureza",
        "order_index": 8,
        "description": "Cadeias alimentares, ciclos e impactos.",
        "inep_incidence": 6.0,
    },
    {
        "name": "Cinemática",
        "subject": "Ciências da Natureza",
        "order_index": 9,
        "description": "Movimento retilíneo uniforme e variado.",
        "inep_incidence": 5.5,
    },
    {
        "name": "Revolução Industrial",
        "subject": "Ciências Humanas",
        "order_index": 10,
        "description": "Transformações sociais e econômicas dos séculos XVIII–XIX.",
        "inep_incidence": 4.8,
    },
    {
        "name": "Geopolítica contemporânea",
        "subject": "Ciências Humanas",
        "order_index": 11,
        "description": "Blocos econômicos, conflitos e globalização.",
        "inep_incidence": 5.1,
    },
    {
        "name": "Química ambiental",
        "subject": "Ciências da Natureza",
        "order_index": 12,
        "description": "Poluição, combustíveis e sustentabilidade.",
        "inep_incidence": 4.0,
    },
]

YEARS = [2009, 2012, 2015, 2018, 2021, 2023]
OPTION_LETTERS = ["A", "B", "C", "D", "E"]
TARGET_QUESTIONS = 120

def _option_texts(topic_name: str, q_index: int, correct: str) -> dict[str, str]:
    texts = {}
    for letter in OPTION_LETTERS:
        if letter == correct:
            texts[letter] = f"Alternativa correta sobre {topic_name} (questão {q_index})."
        else:
            texts[letter] = f"Distrator {letter} para {topic_name} (questão {q_index})."
    return texts

def _clear_all() -> None:
    ReviewEvent.query.delete()
    ReviewCycle.query.delete()
    PointsTransaction.query.delete()
    StreakRecord.query.delete()
    DailyGoal.query.delete()
    Attempt.query.delete()
    Note.query.delete()
    UserTopicProgress.query.delete()
    QuestionOption.query.filter(
        QuestionOption.question_id.in_(
            db.session.query(Question.id).filter(Question.source != "enem-api")
        )
    ).delete(synchronize_session=False)
    Question.query.filter(Question.source != "enem-api").delete()
    Topic.query.delete()
    User.query.delete()
    db.session.commit()

def _seed_demo_engagement(questions: list[Question]) -> None:
    demo = User(name="Demo Aluno", email="demo@proenem.lab", total_points=0)
    demo.set_password("password123")
    db.session.add(demo)
    db.session.flush()

    today = date.today()
    streak = StreakRecord(
        user_id=demo.id,
        current_streak=4,
        longest_streak=7,
        last_activity_date=today - timedelta(days=1),
    )
    db.session.add(streak)
    db.session.flush()

    sample = questions[:30]
    for i, question in enumerate(sample):
        is_correct = i % 3 != 0
        if question.topic_id == sample[0].topic_id:
            is_correct = i % 5 == 0
        selected = (
            question.correct_option
            if is_correct
            else ("B" if question.correct_option != "B" else "C")
        )
        attempt = Attempt(
            user_id=demo.id,
            question_id=question.id,
            selected_option=selected,
            is_correct=is_correct,
            error_type=None if is_correct else ("conceito" if i % 2 == 0 else "atencao"),
            answered_at=datetime.now(timezone.utc) - timedelta(hours=i),
        )
        db.session.add(attempt)
        db.session.flush()
        points_service.award_points(
            demo.id,
            "question_answered",
            reference_id=attempt.id,
            commit=False,
        )

    streak_service.register_activity(demo.id, today=today, commit=False)

    goal = DailyGoal(
        user_id=demo.id,
        description="Resolver 15 questões de Biologia hoje",
        target_date=today,
        is_completed=False,
    )
    db.session.add(goal)
    db.session.commit()
    print(f"Demo user: {demo.email} / password123 (id={demo.id})")

def run_seed(*, clear: bool = True) -> None:
    if clear:
        _clear_all()

    topics = []
    for data in TOPICS:
        topic = Topic(**data)
        db.session.add(topic)
        topics.append(topic)
    db.session.flush()

    questions: list[Question] = []
    questions_created = 0
    q_global = 1
    while questions_created < TARGET_QUESTIONS:
        for topic in topics:
            if questions_created >= TARGET_QUESTIONS:
                break
            year = YEARS[questions_created % len(YEARS)]
            correct = OPTION_LETTERS[questions_created % 5]
            statement = (
                f"[ENEM {year}] Questão de exemplo #{q_global} sobre '{topic.name}' "
                f"({topic.subject}). Escolha a alternativa correta."
            )
            explanation = (
                f"A alternativa correta é {correct} porque aborda o conceito central de "
                f"'{topic.name}'. As demais opções apresentam erros conceituais comuns."
            )
            question = Question(
                year=year,
                subject=topic.subject,
                topic_id=topic.id,
                statement=statement,
                image_url=None,
                correct_option=correct,
                explanation_text=explanation,
                explanation_image_url=None,
                explanation_video_url=None,
                source="seed",
            )
            db.session.add(question)
            db.session.flush()

            for letter, text in _option_texts(topic.name, q_global, correct).items():
                db.session.add(QuestionOption(question_id=question.id, letter=letter, text=text))

            questions.append(question)
            questions_created += 1
            q_global += 1

    db.session.commit()
    _seed_demo_engagement(questions)
    print(f"Seeded {len(topics)} topics and {questions_created} questions.")

def main() -> None:
    app = create_app()
    with app.app_context():
        db.create_all()
        run_seed()

if __name__ == "__main__":
    main()

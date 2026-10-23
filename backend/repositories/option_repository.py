from models.question import QuestionOption
from repositories.base_repository import BaseRepository

class OptionRepository(BaseRepository):

    model = QuestionOption

    def delete_for_question(self, question_id: int) -> None:
        QuestionOption.query.filter_by(question_id=question_id).delete()

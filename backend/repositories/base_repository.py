from extensions import db

class BaseRepository:

    model = None

    def get_by_id(self, entity_id: int):
        return db.session.get(self.model, entity_id)

    def add(self, entity):
        db.session.add(entity)
        return entity

    def delete(self, entity) -> None:
        db.session.delete(entity)

    def flush(self) -> None:
        db.session.flush()

    def commit(self) -> None:
        db.session.commit()

    def rollback(self) -> None:
        db.session.rollback()

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SmartReturn Pro SQLAlchemy Declarative Base."""


# P0 업무 모델은 후속 작업에서 명시된 migration 범위에 맞춰 추가한다.

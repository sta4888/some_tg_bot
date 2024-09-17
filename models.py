import uuid
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, UUID, Table, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)

    # UUID для уникального идентификатора пользователя
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)

    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100), nullable=True)
    chat_id = Column(String(100), nullable=True)
    is_client = Column(Boolean, nullable=False, default=True)

    # Внешний ключ для связи с Agency (делаем необязательным для отложенной связи)
    agency_id = Column(Integer, ForeignKey('agency.id'), nullable=True)

    # Связь с агентством (может быть установлена позже)
    agency = relationship('Agency', back_populates='users')

    # Поле для хранения реферала (ссылка на другого пользователя)
    referer_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    # Связь с тем, кто привел этого пользователя
    referer = relationship('User', remote_side=[id], backref='referred_users')



from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import DATABASE_URL

# Настройка подключения к базе данных PostgreSQL через SQLAlchemy
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.environ.get('DB_URL')

# Настройка подключения к базе данных PostgreSQL через SQLAlchemy
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()
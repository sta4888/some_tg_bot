import uuid
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey, UUID
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy import JSON

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100), nullable=True)
    chat_id = Column(String(100), nullable=True)
    is_client = Column(Boolean, nullable=False, default=True)
    referer_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    referer = relationship('User', remote_side=[id], backref='referred_users')

    # Отношение "один ко многим" с XML_FEED
    xml_feeds = relationship('XML_FEED', back_populates='user')


class XML_FEED(Base):
    __tablename__ = 'xml_feed'

    id = Column(Integer, primary_key=True)
    url = Column(String(255), nullable=False)  # Поле для хранения ссылки
    user_id = Column(Integer, ForeignKey('users.id'))  # Внешний ключ на таблицу User

    # Отношение к User (многие к одному)
    user = relationship('User', back_populates='xml_feeds')


class SalesAgent(Base):
    __tablename__ = 'sales_agent'

    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    phone = Column(String(20))
    email = Column(String(255))


class Offer(Base):
    __tablename__ = 'offer'

    id = Column(Integer, primary_key=True)
    internal_id = Column(String(50), unique=True)
    offer_type = Column(String(50))  # 'аренда'
    property_type = Column(String(50))  # 'жилая'
    category = Column(String(50))  # 'квартира'
    url_to = Column(String(150), default=None)  # 'ссылка на '
    creation_date = Column(DateTime)
    last_update_date = Column(DateTime)

    min_stay = Column(Integer)
    agency_id = Column(Integer)
    description = Column(Text)

    sales_agent_id = Column(Integer, ForeignKey('sales_agent.id'))
    price_id = Column(Integer, ForeignKey('price.id'), unique=True)  # Одно предложение - одна цена
    location_id = Column(Integer, ForeignKey('location.id'), unique=True)  # Одно предложение - одно местоположение
    area_id = Column(Integer, ForeignKey('area.id'), unique=True)  # Одно предложение - одна площадь

    created_by = Column(Integer, ForeignKey('users.id'))  # Поле для указания создателя
    created_at = Column(DateTime)  # Поле для хранения даты создания

    # Удобства
    washing_machine = Column(Boolean, default=False)
    wi_fi = Column(Boolean, default=False)
    tv = Column(Boolean, default=False)
    air_conditioner = Column(Boolean, default=False)
    kids_friendly = Column(Boolean, default=False)
    party = Column(Boolean, default=False)
    refrigerator = Column(Boolean, default=False)
    phone = Column(Boolean, default=False)
    stove = Column(Boolean, default=False)
    dishwasher = Column(Boolean, default=False)
    music_center = Column(Boolean, default=False)
    microwave = Column(Boolean, default=False)
    iron = Column(Boolean, default=False)
    concierge = Column(Boolean, default=False)
    parking = Column(Boolean, default=False)
    safe = Column(Boolean, default=False)
    water_heater = Column(Boolean, default=False)
    television = Column(Boolean, default=False)
    bathroom = Column(Boolean, default=False)
    pet_friendly = Column(Boolean, default=False)
    smoke = Column(Boolean, default=False)
    romantic = Column(Boolean, default=False)
    jacuzzi = Column(Boolean, default=False)
    balcony = Column(Boolean, default=False)
    elevator = Column(Boolean, default=False)
    sleeps = Column(String(20))  # '2+2'
    rooms = Column(Integer)

    check_in_time_start = Column(String(5))  # '14:00'
    check_in_time_end = Column(String(5))  # '22:00'
    check_out_time_start = Column(String(5))  # '12:00'
    check_out_time_end = Column(String(5))  # '12:00'

    deposit_value = Column(Float)
    deposit_currency = Column(String(10))

    sales_agent = relationship("SalesAgent")
    price = relationship("Price", uselist=False)  # Один к одному
    location = relationship("Location", uselist=False)  # Один к одному
    area = relationship("Area", uselist=False)  # Один к одному
    creator = relationship("User", foreign_keys=[created_by])  # Связь с пользователем, создавшим запись
    photos = relationship("Photo", back_populates="offer")  # Связь с фотографиями

    available_on_file = Column(Boolean, default=True)


class Price(Base):
    __tablename__ = 'price'

    id = Column(Integer, primary_key=True)
    value = Column(Float)
    deposit = Column(Float)
    currency = Column(String(10))
    deposit_currency = Column(String(10))
    period = Column(String(20))


class Location(Base):
    __tablename__ = 'location'

    id = Column(Integer, primary_key=True)
    country = Column(String(100))
    region = Column(String(100))
    locality_name = Column(String(100))
    address = Column(String(255))
    latitude = Column(Float)
    longitude = Column(Float)
    sub_locality_name = Column(String(100))


class Area(Base):
    __tablename__ = 'area'

    id = Column(Integer, primary_key=True)
    value = Column(Float)
    unit = Column(String(10))


class Photo(Base):
    __tablename__ = 'photo'

    id = Column(Integer, primary_key=True)
    offer_id = Column(Integer, ForeignKey('offer.id'))
    is_main = Column(Boolean, default=False)
    url = Column(String(255), nullable=False)  # Ссылка на изображение

    offer = relationship("Offer", back_populates="photos")  # Связь с предложением

# Пример создания базы данных
# engine = create_engine('sqlite:///your_database.db')
# Base.metadata.create_all(engine)

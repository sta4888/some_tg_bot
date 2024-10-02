import uuid
from datetime import datetime

from sqlalchemy import BigInteger
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey, UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    telegram_id = Column(BigInteger, unique=True, nullable=False)  # Изменение на BigInteger
    username = Column(String(100), nullable=True, default="")
    first_name = Column(String(100), nullable=True, default="")
    second_name = Column(String(100), nullable=True, default="")
    chat_id = Column(BigInteger, nullable=True)  # Если это целое число, лучше тоже поменять
    is_client = Column(Boolean, nullable=False, default=True)
    referer_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    referer = relationship('User', remote_side=[id], backref='referred_users')

    xml_feeds = relationship('XML_FEED', back_populates='user')
    invited_count = Column(Integer, default=0)
    payments = relationship("Payment", back_populates="user")
    payouts = relationship("Payout", back_populates="user")
    subscriptions = relationship("Subscription", back_populates="user")


class Payment(Base):
    __tablename__ = 'payments'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    amount = Column(Float, nullable=False)
    payment_date = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="payments")

    def __repr__(self):
        return f"<Payment(user_id={self.user_id}, amount={self.amount}, payment_date={self.payment_date})>"


class Payout(Base):
    __tablename__ = 'payouts'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    amount = Column(Float, nullable=False)
    payout_date = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="payouts")

    def __repr__(self):
        return f"<Payout(user_id={self.user_id}, amount={self.amount}, payout_date={self.payout_date})>"


class Subscription(Base):
    __tablename__ = 'subscriptions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    start_date = Column(DateTime, nullable=False)  # Установите значение по умолчанию
    end_date = Column(DateTime, nullable=False)
    creation_date = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="subscriptions")
    offer_id = Column(Integer, ForeignKey('offer.id'))  # Если подписка связана с предложением
    offer = relationship("Offer", back_populates="subscriptions")
    unique_digits_id = Column(String, unique=True)

    def __repr__(self):
        return f"<Subscription(user_id={self.user_id}, start_date={self.start_date}, end_date={self.end_date})>"


class XML_FEED(Base):
    __tablename__ = 'xml_feed'

    id = Column(Integer, primary_key=True)
    url = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'))

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
    offer_type = Column(String(50))
    property_type = Column(String(50))
    category = Column(String(50))
    url_to = Column(String(150), default=None)
    creation_date = Column(DateTime, default=datetime.utcnow)
    last_update_date = Column(DateTime, default=datetime.utcnow)

    min_stay = Column(Integer)
    agency_id = Column(Integer)
    description = Column(Text)

    sales_agent_id = Column(Integer, ForeignKey('sales_agent.id'))
    price_id = Column(Integer, ForeignKey('price.id'), unique=True)
    location_id = Column(Integer, ForeignKey('location.id'), unique=True)
    area_id = Column(Integer, ForeignKey('area.id'), unique=True)

    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)

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
    sleeps = Column(String(20))
    rooms = Column(Integer)

    check_in_time_start = Column(String(5))
    check_in_time_end = Column(String(5))
    check_out_time_start = Column(String(5))
    check_out_time_end = Column(String(5))

    deposit_value = Column(Float)
    deposit_currency = Column(String(10))

    sales_agent = relationship("SalesAgent")
    price = relationship("Price", uselist=False)
    location = relationship("Location", uselist=False)
    area = relationship("Area", uselist=False)
    creator = relationship("User", foreign_keys=[created_by])
    photos = relationship("Photo", back_populates="offer")
    events = relationship('Event', back_populates='offer')
    subscriptions = relationship("Subscription", back_populates="offer")

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
    internal_id = Column(String(50), default=None)
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


class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True)
    offer_id = Column(Integer, ForeignKey('offer.id'), nullable=False)
    offer = relationship('Offer', back_populates='events')

    uid = Column(String(100), nullable=False)  # уникальный идентификатор события
    start_time = Column(DateTime, nullable=False)  # дата начала
    end_time = Column(DateTime, nullable=False)  # дата окончания
    summary = Column(String(200))  # описание события

    def __str__(self):
        return f"{self.summary} ({self.start_time} - {self.end_time})"

#
# class UserAction(Base):
#     __tablename__ = 'user_action'
#
#     telegram_id = Column(BigInteger, unique=False, nullable=False)  # Изменение на BigInteger
#     username = Column(String(100), nullable=True, default="")
#     first_name = Column(String(100), nullable=True, default="")
#     second_name = Column(String(100), nullable=True, default="")
#     chat_id = Column(BigInteger, nullable=True)  # Если это целое число, лучше тоже поменять
#     action_type = Column(String(255), nullable=True, default="")  # тип действия sand command, send message, changing button
#     action = Column(String(255), nullable=True, default="") # /start..., msg text, button text

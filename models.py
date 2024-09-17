import uuid
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, UUID, Table, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

# Association table for many-to-many relationship between Offer and Inventory (e.g., features like wi-fi, etc.)
offer_inventory = Table(
    'offer_inventory', Base.metadata,
    Column('offer_id', Integer, ForeignKey('offer.id')),
    Column('inventory_id', Integer, ForeignKey('inventory.id'))
)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)

    # UUID для уникального идентификатора пользователя
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)

    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100), nullable=True)
    chat_id = Column(String(100), nullable=True)
    is_client = Column(Boolean, nullable=False, default=True)

    # Внешний ключ для связи с Agency
    agency_id = Column(Integer, ForeignKey('agency.id'), nullable=False)

    # Связь с агентством
    agency = relationship('Agency', back_populates='users')

    # Поле для хранения реферала (ссылка на другого пользователя)
    referer_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    # Связь с тем, кто привел этого пользователя
    referer = relationship('User', remote_side=[id], backref='referred_users')


class Agency(Base):
    __tablename__ = 'agency'

    id = Column(Integer, primary_key=True)
    agency_name = Column(String(100), nullable=True)
    agency_id = Column(Integer, nullable=False)

    # Связь с пользователями
    users = relationship('User', back_populates='agency')

    # Связь с агентами
    agents = relationship('Agent', back_populates='agency')


class Agent(Base):
    __tablename__ = 'agent'

    id = Column(Integer, primary_key=True)
    agency_id = Column(Integer, ForeignKey('agency.id'), nullable=False)
    agent_name = Column(String(100), nullable=False)
    agent_phone = Column(String(100), nullable=False)
    agent_email = Column(String(100), nullable=False)

    agency = relationship('Agency', back_populates='agents')
    offers = relationship('Offer', back_populates='sales_agent')


class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    category_name = Column(String(50), nullable=False)


class Property(Base):
    __tablename__ = 'property'

    id = Column(Integer, primary_key=True)
    property_type = Column(String(50), nullable=False)


class Image(Base):
    __tablename__ = 'image'

    id = Column(Integer, primary_key=True)
    offer_id = Column(Integer, ForeignKey('offer.id'), nullable=False)
    url = Column(String, nullable=False)
    is_main = Column(Integer, default=0)  # 0 for False, 1 for True

    offer = relationship('Offer', back_populates='images')


class Offer(Base):
    __tablename__ = 'offer'

    id = Column(Integer, primary_key=True)
    offer_type = Column(String(50), nullable=False)
    property_id = Column(Integer, ForeignKey('property.id'), nullable=False)
    category_id = Column(Integer, ForeignKey('category.id'), nullable=False)
    creation = Column(DateTime, nullable=False)
    last_update_date = Column(DateTime, nullable=True)
    sales_agent_id = Column(Integer, ForeignKey('agent.id'), nullable=False)
    price = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    min_stay = Column(Integer, nullable=True)
    location = Column(String(100), nullable=True)
    area = Column(Float, nullable=True)
    check_in_time = Column(String(50), nullable=True)
    check_out_time = Column(String(50), nullable=True)

    sales_agent = relationship('Agent', back_populates='offers')
    property = relationship('Property')
    category = relationship('Category')
    inventories = relationship('Inventory', secondary=offer_inventory)
    images = relationship('Image', back_populates='offer')


class Inventory(Base):
    __tablename__ = 'inventory'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)

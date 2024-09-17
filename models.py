from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Table
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
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100), nullable=True)
    chat_id = Column(String(100), nullable=True)


class Agency(Base):
    __tablename__ = 'agency'

    id = Column(Integer, primary_key=True)
    agency_name = Column(String(100), nullable=True)
    agency_id = Column(Integer, nullable=False)

    # Relationship with Agent
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


class Inventory(Base):
    __tablename__ = 'inventory'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)

import xml.etree.ElementTree as ET
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from datetime import datetime
from connect import session
from models import Property, Category, Agent, Offer, Inventory


def parse_and_save_offer(xml_data):
    # Парсинг XML
    root = ET.fromstring(xml_data)

    # Достаём основные данные из XML
    offer_type = root.find('type').text
    property_type = root.find('property-type').text
    category = root.find('category').text
    creation_date = datetime.fromisoformat(root.find('creation-date').text)
    last_update_date = datetime.strptime(root.find('last-update-date').text, '%Y-%m-%d %H:%M:%S %z')

    # Агент и агентство
    agent_name = root.find('sales-agent/name').text
    agent_phone = root.find('sales-agent/phone').text
    agent_email = root.find('sales-agent/email').text

    # Цена
    price_value = float(root.find('price/value').text)

    # Описание
    description = root.find('description').text

    # Минимальный срок проживания
    min_stay = int(root.find('min-stay').text)

    # Локация
    country = root.find('location/country').text
    region = root.find('location/region').text
    locality_name = root.find('location/locality-name').text
    address = root.find('location/address').text
    latitude = float(root.find('location/latitude').text)
    longitude = float(root.find('location/longitude').text)

    # Площадь
    area_value = float(root.find('area/value').text)

    # Время заезда и выезда
    check_in_time_start = root.find('check-in-time/start-time').text
    check_out_time_start = root.find('check-out-time/start-time').text

    # Inventory items (e.g., wi-fi, washing machine)
    inventories = {
        'washing_machine': root.find('washing-machine').text,
        'wi_fi': root.find('wi-fi').text,
        'tv': root.find('tv').text,
        # add more inventories as needed...
    }

    # Создаём или ищем существующие записи
    property_obj = session.query(Property).filter_by(property_type=property_type).first()
    if not property_obj:
        property_obj = Property(property_type=property_type)
        session.add(property_obj)

    category_obj = session.query(Category).filter_by(category_name=category).first()
    if not category_obj:
        category_obj = Category(category_name=category)
        session.add(category_obj)

    agent_obj = session.query(Agent).filter_by(agent_email=agent_email).first()
    if not agent_obj:
        agent_obj = Agent(agent_name=agent_name, agent_phone=agent_phone, agent_email=agent_email)
        session.add(agent_obj)

    # Создаём предложение
    offer = Offer(
        offer_type=offer_type,
        property=property_obj,
        category=category_obj,
        creation=creation_date,
        last_update_date=last_update_date,
        sales_agent=agent_obj,
        price=price_value,
        description=description,
        min_stay=min_stay,
        location=f"{address}, {locality_name}, {region}, {country}",
        area=area_value,
        check_in_time=check_in_time_start,
        check_out_time=check_out_time_start
    )

    session.add(offer)
    session.commit()

    # Добавляем инвентарь (если есть)
    for inventory_name, available in inventories.items():
        if available == '1':  # Если инвентарь доступен
            inventory_obj = session.query(Inventory).filter_by(name=inventory_name).first()
            if not inventory_obj:
                inventory_obj = Inventory(name=inventory_name)
                session.add(inventory_obj)
            offer.inventories.append(inventory_obj)

    session.commit()
    print(f"Offer with ID {offer.id} has been added.")

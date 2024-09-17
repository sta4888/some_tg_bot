from bs4 import BeautifulSoup
from datetime import datetime

from connect import session
from models import Property, Category, Agent, Offer, Inventory


def parse_and_save_offer(xml_data):
    # Парсинг XML с помощью BeautifulSoup
    soup = BeautifulSoup(xml_data, 'xml')

    # Достаём основные данные из XML
    offer_type = soup.find('type').text
    property_type = soup.find('property-type').text
    category = soup.find('category').text
    creation_date = datetime.fromisoformat(soup.find('creation-date').text)
    last_update_date = datetime.strptime(soup.find('last-update-date').text, '%Y-%m-%d %H:%M:%S %z')

    # Агент и агентство
    agent_name = soup.find('sales-agent').find('name').text
    agent_phone = soup.find('sales-agent').find('phone').text
    agent_email = soup.find('sales-agent').find('email').text

    # Цена
    price_value = float(soup.find('price').find('value').text)

    # Описание
    description = soup.find('description').text

    # Минимальный срок проживания
    min_stay = int(soup.find('min-stay').text)

    # Локация
    location = soup.find('location')
    country = location.find('country').text
    region = location.find('region').text
    locality_name = location.find('locality-name').text
    address = location.find('address').text
    latitude = float(location.find('latitude').text)
    longitude = float(location.find('longitude').text)

    # Площадь
    area_value = float(soup.find('area').find('value').text)

    # Время заезда и выезда
    check_in_time_start = soup.find('check-in-time').find('start-time').text
    check_out_time_start = soup.find('check-out-time').find('start-time').text

    # Inventory items (e.g., wi-fi, washing machine)
    inventories = {
        'washing_machine': soup.find('washing-machine').text,
        'wi_fi': soup.find('wi-fi').text,
        'tv': soup.find('tv').text,
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

from datetime import datetime
from bs4 import BeautifulSoup
from sqlalchemy.orm import sessionmaker
from connect import engine
from models import Photo, Offer, User, SalesAgent, Price, Location, Area


def parse_and_save_offer(xml_data, bot, message):
    internal_ids = []
    # Создаем сессию
    Session = sessionmaker(bind=engine)
    session = Session()

    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

    # Парсинг XML с помощью BeautifulSoup
    soup = BeautifulSoup(xml_data, 'xml')
    agency_id = int(soup.find('agency-id').text) if soup.find('agency-id') else None

    for offer in soup.find_all('offer'):
        internal_id = offer.get('internal-id') if offer.get('internal-id') else None
        offer_type = offer.find('type').text if offer.find('type') else None
        property_type = offer.find('property-type').text if offer.find('property-type') else None
        category = offer.find('category').text if offer.find('category') else None
        creation_date_str = offer.find('creation-date').text if offer.find('creation-date') else None
        last_update_date_str = offer.find('last-update-date').text if offer.find('last-update-date') else None
        description = offer.find('description').text if offer.find('description') else None
        min_stay = int(offer.find('min-stay').text) if offer.find('min-stay') else None

        # Пропускаем предложение, если обязательные поля отсутствуют
        if internal_id is None or offer_type is None or property_type is None:
            continue

        # Проверяем, существует ли предложение с таким internal_id
        existing_offer = session.query(Offer).filter_by(internal_id=internal_id).first()

        # Обработка агента по продажам
        agent_name = offer.find('sales-agent').find('name').text if offer.find('sales-agent') and offer.find(
            'sales-agent').find('name') else None
        agent_phone = offer.find('sales-agent').find('phone').text if offer.find('sales-agent') and offer.find(
            'sales-agent').find('phone') else None
        agent_email = offer.find('sales-agent').find('email').text if offer.find('sales-agent') and offer.find(
            'sales-agent').find('email') else None

        sales_agent = None
        if agent_name and agent_phone and agent_email:
            sales_agent = session.query(SalesAgent).filter_by(name=agent_name, phone=agent_phone,
                                                              email=agent_email).first()
            if not sales_agent:
                sales_agent = SalesAgent(name=agent_name, phone=agent_phone, email=agent_email)
                session.add(sales_agent)

        # Обработка цены
        price_value = float(offer.find('price').find('value').text) if offer.find('price') and offer.find('price').find(
            'value') else None
        price_currency = offer.find('price').find('currency').text if offer.find('price') and offer.find('price').find(
            'currency') else None
        price_period = offer.find('price').find('period').text if offer.find('price') and offer.find('price').find(
            'period') else None

        deposit_value = float(offer.find('deposit').find('value').text) if offer.find('deposit') and offer.find(
            'deposit').find(
            'value') else None
        deposit_currency = offer.find('deposit').find('currency').text if offer.find('deposit') and offer.find(
            'deposit').find(
            'currency') else None

        if price_value and price_currency:
            price = Price(value=price_value,
                          currency=price_currency,
                          period=price_period,
                          deposit=deposit_value,
                          deposit_currency=deposit_currency)
            session.add(price)

        # Обработка местоположения
        location_country = offer.find('location').find('country').text if offer.find('location') and offer.find(
            'location').find('country') else None
        location_region = offer.find('location').find('region').text if offer.find('location') and offer.find(
            'location').find('region') else None
        location_locality_name = offer.find('location').find('locality-name').text if offer.find(
            'location') and offer.find('location').find('locality-name') else None
        location_address = offer.find('location').find('address').text if offer.find('location') and offer.find(
            'location').find('address') else None
        location_latitude = float(offer.find('location').find('latitude').text) if offer.find(
            'location') and offer.find('location').find('latitude') else None
        location_longitude = float(offer.find('location').find('longitude').text) if offer.find(
            'location') and offer.find('location').find('longitude') else None

        location = None
        if location_country and location_address:
            location = session.query(Location).filter_by(country=location_country, address=location_address).first()
            if not location:
                location = Location(
                    country=location_country,
                    region=location_region,
                    locality_name=location_locality_name,
                    address=location_address,
                    latitude=location_latitude,
                    longitude=location_longitude
                )
                session.add(location)

        # Обработка площади
        area_value = float(offer.find('area').find('value').text) if offer.find('area') and offer.find('area').find(
            'value') else None
        area_unit = offer.find('area').find('unit').text if offer.find('area') and offer.find('area').find(
            'unit') else None

        area = None
        if area_value and area_unit:
            area = Area(value=area_value, unit=area_unit)
            session.add(area)

        if existing_offer:
            if existing_offer.created_by == user.id:
                # Обновляем необходимые поля
                existing_offer.offer_type = offer_type
                existing_offer.property_type = property_type
                existing_offer.category = category
                existing_offer.creation_date = creation_date_str
                existing_offer.last_update_date = last_update_date_str
                existing_offer.description = description
                existing_offer.min_stay = min_stay
                existing_offer.updated_at = datetime.now()

                # Обновляем фотографии
                existing_offer.photos.clear()
                for photo in offer.find_all('image'):
                    photo_url = photo.text if photo else None
                    photo_is_main = photo.get('main') if photo else None
                    if photo_url:
                        new_photo = Photo(url=photo_url, is_main=1 if photo_is_main else 0)
                        existing_offer.photos.append(new_photo)
                continue
            else:
                continue

        internal_ids.append({'internal_id': internal_id, 'location_address': location_address})

        # Создаем новое предложение
        new_offer = Offer(
            internal_id=internal_id,
            offer_type=offer_type,
            agency_id=agency_id,
            property_type=property_type,
            category=category,
            creation_date=creation_date_str,
            last_update_date=last_update_date_str,
            description=description,
            min_stay=min_stay,
            created_at=datetime.now(),
            created_by=user.id if user else None,
            sales_agent=sales_agent,
            price=price,
            location=location,
            area=area  # Добавляем площадь
        )

        # Добавляем фотографии
        for photo in offer.find_all('image'):
            photo_url = photo.text if photo else None
            photo_is_main = photo.get('main') if photo else None
            if photo_url:
                new_photo = Photo(url=photo_url, is_main=1 if photo_is_main else 0)
                new_offer.photos.append(new_photo)

        session.add(new_offer)

    session.commit()
    session.close()

    print(f"--internal_ids {internal_ids}")

    return internal_ids

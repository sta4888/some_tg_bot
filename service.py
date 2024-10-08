import os
from datetime import datetime
from io import BytesIO

import icalendar
import requests
from loguru import logger
import segno
from PyPDF2 import PdfReader, PdfWriter
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import and_
from sqlalchemy.orm import sessionmaker, Session
from connect import engine, session
from models import Photo, Offer, User, SalesAgent, Price, Location, Area, Subscription, Event


@logger.catch
def parse_and_save_offer(xml_data, bot, message):
    internal_ids = []
    # Создаем сессию
    Session = sessionmaker(bind=engine)
    session = Session()

    user = session.query(User).filter_by(telegram_id=message.from_user.id).first()

    # Парсинг XML с помощью BeautifulSoup
    soup = BeautifulSoup(xml_data, 'xml')
    agency_id = int(soup.find('agency-id').text) if soup.find('agency-id') else None

    for num, offer in enumerate(soup.find_all('offer')):
        logger.info(f"################# {num} ######################")
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

        logger.info(f"--internal_id {internal_id}")

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
            location = session.query(Location).filter_by(
                internal_id=internal_id,
                country=location_country,
                address=location_address,
                region=location_region,
                locality_name=location_locality_name,
            ).first()
            logger.info(f"--location {location}")
            if not location:
                location = Location(
                    internal_id=internal_id,
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

        phones = offer.find_all('phone')

        # Проверим, что есть хотя бы два телефона
        if len(phones) > 1:
            second_phone = phones[1].text  # Получаем второй телефон
        else:
            second_phone = None

        amenities = {
            'washing_machine': bool(int(offer.find('washing-machine').text)) if offer.find('washing-machine') else 0,
            'wi_fi': bool(int(offer.find('wi-fi').text)) if offer.find('wi-fi') else 0,
            'tv': bool(int(offer.find('tv').text)) if offer and offer.find('tv') else 0,
            'air_conditioner': bool(int(offer.find('air-conditioner').text)) if offer.find('air-conditioner') else 0,
            'kids_friendly': bool(int(offer.find('kids-friendly').text)) if offer.find('kids-friendly') else 0,
            'party': bool(int(offer.find('party').text)) if offer and offer.find('party') else 0,
            'refrigerator': bool(int(offer.find('refrigerator').text)) if offer.find('refrigerator') else 0,
            'phone': bool(int(second_phone)) if second_phone else 0,
            'stove': bool(int(offer.find('stove').text)) if offer.find('stove') else 0,
            'dishwasher': bool(int(offer.find('dishwasher').text)) if offer.find('dishwasher') else 0,
            'music_center': bool(int(offer.find('music-center').text)) if offer.find('music-center') else 0,
            'microwave': bool(int(offer.find('microwave').text)) if offer.find('microwave') else 0,
            'iron': bool(int(offer.find('iron').text)) if offer.find('iron') else 0,
            'concierge': bool(int(offer.find('concierge').text)) if offer.find('concierge') else 0,
            'parking': bool(int(offer.find('parking').text)) if offer.find('parking') else 0,
            'safe': bool(int(offer.find('safe').text)) if offer.find('safe') else 0,
            'water_heater': bool(int(offer.find('water-heater').text)) if offer.find('water-heater') else 0,
            'balcony': bool(int(offer.find('balcony').text)) if offer.find('balcony') else 0,
            'television': bool(int(offer.find('television').text)) if offer.find('television') else 0,
            'bathroom': bool(int(offer.find('bathroom').text)) if offer.find('bathroom') else 0,
            'pet_friendly': bool(int(offer.find('pet-friendly').text)) if offer.find('pet-friendly') else 0,
            'smoke': bool(int(offer.find('smoke').text)) if offer.find('smoke') else 0,
            'romantic': bool(int(offer.find('romantic').text)) if offer.find('romantic') else 0,
            'jacuzzi': bool(int(offer.find('jacuzzi').text)) if offer.find('jacuzzi') else 0,
            'elevator': bool(int(offer.find('elevator').text)) if offer.find('elevator') else 0,
            'sleeps': str(offer.find('sleeps').text) if offer.find('sleeps') else '0',
            'rooms': int(offer.find('rooms').text) if offer.find('rooms') else 0,
        }

        if existing_offer:
            logger.info(f"----------------------------## existing_offer {existing_offer.created_by} ##--")

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
                for key, value in amenities.items():
                    setattr(existing_offer, key, value)

                # Обновляем фотографии
                existing_offer.photos.clear()
                for photo in offer.find_all('image'):
                    photo_url = photo.text if photo else None
                    photo_url = photo_url if str(photo_url).startswith('http') else None
                    photo_is_main = photo.get('main') if photo else None
                    if photo_url:
                        new_photo = Photo(url=photo_url, is_main=1 if photo_is_main else 0)
                        existing_offer.photos.append(new_photo)
                continue
            else:
                continue

        internal_ids.append({'internal_id': internal_id, 'location_address': location_address})
        logger.info("Finnnnnnn")

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
            area=area,  # Добавляем площадь
            **amenities,
        )

        # Добавляем фотографии
        for photo in offer.find_all('image'):
            photo_url = photo.text if photo else None
            photo_url = photo_url if str(photo_url).startswith('http') else None
            photo_is_main = photo.get('main') if photo else None
            if photo_url:
                new_photo = Photo(url=photo_url, is_main=1 if photo_is_main else 0)
                new_offer.photos.append(new_photo)

        session.add(new_offer)

    session.commit()
    session.close()

    return internal_ids


@logger.catch
def qr_generate(qr_data: str, pdf_file: str, uuid_user: str) -> None:
    qrcode = segno.make_qr(qr_data)
    image_file = f"{os.getcwd()}/{uuid_user}.png"
    qrcode.save(
        image_file,
        scale=2,
        border=None,
        dark="darkblue",
    )
    output_pdf = f'{os.getcwd()}/pdfs/created/{uuid_user}.pdf'

    insert_image_to_pdf(pdf_file, output_pdf, image_file, 92, 27)


@logger.catch
def insert_image_to_pdf(existing_pdf, output_pdf, image_path, x, y):
    # Create a PDF with the image
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    can.drawImage(image_path, x, y)  # x, y coordinates where to place the image
    can.save()

    # Move to the beginning of the BytesIO buffer
    packet.seek(0)
    new_pdf = PdfReader(packet)

    # Read the existing PDF
    existing_pdf_reader = PdfReader(existing_pdf)
    pdf_writer = PdfWriter()

    # Add the image to each page of the existing PDF
    for page in existing_pdf_reader.pages:
        page.merge_page(new_pdf.pages[0])  # Merge the new image PDF with the existing page
        pdf_writer.add_page(page)

    # Write to the output PDF
    with open(output_pdf, "wb") as output_file:
        pdf_writer.write(output_file)


@logger.catch
def get_referral_chain(user, level=1, max_levels=6):
    if not user or level > max_levels:
        return []

    referrals = session.query(User).filter_by(referer=user).all()
    chain = []

    for referral in referrals:
        # Проверяем, активна ли подписка (если есть записи в таблице подписок)
        latest_subscription = session.query(Subscription).filter_by(user_id=referral.id).order_by(
            Subscription.end_date.desc()).first()
        has_active_subscription = False

        if latest_subscription:
            # Получаем обе даты в виде объектов типа `date` для корректного сравнения
            subscription_end_date = latest_subscription.end_date.date()
            current_date = datetime.utcnow().date()

            if subscription_end_date >= current_date:
                has_active_subscription = True

        # Добавляем реферала в цепочку с нужной информацией
        chain.append({
            "first_name": referral.first_name,
            "telegram_id": referral.telegram_id,
            "level": level,
            "has_active_subscription": has_active_subscription,
        })

        # Рекурсивно добавляем рефералов следующего уровня
        chain.extend(get_referral_chain(referral, level + 1, max_levels))

    return chain


def escape_markdown(text):
    """
    Экранирует специальные символы для MarkdownV2
    """
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(['\\' + char if char in escape_chars else char for char in text])


def check_calendars():
    offers = session.query(Offer).all()
    print(len(offers))
    for offer in offers:
        print(offer.id)
        if offer.url_to.startswith("http"):
            # Логика для проверки и обновления событий календаря url_to
            parse_ical(offer.url_to, offer,
                       session)  # fixme если мы и так передаем объект Offer то зачем мы отдельно отдаем ссылку на календарь офера?
        else:
            continue
    session.close()


def parse_ical(ical_url, offer, session: Session):
    # Получаем календарь по ссылке

    response = requests.get(ical_url)
    if response.status_code != 200:
        print(f"Ошибка при загрузке календаря: {response.status_code}")
        return

    ical_string = response.content
    calendar = icalendar.Calendar.from_ical(ical_string)

    for component in calendar.walk():
        if component.name == "VEVENT":
            uid = component.get('UID')
            start_time = component.get('DTSTART').dt
            end_time = component.get('DTEND').dt
            summary = component.get('SUMMARY')

            # Проверяем, существует ли уже такое событие
            existing_event = session.query(Event).filter(
                and_(
                    Event.uid == uid,
                    Event.start_time == start_time,
                    Event.end_time == end_time,
                    Event.offer == offer  # если offer уникален для сотрудника
                )
            ).first()

            if existing_event:
                # Если событие уже существует, пропускаем его
                print(f"Событие {uid} уже существует. Пропуск.")
                continue

            # Если событие не найдено, создаем его
            event = Event(
                offer=offer,
                uid=uid,
                start_time=start_time,
                end_time=end_time,
                summary=summary
            )
            session.add(event)

    # Сохраняем изменения
    session.commit()

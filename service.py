from datetime import datetime

import icalendar
import requests
from sqlalchemy import and_
from sqlalchemy.orm import joinedload

from connect import session, Session
from models import Location, Offer, Event

from io import BytesIO

import segno
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def find_offers(city, start_date, end_date, guest_count, bedrooms, amenities=None):
    # Поиск местоположения по городу
    locations = session.query(Location).filter(Location.locality_name.ilike(f'%{city}%')).all()
    print(f"--locations {locations}")

    end_date = datetime.strptime(end_date, '%Y-%m-%d')
    start_date = datetime.strptime(start_date, '%Y-%m-%d')

    if not locations:
        return None  # Если нет предложений в этом городе

    for location in locations:
        print(location.locality_name)
    print("########################################")
    print(start_date, end_date, guest_count, bedrooms, amenities)
    print("########################################")

    # Начало фильтрации предложений
    query = session.query(Offer).options(joinedload(Offer.photos)).filter(
        Offer.location_id.in_([loc.id for loc in locations]),  # Предложения по найденным локациям
        Offer.available_on_file.is_(True),  # Только доступные предложения
        # Offer.rooms >= bedrooms,  # Учитываем количество спален
        Offer.sleeps == bedrooms  # Учитываем количество гостей
    )

    # Учитываем выбранные удобства, если они переданы
    if amenities:
        for amenity in amenities:
            query = query.filter(getattr(Offer, amenity).is_(True))

    offers = query.all()
    print("########################################")
    print(f"--offers {offers}")
    print("########################################")

    # Фильтруем предложения по датам
    valid_offers = []
    for offer in offers:
        # Получаем события, связанные с предложением
        events = session.query(Event).filter(Event.offer_id == offer.id).all()
        # Проверка на наличие пересечений дат

        # Создаем объекты datetime

        is_valid = True
        for event in events:  # 10 10 - 14 09   10 01 - 10 04
            print(end_date, event.start_time)
            print(start_date, event.end_time)
            if not (end_date <= event.start_time and start_date >= event.end_time):
                is_valid = False
                break

        if is_valid:
            valid_offers.append(offer)

    return valid_offers


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


def qr_generate(qr_data: str, pdf_file: str) -> None:
    qrcode = segno.make_qr(qr_data)
    image_file = "darkblue_qrcode.png"
    qrcode.save(
        image_file,
        scale=3,
        border=None,
        dark="darkblue",
    )
    output_pdf = 'darkblue_qrcode.pdf'

    insert_image_to_pdf(pdf_file, output_pdf, image_file, 90, 26)


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

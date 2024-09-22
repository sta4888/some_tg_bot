import icalendar
import requests
from sqlalchemy import and_
from sqlalchemy.orm import joinedload

from connect import session, Session
from models import Location, Offer, Event


def find_offers(city, start_date, end_date, guest_count, bedrooms, amenities=None):
    # Поиск местоположения по городу
    locations = session.query(Location).filter(Location.locality_name.ilike(f'%{city}%')).all()
    print(f"--locations {locations}")

    if not locations:
        return None  # Если нет предложений в этом городе

    for location in locations:
        print(location.locality_name)

    # Начало фильтрации предложений
    query = session.query(Offer).options(joinedload(Offer.photos)).filter(
        Offer.location_id.in_([loc.id for loc in locations]),  # Предложения по найденным локациям
        Offer.available_on_file.is_(True),  # Только доступные предложения
        # Offer.rooms >= bedrooms,  # Учитываем количество спален
        Offer.sleeps >= bedrooms  # Учитываем количество гостей
    )

    # Учитываем выбранные удобства, если они переданы
    if amenities:
        for amenity in amenities:
            query = query.filter(getattr(Offer, amenity).is_(True))

    offers = query.all()

    return offers


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

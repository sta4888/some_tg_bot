from datetime import datetime
from bs4 import BeautifulSoup
from sqlalchemy.orm import sessionmaker
from connect import engine
from models import Photo, Offer, User


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
        # Достаём основные данные из XML
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
                existing_offer.photos.clear()  # Очищаем старые фотографии
                for photo in offer.find_all('image'):
                    photo_url = photo.text if photo else None
                    photo_is_main = photo.get('main') if photo else None
                    if photo_url:
                        new_photo = Photo(url=photo_url, is_main=1 if photo_is_main else 0)
                        existing_offer.photos.append(new_photo)
                continue
            else:
                continue

        # Если предложение не существует, добавляем новое
        internal_ids.append(internal_id)

        # Создаем новый объект Offer
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
        )

        # Добавляем фотографии, если есть
        for photo in offer.find_all('image'):
            photo_url = photo.text if photo else None
            photo_is_main = photo.get('main') if photo else None
            if photo_url:
                new_photo = Photo(url=photo_url, is_main=1 if photo_is_main else 0)
                new_offer.photos.append(new_photo)

        # Сохраняем новое предложение в базе данных
        session.add(new_offer)

    # Фиксируем транзакцию и закрываем сессию
    session.commit()
    session.close()

    print(f"--internal_ids {internal_ids}")

    return internal_ids

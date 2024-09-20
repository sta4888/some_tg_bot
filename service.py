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
        internal_id = offer.find('internal-id').text if offer.find('internal-id') else None
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

        internal_ids.append(internal_id)

        # Преобразуем даты, если они есть
        creation_date = datetime.strptime(creation_date_str, '%Y-%m-%dT%H:%M:%S') if creation_date_str else None
        last_update_date = datetime.strptime(last_update_date_str,
                                             '%Y-%m-%dT%H:%M:%S') if last_update_date_str else None

        # Создаём новый объект Offer
        new_offer = Offer(
            internal_id=internal_id,
            offer_type=offer_type,
            agency_id=agency_id,
            property_type=property_type,
            category=category,
            creation_date=creation_date,
            last_update_date=last_update_date,
            description=description,
            min_stay=min_stay,
            created_at=datetime.now(),  # Установка даты создания
            created_by=user,  # Пример ID пользователя, можно заменить на актуальный
        )

        # Добавляем фотографии, если есть
        for photo in offer.find_all('photo'):
            photo_url = photo.text if photo else None
            if photo_url:
                new_photo = Photo(url=photo_url)
                new_offer.photos.append(new_photo)  # Добавляем фотографию к предложению

        # Сохраняем предложение в базе данных
        session.add(new_offer)

    # Фиксируем транзакцию и закрываем сессию
    session.commit()
    session.close()

    return internal_ids

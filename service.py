from sqlalchemy.orm import sessionmaker
from datetime import datetime
from bs4 import BeautifulSoup

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

    agency_id = int(soup.find('agency-id').text)

    for offer in soup.find_all('offer'):

        # Достаём основные данные из XML
        internal_id = offer.find('internal-id').text
        offer_type = offer.find('type').text
        property_type = offer.find('property-type').text
        category = offer.find('category').text
        creation_date = datetime.strptime(offer.find('creation-date').text, '%Y-%m-%dT%H:%M:%S')
        last_update_date = datetime.strptime(offer.find('last-update-date').text, '%Y-%m-%dT%H:%M:%S')
        description = offer.find('description').text
        min_stay = int(offer.find('min-stay').text)
        internal_ids.append(internal_id)

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
            photo_url = photo.text
            new_photo = Photo(url=photo_url)
            new_offer.photos.append(new_photo)  # Добавляем фотографию к предложению

        # Сохраняем предложение в базе данных
        session.add(new_offer)

    # Фиксируем транзакцию и закрываем сессию
    session.commit()
    session.close()

    return internal_ids

from bs4 import BeautifulSoup
from datetime import datetime

from connect import session
from models import Property, Category, Agent, Offer, Inventory, Agency, Image


def parse_and_save_offer(xml_data, bot, message):
    # Парсинг XML с помощью BeautifulSoup
    soup = BeautifulSoup(xml_data, 'xml')

    agency_id = int(soup.find('agency-id').text)
    print(f"--agency_id {agency_id}")

    # Открываем транзакцию
    with session.begin():
        agency = session.query(Agency).filter_by(agency_id=agency_id).first()
        if not agency:
            agency = Agency(agency_id=agency_id)
            session.add(agency)

        for offer_data in soup.find_all('offer'):
            try:
                # Достаём основные данные
                offer_type = offer_data.find('type').text
                property_type = offer_data.find('property-type').text
                category = offer_data.find('category').text
                creation_date = datetime.fromisoformat(offer_data.find('creation-date').text)
                last_update_date = datetime.strptime(offer_data.find('last-update-date').text, '%Y-%m-%d %H:%M:%S %z')
                price_value = float(offer_data.find('price').find('value').text)

                # Дополнительные данные
                description = offer_data.find('description').text or ""
                min_stay = int(offer_data.find('min-stay').text)
                location = offer_data.find('location')
                address = location.find('address').text
                area_value = float(offer_data.find('area').find('value').text)

                # Получение/создание записей связанных моделей
                property_obj = session.query(Property).filter_by(property_type=property_type).first()
                if not property_obj:
                    property_obj = Property(property_type=property_type)
                    session.add(property_obj)

                category_obj = session.query(Category).filter_by(category_name=category).first()
                if not category_obj:
                    category_obj = Category(category_name=category)
                    session.add(category_obj)

                # Создаём новое предложение
                offer = Offer(
                    offer_type=offer_type,
                    property=property_obj,
                    category=category_obj,
                    creation=creation_date,
                    last_update_date=last_update_date,
                    price=price_value,
                    description=description,
                    min_stay=min_stay,
                    location=address,
                    area=area_value,
                )
                session.add(offer)
                session.flush()  # Промежуточное сохранение, чтобы получить ID

                # Сохранение изображений
                for img_url in offer_data.find_all('image'):
                    image = Image(offer_id=offer.id, url=img_url.get_text(strip=True))
                    session.add(image)

                # Генератор для обработки ссылок
                bot.reply_to(message, f"XML файл загружен. Введите ссылку для предложения с internal_id: {value}")

            except Exception as e:
                # Логируем ошибки для отладки
                print(f"Ошибка при парсинге предложения: {e}")
                session.rollback()  # Откат транзакции в случае ошибки

from sqlalchemy import and_
from sqlalchemy.orm import aliased

from connect import session
from models import Location, Offer, Photo


def find_offers(city, start_date, end_date, guest_count, bedrooms, amenities=None):
    # Поиск местоположения по городу
    locations = session.query(Location).filter(Location.locality_name.ilike(f'%{city}%')).all()
    print(f"--locations {locations}")

    if not locations:
        return None  # Если нет предложений в этом городе

    for location in locations:
        print(location.locality_name)

    # Создание алиаса для модели Photo
    main_photo = aliased(Photo)

    # Основной запрос для предложений с фильтрацией
    query = session.query(
        Offer, main_photo.url  # Получаем предложение и URL главной фотографии
    ).outerjoin(
        main_photo,  # Присоединяем таблицу фото
        and_(
            main_photo.offer_id == Offer.id,
            main_photo.is_main.is_(True)  # Только главное фото
        )
    ).filter(
        Offer.location_id.in_([loc.id for loc in locations]),
        Offer.available_on_file.is_(True),
        Offer.rooms >= bedrooms,
        Offer.sleeps >= guest_count
    )

    # Учитываем выбранные удобства, если они переданы
    if amenities:
        for amenity in amenities:
            query = query.filter(getattr(Offer, amenity).is_(True))

    offers = query.all()

    return offers


sleeps_dict = {
    1: {1: 1, 2: 2},
    2: {1: 0, 2: 3},
    3: {1: 1, 2: 1},
    4: {1: 2, 2: 2},
    5: {1: 0, 2: 1},
    6: {1: 2, 2: 0},
    7: {1: 2, 2: 2},
    8: {1: 0, 2: 3},
    9: {1: 1, 2: 1},
    10: {1: 3, 2: 2},
    11: {1: 4, 2: 2},
}

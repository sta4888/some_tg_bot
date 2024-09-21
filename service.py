from connect import session
from models import Location, Offer


def find_offers(city, start_date, end_date, guest_count, bedrooms):
    # Поиск местоположения по городу
    locations = session.query(Location).filter(Location.locality_name.ilike(f'%{city}%')).all()

    if not locations:
        return None  # Если нет предложений в этом городе

    # Поиск предложений, удовлетворяющих условиям
    offers = session.query(Offer).filter(
        Offer.location_id.in_([loc.id for loc in locations]),  # Предложения по найденным локациям
        # Offer.sleeps >= bedrooms,  # Предложения, где могут разместиться столько гостей
        # Offer.rooms >= bedrooms,  # Предложения с нужным количеством спален
        Offer.available_on_file.is_(True)  # Только доступные предложения
    ).all()

    return offers





sleeps_dict = {
    1: {1:1, 2:2},
    2: {1:0, 2:3},
    3: {1:1, 2:1},
    4: {1:2, 2:2},
    5: {1:0, 2:1},
    6: {1:2, 2:0},
    7: {1:2, 2:2},
    8: {1:0, 2:3},
    9: {1:1, 2:1},
    10: {1:3, 2:2},
    11: {1:4, 2:2},
}
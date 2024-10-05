import math

EARTH_RADIUS = 6371210  # Радиус Земли в метрах
DISTANCE = 10000  # Интересующее нас расстояние в метрах (10 км)


# Функция для перевода градусов в радианы
def deg2rad(degrees):
    return degrees * math.pi / 180


# Функция для вычисления длины одного градуса по широте
def compute_latitude_delta():
    return EARTH_RADIUS * math.pi / 180


# Функция для вычисления длины одного градуса по долготе
def compute_longitude_delta(latitude):
    return EARTH_RADIUS * math.pi / 180 * math.cos(deg2rad(latitude))


def find_offer_by_location(latitude, longitude):
    delta_lat = compute_latitude_delta()  # Дельта по широте
    delta_lon = compute_longitude_delta(latitude)  # Дельта по долготе

    # Вычисляем диапазоны координат
    min_latitude = latitude - (DISTANCE / delta_lat)
    max_latitude = latitude + (DISTANCE / delta_lat)
    min_longitude = longitude - (DISTANCE / delta_lon)
    max_longitude = longitude + (DISTANCE / delta_lon)

    # Формируем списки долготы и широты
    longitude_range = [min_longitude, max_longitude]
    latitude_range = [min_latitude, max_latitude]

    return [longitude_range, latitude_range]


# Пример использования
latitude = 55.460531  # Координаты широты
longitude = 37.210488  # Координаты долготы
range_coordinates = find_offer_by_location(latitude, longitude)
print(range_coordinates)  # [[min_longitude, max_longitude], [min_latitude, max_latitude]]

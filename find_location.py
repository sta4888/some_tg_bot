import math

EARTH_RADIUS = 6371210  # Радиус Земли
DISTANCE = 20000  # Интересующее нас расстояние


# Функция для вычисления дельты
def compute_delta(degrees):
    return math.pi / 180 * EARTH_RADIUS * math.cos(deg2rad(degrees))


# Функция для перевода градусов в радианы
def deg2rad(degrees):
    return degrees * math.pi / 180


latitude = 55.460531  # Интересующие нас координаты широты
longitude = 37.210488  # Интересующие нас координаты долготы

delta_lat = compute_delta(latitude)  # Получаем дельту по широте
delta_lon = compute_delta(longitude)  # Получаем дельту по долготе

around_lat = DISTANCE / delta_lat  # Вычисляем диапазон координат по широте
around_lon = DISTANCE / delta_lon  # Вычисляем диапазон координат по долготе

print(around_lat, around_lon)

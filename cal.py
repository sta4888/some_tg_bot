import requests
from icalendar import Calendar
from datetime import datetime

# Скачиваем файл .ics с указанной ссылки
url = 'https://realtycalendar.ru/apartments/export.ics?q=ODQzMjE%3D%0A'
response = requests.get(url)

if response.status_code == 200:
    ics_data = response.content

    # Парсим iCalendar данные
    cal = Calendar.from_ical(ics_data)

    # Проходим по всем событиям в календаре
    for component in cal.walk():
        if component.name == "VEVENT":
            uid = component.get('uid')
            summary = component.get('summary')
            dtstart = component.get('dtstart').dt
            dtend = component.get('dtend').dt
            created = component.get('created').dt
            last_modified = component.get('last-modified').dt

            # Выводим информацию о событии
            print(f"UID: {uid}")
            print(f"Summary: {summary}")
            print(f"Start: {dtstart}")
            print(f"End: {dtend}")
            print(f"Created: {created}")
            print(f"Last Modified: {last_modified}")
            print("="*40)
else:
    print(f"Ошибка загрузки данных. Статус код: {response.status_code}")



# import requests
# from icalendar import Calendar, Event
# from datetime import datetime, timedelta
#
# # Загрузка iCalendar файла
# url = 'https://claen.com/apartments/export.ics?q=ODQz'
# response = requests.get(url)
#
# if response.status_code == 200:
#     ics_data = response.content
#
#     # Парсим iCalendar данные
#     cal = Calendar.from_ical(ics_data)
#
#     # Проходим по всем событиям в календаре
#     for component in cal.walk():
#         if component.name == "VEVENT":
#             # Изменение данных события
#             summary = component.get('summary')
#             if summary == "RC(39426719)":  # Изменяем событие с конкретным UID или summary
#                 print(f"Original Summary: {summary}")
#
#                 # Меняем summary (заголовок события)
#                 component['summary'] = "Changed Summary Event"
#
#                 # Меняем дату начала и конца
#                 new_dtstart = datetime(2024, 9, 20, 9, 0, 0)
#                 new_dtend = new_dtstart + timedelta(hours=2)
#                 component['dtstart'].dt = new_dtstart
#                 component['dtend'].dt = new_dtend
#
#                 print(f"Updated Summary: {component.get('summary')}")
#                 print(f"Updated Start: {component.get('dtstart').dt}")
#                 print(f"Updated End: {component.get('dtend').dt}")
#
#     # Сохраняем изменения в новый файл
#     with open('updated_calendar.ics', 'wb') as f:
#         f.write(cal.to_ical())
#
#     print("Файл обновлен и сохранен как 'updated_calendar.ics'.")
# else:
#     print(f"Ошибка загрузки данных. Статус код: {response.status_code}")




####################################################################
# # Добавление нового события
# new_event = Event()
# new_event.add('summary', 'My New Event')
# new_event.add('dtstart', datetime(2024, 9, 25, 14, 0, 0))
# new_event.add('dtend', datetime(2024, 9, 25, 16, 0, 0))
# new_event.add('description', 'Описание моего нового события')
# new_event.add('location', 'Город, Улица, 123')
# new_event.add('uid', 'new-event-12345')
#
# cal.add_component(new_event)
####################################################################
####################################################################
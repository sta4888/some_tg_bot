import os
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from icalendar import Calendar, Event
from datetime import datetime
from pathlib import Path

app = FastAPI()

# Папка для хранения сгенерированных файлов
ICAL_FILES_DIR = Path("./ical_files")
ICAL_FILES_DIR.mkdir(exist_ok=True)


class EventData(BaseModel):
    summary: str
    description: str
    location: str
    dtstart: datetime
    dtend: datetime


@app.post("/generate_ical/")
def generate_ical():
    # Генерируем уникальный идентификатор файла
    unique_id = uuid.uuid4().hex[:16]  # UUID-4 как уникальный идентификатор
    filename = f"{unique_id}.ical"
    filepath = ICAL_FILES_DIR / filename

    # Создаем новый календарь
    cal = Calendar()
    cal.add('prodid', '-//My Calendar Product//mycalendar.com//')
    cal.add('version', '2.0')
    cal.add('calscale', 'GREGORIAN')

    # Сохраняем пустой файл
    with open(filepath, 'wb') as f:
        f.write(cal.to_ical())

    return {"message": "iCal file generated", "url": f"/ical/{unique_id}"}


@app.post("/ical/{unique_id}/add_event/")
def add_event(unique_id: str, event_data: EventData):
    # Путь к файлу
    filepath = ICAL_FILES_DIR / f"{unique_id}.ical"

    # Проверяем существует ли файл
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="iCal file not found")

    # Загружаем календарь
    with open(filepath, 'rb') as f:
        cal = Calendar.from_ical(f.read())

    # Создаем новое событие
    event = Event()
    event.add('summary', event_data.summary)
    event.add('dtstart', event_data.dtstart)
    event.add('dtend', event_data.dtend)
    event.add('description', event_data.description)
    event.add('location', event_data.location)
    event.add('uid', unique_id)

    # Добавляем событие в календарь
    cal.add_component(event)

    # Сохраняем изменения
    with open(filepath, 'wb') as f:
        f.write(cal.to_ical())

    return {"message": "Event added", "url": f"/ical/{unique_id}"}


@app.get("/ical/{unique_id}")
def get_ical_file(unique_id: str):
    # Путь к файлу
    filepath = ICAL_FILES_DIR / f"{unique_id}.ical"

    # Проверяем существует ли файл
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="iCal file not found")

    # Возвращаем файл
    return FileResponse(filepath, media_type='text/calendar', filename=f"{unique_id}.ical")



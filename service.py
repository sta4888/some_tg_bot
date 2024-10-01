from datetime import datetime
from random import randint
from fuzzywuzzy import process
import icalendar
import requests
from sqlalchemy import and_
from sqlalchemy.orm import joinedload

from connect import session, Session
from models import Location, Offer, Event

from io import BytesIO

import segno
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def find_offers(city, start_date, end_date, guest_count, bedrooms, amenities=None):
    # Поиск местоположения по городу
    locations = session.query(Location).filter(Location.locality_name.ilike(f'%{city}%')).all()
    print(f"--locations {locations}")

    end_date = datetime.strptime(end_date, '%Y-%m-%d')
    start_date = datetime.strptime(start_date, '%Y-%m-%d')

    if not locations:
        return None  # Если нет предложений в этом городе

    print(city, start_date, end_date, guest_count, bedrooms, amenities)

    # Начало фильтрации предложений
    query = session.query(Offer).options(joinedload(Offer.photos)).filter(
        Offer.location_id.in_([loc.id for loc in locations]),  # Предложения по найденным локациям
        Offer.available_on_file.is_(True),  # Только доступные предложения
        Offer.sleeps == bedrooms  # Учитываем количество гостей
    )

    # Учитываем выбранные удобства, если они переданы
    # if amenities:
    #     for amenity in amenities:
    #         query = query.filter(getattr(Offer, amenity).is_(True))

    offers = query.all()
    print(f"--offers {offers}")

    # Фильтруем предложения по датам
    valid_offers = []
    for offer in offers:
        # Получаем события, связанные с предложением
        events = session.query(Event).filter(Event.offer_id == offer.id).all()

        is_valid = True
        for event in events:
            # Проверяем, пересекаются ли даты
            if not (end_date <= event.start_time or start_date >= event.end_time):
                # Если даты пересекаются, то оффер не подходит
                is_valid = False
                break

        if is_valid:
            valid_offers.append(offer)

    return valid_offers


def parse_ical(ical_url, offer, session: Session):
    # Получаем календарь по ссылке

    response = requests.get(ical_url)
    if response.status_code != 200:
        print(f"Ошибка при загрузке календаря: {response.status_code}")
        return

    ical_string = response.content
    calendar = icalendar.Calendar.from_ical(ical_string)

    for component in calendar.walk():
        if component.name == "VEVENT":
            uid = component.get('UID')
            start_time = component.get('DTSTART').dt
            end_time = component.get('DTEND').dt
            summary = component.get('SUMMARY')

            # Проверяем, существует ли уже такое событие
            existing_event = session.query(Event).filter(
                and_(
                    Event.uid == uid,
                    Event.start_time == start_time,
                    Event.end_time == end_time,
                    Event.offer == offer  # если offer уникален для сотрудника
                )
            ).first()

            if existing_event:
                # Если событие уже существует, пропускаем его
                print(f"Событие {uid} уже существует. Пропуск.")
                continue

            # Если событие не найдено, создаем его
            event = Event(
                offer=offer,
                uid=uid,
                start_time=start_time,
                end_time=end_time,
                summary=summary
            )
            session.add(event)

    # Сохраняем изменения
    session.commit()


def qr_generate(qr_data: str, pdf_file: str) -> None:
    qrcode = segno.make_qr(qr_data)
    image_file = "darkblue_qrcode.png"
    qrcode.save(
        image_file,
        scale=3,
        border=None,
        dark="darkblue",
    )
    output_pdf = 'darkblue_qrcode.pdf'

    insert_image_to_pdf(pdf_file, output_pdf, image_file, 90, 26)


def insert_image_to_pdf(existing_pdf, output_pdf, image_path, x, y):
    # Create a PDF with the image
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    can.drawImage(image_path, x, y)  # x, y coordinates where to place the image
    can.save()

    # Move to the beginning of the BytesIO buffer
    packet.seek(0)
    new_pdf = PdfReader(packet)

    # Read the existing PDF
    existing_pdf_reader = PdfReader(existing_pdf)
    pdf_writer = PdfWriter()

    # Add the image to each page of the existing PDF
    for page in existing_pdf_reader.pages:
        page.merge_page(new_pdf.pages[0])  # Merge the new image PDF with the existing page
        pdf_writer.add_page(page)

    # Write to the output PDF
    with open(output_pdf, "wb") as output_file:
        pdf_writer.write(output_file)


def random_with_N_digits(n):
    range_start = 10 ** (n - 1)
    range_end = (10 ** n) - 1
    return randint(range_start, range_end)


# Список городов (можно взять из базы данных или API)
cities = ["абаза", "абакан", "абдулино", "абинск", "агидель", "агрыз", "адыгейск", "азнакаево", "азов", "ак-довурак",
          "аксай", "алагир", "алапаевск", "алатырь", "алдан", "алейск", "александров", "александровск",
          "александровск-сахалинский", "алексеевка", "алексин", "алзамай", "алупкане призн.", "алуштане призн.",
          "альметьевск", "амурск", "анадырь", "анапа", "ангарск", "андреаполь", "анжеро-судженск", "анива", "апатиты",
          "апрелевка", "апшеронск", "арамиль", "аргун", "ардатов", "ардон", "арзамас", "аркадак", "армавир",
          "армянскне призн.", "арсеньев", "арск", "артём", "артёмовск", "артёмовский", "архангельск", "асбест", "асино",
          "астрахань", "аткарск", "ахтубинск", "ачинск", "ачхой-мартан", "аша", "бабаево", "бабушкин", "бавлы",
          "багратионовск", "байкальск", "баймак", "бакал", "баксан", "балабаново", "балаково", "балахна", "балашиха",
          "балашов", "балей", "балтийск", "барабинск", "барнаул", "барыш", "батайск", "бахчисарайне призн.", "бежецк",
          "белая калитва", "белая холуница", "белгород", "белебей", "белёв", "белинский", "белово", "белогорск",
          "белогорскне призн.", "белозерск", "белокуриха", "беломорск", "белоозёрский", "белорецк", "белореченск",
          "белоусово", "белоярский", "белый", "бердск", "березники", "берёзовский", "берёзовский", "беслан", "бийск",
          "бикин", "билибино", "биробиджан", "бирск", "бирюсинск", "бирюч", "благовещенск", "благовещенск",
          "благодарный", "бобров", "богданович", "богородицк", "богородск", "боготол", "богучар", "бодайбо",
          "бокситогорск", "болгар", "бологое", "болотное", "болохово", "болхов", "большой камень", "бор", "борзя",
          "борисоглебск", "боровичи", "боровск", "бородино", "братск", "бронницы", "брянск", "бугры", "бугульма",
          "бугуруслан", "будённовск", "бузулук", "буинск", "буй", "буйнакск", "бутурлиновка", "валдай", "валуйки",
          "велиж", "великие луки", "великий новгород", "великий устюг", "вельск", "венёв", "верещагино", "верея",
          "верхнеуральск", "верхний тагил", "верхний уфалей", "верхняя пышма", "верхняя салда", "верхняя тура",
          "верхотурье", "верхоянск", "весьегонск", "ветлуга", "видное", "вилюйск", "вилючинск", "вихоревка", "вичуга",
          "владивосток", "владикавказ", "владимир", "волгоград", "волгодонск", "волгореченск", "волжск", "волжский",
          "вологда", "володарск", "волоколамск", "волосово", "волхов", "волчанск", "вольск", "воркута", "воронеж",
          "ворсма", "воскресенск", "воткинск", "всеволожск", "вуктыл", "выборг", "выкса", "высоковск", "высоцк",
          "вытегра", "вышний волочёк", "вяземский", "вязники", "вязьма", "вятские поляны", "гаврилов посад",
          "гаврилов-ям", "гагарин", "гаджиево", "гай", "галич", "гатчина", "гвардейск", "гдов", "геленджик",
          "георгиевск", "глазов", "голицыно", "горбатов", "горно-алтайск", "горнозаводск", "горняк", "городец",
          "городище", "городовиковск", "гороховец", "горячий ключ", "грайворон", "гремячинск", "грозный", "грязи",
          "грязовец", "губаха", "губкин", "губкинский", "гудермес", "гуково", "гулькевичи", "гурьевск", "гурьевск",
          "гусев", "гусиноозёрск", "гусь-хрустальный", "давлеканово", "дагестанские огни", "далматово", "дальнегорск",
          "дальнереченск", "данилов", "данков", "дегтярск", "дедовск", "демидов", "дербент", "десногорск",
          "джанкойне призн.", "дзержинск", "дзержинский", "дивногорск", "дигора", "димитровград", "дмитриев", "дмитров",
          "дмитровск", "дно", "добрянка", "долгопрудный", "долинск", "домодедово", "донецк", "донской", "дорогобуж",
          "дрезна", "дубна", "дубовка", "дудинка", "духовщина", "дюртюли", "дятьково", "евпаторияне призн.",
          "егорьевск", "ейск", "екатеринбург", "елабуга", "елец", "елизово", "ельня", "еманжелинск", "емва", "енисейск",
          "ермолино", "ершов", "ессентуки", "ефремов", "железноводск", "железногорск", "железногорск",
          "железногорск-илимский", "жердевка", "жигулёвск", "жиздра", "жирновск", "жуков", "жуковка", "жуковский",
          "завитинск", "заводоуковск", "заволжск", "заволжье", "задонск", "заинск", "закаменск", "заозёрный",
          "заозёрск", "западная двина", "заполярный", "зарайск", "заречный", "заречный", "заринск", "звенигово",
          "звенигород", "зверево", "зеленогорск", "зеленоградск", "зеленодольск", "зеленокумск", "зерноград", "зея",
          "зима", "златоуст", "злынка", "змеиногорск", "знаменск", "зубцов", "зуевка", "ивангород", "иваново",
          "ивантеевка", "ивдель", "игарка", "ижевск", "избербаш", "изобильный", "иланский", "инза", "иннополис",
          "инсар", "инта", "ипатово", "ирбит", "иркутск", "исилькуль", "искитим", "истра", "ишим", "ишимбай",
          "йошкар-ола", "кадников", "казань", "калач", "калач-на-дону", "калачинск", "калининград", "калининск",
          "калтан", "калуга", "калязин", "камбарка", "каменка", "каменногорск", "каменск-уральский",
          "каменск-шахтинский", "камень-на-оби", "камешково", "камызяк", "камышин", "камышлов", "канаш", "кандалакша",
          "канск", "карабаново", "карабаш", "карабулак", "карасук", "карачаевск", "карачев", "каргат", "каргополь",
          "карпинск", "карталы", "касимов", "касли", "каспийск", "катав-ивановск", "катайск", "качканар", "кашин",
          "кашира", "кедровый", "кемерово", "кемь", "керчьне призн.", "кизел", "кизилюрт", "кизляр", "кимовск", "кимры",
          "кингисепп", "кинель", "кинешма", "киреевск", "киренск", "киржач", "кириллов", "кириши", "киров", "киров",
          "кировград", "кирово-чепецк", "кировск", "кировск", "кирс", "кирсанов", "киселёвск", "кисловодск", "клин",
          "клинцы", "княгинино", "ковдор", "ковров", "ковылкино", "когалым", "кодинск", "козельск", "козловка",
          "козьмодемьянск", "кола", "кологрив", "коломна", "колпашево", "колтуши", "кольчугино", "коммунар",
          "комсомольск", "комсомольск-на-амуре", "конаково", "кондопога", "кондрово", "константиновск", "копейск",
          "кораблино", "кореновск", "коркино", "королёв", "короча", "корсаков", "коряжма", "костерёво", "костомукша",
          "кострома", "котельники", "котельниково", "котельнич", "котлас", "котово", "котовск", "кохма", "красавино",
          "красноармейск", "красноармейск", "красновишерск", "красногорск", "краснодар", "краснозаводск",
          "краснознаменск", "краснознаменск", "краснокаменск", "краснокамск", "красноперекопскне призн.",
          "краснослободск", "краснослободск", "краснотурьинск", "красноуральск", "красноуфимск", "красноярск",
          "красный кут", "красный сулин", "красный холм", "кремёнки", "кропоткин", "крымск", "кстово", "кубинка",
          "кувандык", "кувшиново", "кудрово", "кудымкар", "кузнецк", "куйбышев", "кукмор", "кулебаки", "кумертау",
          "кунгур", "купино", "курган", "курганинск", "курильск", "курлово", "куровское", "курск", "куртамыш",
          "курчалой", "курчатов", "куса", "кушва", "кызыл", "кыштым", "кяхта", "лабинск", "лабытнанги", "лагань",
          "ладушкин", "лаишево", "лакинск", "лангепас", "лахденпохья", "лебедянь", "лениногорск", "ленинск",
          "ленинск-кузнецкий", "ленск", "лермонтов", "лесной", "лесозаводск", "лесосибирск", "ливны", "ликино-дулёво",
          "липецк", "липки", "лиски", "лихославль", "лобня", "лодейное поле", "лосино-петровский", "луга", "луза",
          "лукоянов", "луховицы", "лысково", "лысьва", "лыткарино", "льгов", "любань", "люберцы", "любим", "людиново",
          "лянтор", "магадан", "магас", "магнитогорск", "майкоп", "майский", "макаров", "макарьев", "макушино",
          "малая вишера", "малгобек", "малмыж", "малоархангельск", "малоярославец", "мамадыш", "мамоново", "мантурово",
          "мариинск", "мариинский посад", "маркс", "махачкала", "мглин", "мегион", "медвежьегорск", "медногорск",
          "медынь", "межгорье", "междуреченск", "мезень", "меленки", "мелеуз", "менделеевск", "мензелинск", "мещовск",
          "миасс", "микунь", "миллерово", "минеральные воды", "минусинск", "миньяр", "мирный", "мирный", "михайлов",
          "михайловка", "михайловск", "михайловск", "мичуринск", "могоча", "можайск", "можга", "моздок", "мончегорск",
          "морозовск", "моршанск", "мосальск", "москва", "муравленко", "мураши", "мурино", "мурманск", "муром",
          "мценск", "мыски", "мытищи", "мышкин", "набережные челны", "навашино", "наволоки", "надым", "назарово",
          "назрань", "называевск", "нальчик", "нариманов", "наро-фоминск", "нарткала", "нарьян-мар", "наурская",
          "находка", "невель", "невельск", "невинномысск", "невьянск", "нелидово", "неман", "нерехта", "нерчинск",
          "нерюнгри", "нестеров", "нефтегорск", "нефтекамск", "нефтекумск", "нефтеюганск", "нея", "нижневартовск",
          "нижнекамск", "нижнеудинск", "нижние серги", "нижний ломов", "нижний новгород", "нижний тагил",
          "нижняя салда", "нижняя тура", "николаевск", "николаевск-на-амуре", "никольск", "никольск", "никольское",
          "новая ладога", "новая ляля", "новоалександровск", "новоалтайск", "новоаннинский", "нововоронеж",
          "новодвинск", "новозыбков", "новокубанск", "новокузнецк", "новокуйбышевск", "новомичуринск", "новомосковск",
          "новопавловск", "новоржев", "новороссийск", "новосибирск", "новосиль", "новосокольники", "новотроицк",
          "новоузенск", "новоульяновск", "новоуральск", "новохопёрск", "новочебоксарск", "новочеркасск", "новошахтинск",
          "новый оскол", "новый уренгой", "ногинск", "нолинск", "норильск", "ноябрьск", "нурлат", "нытва", "нюрба",
          "нягань", "нязепетровск", "няндома", "облучье", "обнинск", "обоянь", "обь", "одинцово", "озёрск", "озёрск",
          "озёры", "ойсхара", "октябрьск", "октябрьский", "окуловка", "олёкминск", "оленегорск", "олонец", "омск",
          "омутнинск", "онега", "опочка", "орёл", "оренбург", "орехово-зуево", "орлов", "орск", "оса", "осинники",
          "осташков", "остров", "островной", "острогожск", "отрадное", "отрадный", "оха", "оханск", "очёр", "павлово",
          "павловск", "павловский посад", "палласовка", "партизанск", "певек", "пенза", "первомайск", "первоуральск",
          "перевоз", "пересвет", "переславль-залесский", "пермь", "пестово", "петров вал", "петровск",
          "петровск-забайкальский", "петрозаводск", "петропавловск-камчатский", "петухово", "петушки", "печора",
          "печоры", "пикалёво", "пионерский", "питкяранта", "плавск", "пласт", "плёс", "поворино", "подольск",
          "подпорожье", "покачи", "покров", "покровск", "полевской", "полесск", "полысаево", "полярные зори",
          "полярный", "поронайск", "порхов", "похвистнево", "почеп", "починок", "пошехонье", "правдинск", "приволжск",
          "приморск", "приморск", "приморско-ахтарск", "приозерск", "прокопьевск", "пролетарск", "протвино",
          "прохладный", "псков", "пугачёв", "пудож", "пустошка", "пучеж", "пушкино", "пущино", "пыталово", "пыть-ях",
          "пятигорск", "радужный", "радужный", "райчихинск", "раменское", "рассказово", "ревда", "реж", "реутов",
          "ржев", "родники", "рославль", "россошь", "ростов-на-дону", "ростов", "рошаль", "ртищево", "рубцовск",
          "рудня", "руза", "рузаевка", "рыбинск", "рыбное", "рыльск", "ряжск", "рязань", "сакине призн.", "салават",
          "салаир", "салехард", "сальск", "самара", "санкт-петербург", "саранск", "сарапул", "саратов", "саров",
          "сасово", "сатка", "сафоново", "саяногорск", "саянск", "светлогорск", "светлоград", "светлый", "светогорск",
          "свирск", "свободный", "себеж", "севастопольне призн.", "северо-курильск", "северобайкальск", "северодвинск",
          "североморск", "североуральск", "северск", "севск", "сегежа", "сельцо", "семёнов", "семикаракорск",
          "семилуки", "сенгилей", "серафимович", "сергач", "сергиев посад", "сердобск", "серноводское", "серов",
          "серпухов", "сертолово", "сибай", "сим", "симферопольне призн.", "сковородино", "скопин", "славгород",
          "славск", "славянск-на-кубани", "сланцы", "слободской", "слюдянка", "смоленск", "снежинск", "снежногорск",
          "собинка", "советск", "советск", "советск", "советская гавань", "советский", "сокол", "солигалич",
          "соликамск", "солнечногорск", "соль-илецк", "сольвычегодск", "сольцы", "сорочинск", "сорск", "сортавала",
          "сосенский", "сосновка", "сосновоборск", "сосновый бор", "сосногорск", "сочи", "спас-деменск", "спас-клепики",
          "спасск", "спасск-дальний", "спасск-рязанский", "среднеколымск", "среднеуральск", "сретенск", "ставрополь",
          "старая купавна", "старая русса", "старица", "стародуб", "старый крымне призн.", "старый оскол",
          "стерлитамак", "стрежевой", "строитель", "струнино", "ступино", "суворов", "судакне призн.", "суджа",
          "судогда", "суздаль", "сунжа", "суоярви", "сураж", "сургут", "суровикино", "сурск", "сусуман", "сухиничи",
          "сухой лог", "сызрань", "сыктывкар", "сысерть", "сычёвка", "сясьстрой", "тавда", "таганрог", "тайга",
          "тайшет", "талдом", "талица", "тамбов", "тара", "тарко-сале", "таруса", "татарск", "таштагол", "тверь",
          "теберда", "тейково", "тельмана", "темников", "темрюк", "терек", "тетюши", "тимашёвск", "тихвин", "тихорецк",
          "тобольск", "тогучин", "тольятти", "томари", "томмот", "томск", "топки", "торжок", "торопец", "тосно",
          "тотьма", "трёхгорный", "троицк", "трубчевск", "туапсе", "туймазы", "тула", "тулун", "туран", "туринск",
          "тутаев", "тында", "тырныауз", "тюкалинск", "тюмень", "уварово", "углегорск", "углич", "удачный", "удомля",
          "ужур", "узловая", "улан-удэ", "ульяновск", "унеча", "урай", "урень", "уржум", "урус-мартан", "урюпинск",
          "усинск", "усмань", "усолье-сибирское", "усолье", "уссурийск", "усть-джегута", "усть-илимск", "усть-катав",
          "усть-кут", "усть-лабинск", "устюжна", "уфа", "ухта", "учалы", "уяр", "фатеж", "феодосияне призн.", "фокино",
          "фокино", "фролово", "фрязино", "фурманов", "хабаровск", "хадыженск", "ханты-мансийск", "харабали", "харовск",
          "хасавюрт", "хвалынск", "хилок", "химки", "холм", "холмск", "хотьково", "цивильск", "цимлянск", "циолковский",
          "чадан", "чайковский", "чапаевск", "чаплыгин", "чебаркуль", "чебоксары", "чегем", "чекалин", "челябинск",
          "чердынь", "черемхово", "черепаново", "череповец", "черкесск", "чёрмоз", "черноголовка", "черногорск",
          "чернушка", "черняховск", "чехов", "чистополь", "чита", "чкаловск", "чудово", "чулым", "чусовой", "чухлома",
          "шагонар", "шадринск", "шали", "шарыпово", "шарья", "шатура", "шахты", "шахунья", "шацк", "шебекино",
          "шелехов", "шелковская", "шенкурск", "шилка", "шимановск", "шиханы", "шлиссельбург", "шумерля", "шумиха",
          "шуя", "щёкино", "щёлкиноне призн.", "щёлково", "щигры", "щучье", "электрогорск", "электросталь",
          "электроугли", "элиста", "энгельс", "эртиль", "югорск", "южа", "южно-сахалинск", "южно-сухокумск",
          "южноуральск", "юрга", "юрьев-польский", "юрьевец", "юрюзань", "юхнов", "ядрин", "якутск", "ялтане призн.",
          "ялуторовск", "янаул", "яранск", "яровое", "ярославль", "ярцево", "ясногорск", "ясный", "яхрома"]
cities_true = ["Абаза", "Абакан", "Абдулино", "Абинск", "Агидель", "Агрыз", "Адыгейск", "Азнакаево", "Азов",
               "Ак-Довурак", "Аксай", "Алагир", "Алапаевск", "Алатырь", "Алдан", "Алейск", "Александров",
               "Александровск", "Александровск-Сахалинский", "Алексеевка", "Алексин", "Алзамай", "Алупкане призн.",
               "Алуштане призн.", "Альметьевск", "Амурск", "Анадырь", "Анапа", "Ангарск", "Андреаполь",
               "Анжеро-Судженск", "Анива", "Апатиты", "Апрелевка", "Апшеронск", "Арамиль", "Аргун", "Ардатов", "Ардон",
               "Арзамас", "Аркадак", "Армавир", "Армянскне призн.", "Арсеньев", "Арск", "Артём", "Артёмовск",
               "Артёмовский", "Архангельск", "Асбест", "Асино", "Астрахань", "Аткарск", "Ахтубинск", "Ачинск",
               "Ачхой-Мартан", "Аша", "Бабаево", "Бабушкин", "Бавлы", "Багратионовск", "Байкальск", "Баймак", "Бакал",
               "Баксан", "Балабаново", "Балаково", "Балахна", "Балашиха", "Балашов", "Балей", "Балтийск", "Барабинск",
               "Барнаул", "Барыш", "Батайск", "Бахчисарайне призн.", "Бежецк", "Белая Калитва", "Белая Холуница",
               "Белгород", "Белебей", "Белёв", "Белинский", "Белово", "Белогорск", "Белогорскне призн.", "Белозерск",
               "Белокуриха", "Беломорск", "Белоозёрский", "Белорецк", "Белореченск", "Белоусово", "Белоярский", "Белый",
               "Бердск", "Березники", "Берёзовский", "Берёзовский", "Беслан", "Бийск", "Бикин", "Билибино",
               "Биробиджан", "Бирск", "Бирюсинск", "Бирюч", "Благовещенск", "Благовещенск", "Благодарный", "Бобров",
               "Богданович", "Богородицк", "Богородск", "Боготол", "Богучар", "Бодайбо", "Бокситогорск", "Болгар",
               "Бологое", "Болотное", "Болохово", "Болхов", "Большой Камень", "Бор", "Борзя", "Борисоглебск",
               "Боровичи", "Боровск", "Бородино", "Братск", "Бронницы", "Брянск", "Бугры", "Бугульма", "Бугуруслан",
               "Будённовск", "Бузулук", "Буинск", "Буй", "Буйнакск", "Бутурлиновка", "Валдай", "Валуйки", "Велиж",
               "Великие Луки", "Великий Новгород", "Великий Устюг", "Вельск", "Венёв", "Верещагино", "Верея",
               "Верхнеуральск", "Верхний Тагил", "Верхний Уфалей", "Верхняя Пышма", "Верхняя Салда", "Верхняя Тура",
               "Верхотурье", "Верхоянск", "Весьегонск", "Ветлуга", "Видное", "Вилюйск", "Вилючинск", "Вихоревка",
               "Вичуга", "Владивосток", "Владикавказ", "Владимир", "Волгоград", "Волгодонск", "Волгореченск", "Волжск",
               "Волжский", "Вологда", "Володарск", "Волоколамск", "Волосово", "Волхов", "Волчанск", "Вольск", "Воркута",
               "Воронеж", "Ворсма", "Воскресенск", "Воткинск", "Всеволожск", "Вуктыл", "Выборг", "Выкса", "Высоковск",
               "Высоцк", "Вытегра", "Вышний Волочёк", "Вяземский", "Вязники", "Вязьма", "Вятские Поляны",
               "Гаврилов Посад", "Гаврилов-Ям", "Гагарин", "Гаджиево", "Гай", "Галич", "Гатчина", "Гвардейск", "Гдов",
               "Геленджик", "Георгиевск", "Глазов", "Голицыно", "Горбатов", "Горно-Алтайск", "Горнозаводск", "Горняк",
               "Городец", "Городище", "Городовиковск", "Гороховец", "Горячий Ключ", "Грайворон", "Гремячинск",
               "Грозный", "Грязи", "Грязовец", "Губаха", "Губкин", "Губкинский", "Гудермес", "Гуково", "Гулькевичи",
               "Гурьевск", "Гурьевск", "Гусев", "Гусиноозёрск", "Гусь-Хрустальный", "Давлеканово", "Дагестанские Огни",
               "Далматово", "Дальнегорск", "Дальнереченск", "Данилов", "Данков", "Дегтярск", "Дедовск", "Демидов",
               "Дербент", "Десногорск", "Джанкойне призн.", "Дзержинск", "Дзержинский", "Дивногорск", "Дигора",
               "Димитровград", "Дмитриев", "Дмитров", "Дмитровск", "Дно", "Добрянка", "Долгопрудный", "Долинск",
               "Домодедово", "Донецк", "Донской", "Дорогобуж", "Дрезна", "Дубна", "Дубовка", "Дудинка", "Духовщина",
               "Дюртюли", "Дятьково", "Евпаторияне призн.", "Егорьевск", "Ейск", "Екатеринбург", "Елабуга", "Елец",
               "Елизово", "Ельня", "Еманжелинск", "Емва", "Енисейск", "Ермолино", "Ершов", "Ессентуки", "Ефремов",
               "Железноводск", "Железногорск", "Железногорск", "Железногорск-Илимский", "Жердевка", "Жигулёвск",
               "Жиздра", "Жирновск", "Жуков", "Жуковка", "Жуковский", "Завитинск", "Заводоуковск", "Заволжск",
               "Заволжье", "Задонск", "Заинск", "Закаменск", "Заозёрный", "Заозёрск", "Западная Двина", "Заполярный",
               "Зарайск", "Заречный", "Заречный", "Заринск", "Звенигово", "Звенигород", "Зверево", "Зеленогорск",
               "Зеленоградск", "Зеленодольск", "Зеленокумск", "Зерноград", "Зея", "Зима", "Златоуст", "Злынка",
               "Змеиногорск", "Знаменск", "Зубцов", "Зуевка", "Ивангород", "Иваново", "Ивантеевка", "Ивдель", "Игарка",
               "Ижевск", "Избербаш", "Изобильный", "Иланский", "Инза", "Иннополис", "Инсар", "Инта", "Ипатово", "Ирбит",
               "Иркутск", "Исилькуль", "Искитим", "Истра", "Ишим", "Ишимбай", "Йошкар-Ола", "Кадников", "Казань",
               "Калач", "Калач-на-Дону", "Калачинск", "Калининград", "Калининск", "Калтан", "Калуга", "Калязин",
               "Камбарка", "Каменка", "Каменногорск", "Каменск-Уральский", "Каменск-Шахтинский", "Камень-на-Оби",
               "Камешково", "Камызяк", "Камышин", "Камышлов", "Канаш", "Кандалакша", "Канск", "Карабаново", "Карабаш",
               "Карабулак", "Карасук", "Карачаевск", "Карачев", "Каргат", "Каргополь", "Карпинск", "Карталы", "Касимов",
               "Касли", "Каспийск", "Катав-Ивановск", "Катайск", "Качканар", "Кашин", "Кашира", "Кедровый", "Кемерово",
               "Кемь", "Керчьне призн.", "Кизел", "Кизилюрт", "Кизляр", "Кимовск", "Кимры", "Кингисепп", "Кинель",
               "Кинешма", "Киреевск", "Киренск", "Киржач", "Кириллов", "Кириши", "Киров", "Киров", "Кировград",
               "Кирово-Чепецк", "Кировск", "Кировск", "Кирс", "Кирсанов", "Киселёвск", "Кисловодск", "Клин", "Клинцы",
               "Княгинино", "Ковдор", "Ковров", "Ковылкино", "Когалым", "Кодинск", "Козельск", "Козловка",
               "Козьмодемьянск", "Кола", "Кологрив", "Коломна", "Колпашево", "Колтуши", "Кольчугино", "Коммунар",
               "Комсомольск", "Комсомольск-на-Амуре", "Конаково", "Кондопога", "Кондрово", "Константиновск", "Копейск",
               "Кораблино", "Кореновск", "Коркино", "Королёв", "Короча", "Корсаков", "Коряжма", "Костерёво",
               "Костомукша", "Кострома", "Котельники", "Котельниково", "Котельнич", "Котлас", "Котово", "Котовск",
               "Кохма", "Красавино", "Красноармейск", "Красноармейск", "Красновишерск", "Красногорск", "Краснодар",
               "Краснозаводск", "Краснознаменск", "Краснознаменск", "Краснокаменск", "Краснокамск",
               "Красноперекопскне призн.", "Краснослободск", "Краснослободск", "Краснотурьинск", "Красноуральск",
               "Красноуфимск", "Красноярск", "Красный Кут", "Красный Сулин", "Красный Холм", "Кремёнки", "Кропоткин",
               "Крымск", "Кстово", "Кубинка", "Кувандык", "Кувшиново", "Кудрово", "Кудымкар", "Кузнецк", "Куйбышев",
               "Кукмор", "Кулебаки", "Кумертау", "Кунгур", "Купино", "Курган", "Курганинск", "Курильск", "Курлово",
               "Куровское", "Курск", "Куртамыш", "Курчалой", "Курчатов", "Куса", "Кушва", "Кызыл", "Кыштым", "Кяхта",
               "Лабинск", "Лабытнанги", "Лагань", "Ладушкин", "Лаишево", "Лакинск", "Лангепас", "Лахденпохья",
               "Лебедянь", "Лениногорск", "Ленинск", "Ленинск-Кузнецкий", "Ленск", "Лермонтов", "Лесной", "Лесозаводск",
               "Лесосибирск", "Ливны", "Ликино-Дулёво", "Липецк", "Липки", "Лиски", "Лихославль", "Лобня",
               "Лодейное Поле", "Лосино-Петровский", "Луга", "Луза", "Лукоянов", "Луховицы", "Лысково", "Лысьва",
               "Лыткарино", "Льгов", "Любань", "Люберцы", "Любим", "Людиново", "Лянтор", "Магадан", "Магас",
               "Магнитогорск", "Майкоп", "Майский", "Макаров", "Макарьев", "Макушино", "Малая Вишера", "Малгобек",
               "Малмыж", "Малоархангельск", "Малоярославец", "Мамадыш", "Мамоново", "Мантурово", "Мариинск",
               "Мариинский Посад", "Маркс", "Махачкала", "Мглин", "Мегион", "Медвежьегорск", "Медногорск", "Медынь",
               "Межгорье", "Междуреченск", "Мезень", "Меленки", "Мелеуз", "Менделеевск", "Мензелинск", "Мещовск",
               "Миасс", "Микунь", "Миллерово", "Минеральные Воды", "Минусинск", "Миньяр", "Мирный", "Мирный",
               "Михайлов", "Михайловка", "Михайловск", "Михайловск", "Мичуринск", "Могоча", "Можайск", "Можга",
               "Моздок", "Мончегорск", "Морозовск", "Моршанск", "Мосальск", "Москва", "Муравленко", "Мураши", "Мурино",
               "Мурманск", "Муром", "Мценск", "Мыски", "Мытищи", "Мышкин", "Набережные Челны", "Навашино", "Наволоки",
               "Надым", "Назарово", "Назрань", "Называевск", "Нальчик", "Нариманов", "Наро-Фоминск", "Нарткала",
               "Нарьян-Мар", "Наурская", "Находка", "Невель", "Невельск", "Невинномысск", "Невьянск", "Нелидово",
               "Неман", "Нерехта", "Нерчинск", "Нерюнгри", "Нестеров", "Нефтегорск", "Нефтекамск", "Нефтекумск",
               "Нефтеюганск", "Нея", "Нижневартовск", "Нижнекамск", "Нижнеудинск", "Нижние Серги", "Нижний Ломов",
               "Нижний Новгород", "Нижний Тагил", "Нижняя Салда", "Нижняя Тура", "Николаевск", "Николаевск-на-Амуре",
               "Никольск", "Никольск", "Никольское", "Новая Ладога", "Новая Ляля", "Новоалександровск", "Новоалтайск",
               "Новоаннинский", "Нововоронеж", "Новодвинск", "Новозыбков", "Новокубанск", "Новокузнецк",
               "Новокуйбышевск", "Новомичуринск", "Новомосковск", "Новопавловск", "Новоржев", "Новороссийск",
               "Новосибирск", "Новосиль", "Новосокольники", "Новотроицк", "Новоузенск", "Новоульяновск", "Новоуральск",
               "Новохопёрск", "Новочебоксарск", "Новочеркасск", "Новошахтинск", "Новый Оскол", "Новый Уренгой",
               "Ногинск", "Нолинск", "Норильск", "Ноябрьск", "Нурлат", "Нытва", "Нюрба", "Нягань", "Нязепетровск",
               "Няндома", "Облучье", "Обнинск", "Обоянь", "Обь", "Одинцово", "Озёрск", "Озёрск", "Озёры", "Ойсхара",
               "Октябрьск", "Октябрьский", "Окуловка", "Олёкминск", "Оленегорск", "Олонец", "Омск", "Омутнинск",
               "Онега", "Опочка", "Орёл", "Оренбург", "Орехово-Зуево", "Орлов", "Орск", "Оса", "Осинники", "Осташков",
               "Остров", "Островной", "Острогожск", "Отрадное", "Отрадный", "Оха", "Оханск", "Очёр", "Павлово",
               "Павловск", "Павловский Посад", "Палласовка", "Партизанск", "Певек", "Пенза", "Первомайск",
               "Первоуральск", "Перевоз", "Пересвет", "Переславль-Залесский", "Пермь", "Пестово", "Петров Вал",
               "Петровск", "Петровск-Забайкальский", "Петрозаводск", "Петропавловск-Камчатский", "Петухово", "Петушки",
               "Печора", "Печоры", "Пикалёво", "Пионерский", "Питкяранта", "Плавск", "Пласт", "Плёс", "Поворино",
               "Подольск", "Подпорожье", "Покачи", "Покров", "Покровск", "Полевской", "Полесск", "Полысаево",
               "Полярные Зори", "Полярный", "Поронайск", "Порхов", "Похвистнево", "Почеп", "Починок", "Пошехонье",
               "Правдинск", "Приволжск", "Приморск", "Приморск", "Приморско-Ахтарск", "Приозерск", "Прокопьевск",
               "Пролетарск", "Протвино", "Прохладный", "Псков", "Пугачёв", "Пудож", "Пустошка", "Пучеж", "Пушкино",
               "Пущино", "Пыталово", "Пыть-Ях", "Пятигорск", "Радужный", "Радужный", "Райчихинск", "Раменское",
               "Рассказово", "Ревда", "Реж", "Реутов", "Ржев", "Родники", "Рославль", "Россошь", "Ростов-на-Дону",
               "Ростов", "Рошаль", "Ртищево", "Рубцовск", "Рудня", "Руза", "Рузаевка", "Рыбинск", "Рыбное", "Рыльск",
               "Ряжск", "Рязань", "Сакине призн.", "Салават", "Салаир", "Салехард", "Сальск", "Самара",
               "Санкт-Петербург", "Саранск", "Сарапул", "Саратов", "Саров", "Сасово", "Сатка", "Сафоново", "Саяногорск",
               "Саянск", "Светлогорск", "Светлоград", "Светлый", "Светогорск", "Свирск", "Свободный", "Себеж",
               "Севастопольне призн.", "Северо-Курильск", "Северобайкальск", "Северодвинск", "Североморск",
               "Североуральск", "Северск", "Севск", "Сегежа", "Сельцо", "Семёнов", "Семикаракорск", "Семилуки",
               "Сенгилей", "Серафимович", "Сергач", "Сергиев Посад", "Сердобск", "Серноводское", "Серов", "Серпухов",
               "Сертолово", "Сибай", "Сим", "Симферопольне призн.", "Сковородино", "Скопин", "Славгород", "Славск",
               "Славянск-на-Кубани", "Сланцы", "Слободской", "Слюдянка", "Смоленск", "Снежинск", "Снежногорск",
               "Собинка", "Советск", "Советск", "Советск", "Советская Гавань", "Советский", "Сокол", "Солигалич",
               "Соликамск", "Солнечногорск", "Соль-Илецк", "Сольвычегодск", "Сольцы", "Сорочинск", "Сорск", "Сортавала",
               "Сосенский", "Сосновка", "Сосновоборск", "Сосновый Бор", "Сосногорск", "Сочи", "Спас-Деменск",
               "Спас-Клепики", "Спасск", "Спасск-Дальний", "Спасск-Рязанский", "Среднеколымск", "Среднеуральск",
               "Сретенск", "Ставрополь", "Старая Купавна", "Старая Русса", "Старица", "Стародуб",
               "Старый Крымне призн.", "Старый Оскол", "Стерлитамак", "Стрежевой", "Строитель", "Струнино", "Ступино",
               "Суворов", "Судакне призн.", "Суджа", "Судогда", "Суздаль", "Сунжа", "Суоярви", "Сураж", "Сургут",
               "Суровикино", "Сурск", "Сусуман", "Сухиничи", "Сухой Лог", "Сызрань", "Сыктывкар", "Сысерть", "Сычёвка",
               "Сясьстрой", "Тавда", "Таганрог", "Тайга", "Тайшет", "Талдом", "Талица", "Тамбов", "Тара", "Тарко-Сале",
               "Таруса", "Татарск", "Таштагол", "Тверь", "Теберда", "Тейково", "Тельмана", "Темников", "Темрюк",
               "Терек", "Тетюши", "Тимашёвск", "Тихвин", "Тихорецк", "Тобольск", "Тогучин", "Тольятти", "Томари",
               "Томмот", "Томск", "Топки", "Торжок", "Торопец", "Тосно", "Тотьма", "Трёхгорный", "Троицк", "Трубчевск",
               "Туапсе", "Туймазы", "Тула", "Тулун", "Туран", "Туринск", "Тутаев", "Тында", "Тырныауз", "Тюкалинск",
               "Тюмень", "Уварово", "Углегорск", "Углич", "Удачный", "Удомля", "Ужур", "Узловая", "Улан-Удэ",
               "Ульяновск", "Унеча", "Урай", "Урень", "Уржум", "Урус-Мартан", "Урюпинск", "Усинск", "Усмань",
               "Усолье-Сибирское", "Усолье", "Уссурийск", "Усть-Джегута", "Усть-Илимск", "Усть-Катав", "Усть-Кут",
               "Усть-Лабинск", "Устюжна", "Уфа", "Ухта", "Учалы", "Уяр", "Фатеж", "Феодосияне призн.", "Фокино",
               "Фокино", "Фролово", "Фрязино", "Фурманов", "Хабаровск", "Хадыженск", "Ханты-Мансийск", "Харабали",
               "Харовск", "Хасавюрт", "Хвалынск", "Хилок", "Химки", "Холм", "Холмск", "Хотьково", "Цивильск",
               "Цимлянск", "Циолковский", "Чадан", "Чайковский", "Чапаевск", "Чаплыгин", "Чебаркуль", "Чебоксары",
               "Чегем", "Чекалин", "Челябинск", "Чердынь", "Черемхово", "Черепаново", "Череповец", "Черкесск", "Чёрмоз",
               "Черноголовка", "Черногорск", "Чернушка", "Черняховск", "Чехов", "Чистополь", "Чита", "Чкаловск",
               "Чудово", "Чулым", "Чусовой", "Чухлома", "Шагонар", "Шадринск", "Шали", "Шарыпово", "Шарья", "Шатура",
               "Шахты", "Шахунья", "Шацк", "Шебекино", "Шелехов", "Шелковская", "Шенкурск", "Шилка", "Шимановск",
               "Шиханы", "Шлиссельбург", "Шумерля", "Шумиха", "Шуя", "Щёкино", "Щёлкиноне призн.", "Щёлково", "Щигры",
               "Щучье", "Электрогорск", "Электросталь", "Электроугли", "Элиста", "Энгельс", "Эртиль", "Югорск", "Южа",
               "Южно-Сахалинск", "Южно-Сухокумск", "Южноуральск", "Юрга", "Юрьев-Польский", "Юрьевец", "Юрюзань",
               "Юхнов", "Ядрин", "Якутск", "Ялтане призн.", "Ялуторовск", "Янаул", "Яранск", "Яровое", "Ярославль",
               "Ярцево", "Ясногорск", "Ясный", "Яхрома"]


def suggest_city(user_input):
    # Поиск до 3-х городов, которые больше всего похожи на введённое значение
    suggestions = process.extract(user_input, cities, limit=3)

    if suggestions:
        # Сформируем строку с вариантами
        # suggestions_text = ', '.join([suggestion[0] for suggestion in suggestions])
        return [suggestion[0] for suggestion in suggestions]
    else:
        return []

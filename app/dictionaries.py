"""
Справочники: перевод кодов из БД на русский язык.

В БД лежат английские коды (cafe, downtown, quiet, food ...), пользователю
показываем только русские названия. Названия заведений НЕ переводим.
Если кода нет в справочнике, показываем сам код — бот не упадёт,
а недостающий перевод легко заметить и дописать сюда.
"""

# код -> (эмодзи, название)

INTERESTS = {
    "food": ("🍽", "Еда"),
    "coffee": ("☕", "Кофе"),
    "desserts": ("🍰", "Десерты"),
    "drinks": ("🍹", "Напитки"),
    "conversation": ("💬", "Поговорить"),
    "social": ("👥", "Большой компанией"),
    "relax": ("😌", "Расслабиться"),
    "movies": ("🎬", "Кино"),
    "culture": ("🎭", "Культура"),
    "art": ("🎨", "Искусство"),
    "learning": ("📚", "Узнать новое"),
    "creative": ("✨", "Творчество"),
    "games": ("🎲", "Игры"),
    "gaming": ("🕹", "Аркады"),
    "board_games": ("♟", "Настолки"),
    "competitive": ("🏆", "Соревнования"),
    "active": ("🏃", "Активный отдых"),
    "adrenaline": ("⚡", "Адреналин"),
    "music": ("🎤", "Музыка"),
    "nightlife": ("🌙", "Ночная жизнь"),
    "outdoor": ("🌳", "На улице"),
    "nature": ("🌿", "Природа"),
    "walking": ("🚶", "Прогулка"),
}

CATEGORIES = {
    "restaurant": ("🍽", "Ресторан"),
    "cafe": ("☕", "Кафе"),
    "bar": ("🍸", "Бар"),
    "cinema": ("🎬", "Кино"),
    "bowling": ("🎳", "Боулинг"),
    "karaoke": ("🎤", "Караоке"),
    "board_game_club": ("♟", "Клуб настольных игр"),
    "escape_room": ("🔐", "Квест"),
    "museum": ("🏛", "Музей"),
    "gallery": ("🖼", "Галерея"),
    "karting": ("🏎", "Картинг"),
    "billiards": ("🎱", "Бильярд"),
    "arcade": ("🕹", "Игровой центр"),
    "park_activity": ("🌳", "Активности в парке"),
}

DISTRICTS = {
    "university": ("🎓", "Университет"),
    "downtown": ("🏙", "Центр"),
    "mall": ("🛍", "ТЦ"),
    "south": ("🏘", "Юг"),
    "park": ("🌳", "Парк"),
    "north": ("🏡", "Север"),
}

# уровни шума
NOISE = {
    "quiet": "тихо",
    "medium": "умеренно",
    "loud": "шумно",
}

# теги мест (те, что совпадают с интересами, берутся из INTERESTS)
TAGS = {
    "dinner": "ужин",
    "entertainment": "развлечения",
    "quest": "квесты",
    "racing": "гонки",
    "indoor": "в помещении",
    "outdoor": "на улице",
    "karaoke": "караоке",
    "karting": "картинг",
    "bowling": "боулинг",
    "billiards": "бильярд",
    "arcade": "аркады",
    "museum": "музей",
}

TRANSPORT = {
    "walk": ("🚶", "Пешком"),
    "car": ("🚗", "На машине"),
}


# ---------------------------------------------------------------- функции

def _name(catalog, code):
    item = catalog.get(code)
    if item is None:
        return str(code)
    return item[1] if isinstance(item, tuple) else item


def category_name(code):
    return _name(CATEGORIES, code)


def district_name(code):
    return _name(DISTRICTS, code)


def interest_name(code):
    return _name(INTERESTS, code)


def noise_name(code):
    return _name(NOISE, code)


def tag_name(code):
    if code in TAGS:
        return TAGS[code]
    return interest_name(code).lower()


def interest_names(codes):
    return ", ".join(interest_name(c) for c in (codes or []))


def category_names(codes):
    return ", ".join(category_name(c) for c in (codes or []))

from app.db import get_places
from app.core.filters import filter_places


def get_list_from_input(text):
    return [
        item.strip()
        for item in input(text).split(",")
        if item.strip()
    ]


def main():
    print("=== Поиск места ===\n")

    budget_max = int(
        input("Максимальный бюджет: ")
    )

    group_size = int(
        input("Количество человек: ")
    )

    required_interests = get_list_from_input(
        "Интересы через запятую: "
    )

    excluded_categories = get_list_from_input(
        "Запрещенные категории через запятую: "
    )

    indoor_input = input(
        "Только помещение? (да/нет/неважно): "
    ).lower()

    if indoor_input == "да":
        indoor = True
    elif indoor_input == "нет":
        indoor = False
    else:
        indoor = None

    food_input = input(
        "Нужна еда? (да/нет): "
    ).lower()

    food_required = food_input == "да"

    max_noise = input(
        "Максимальный уровень шума "
        "(quiet/medium/loud/неважно): "
    ).lower()

    if max_noise == "неважно":
        max_noise = None

    requirements = {
        "budget_max": budget_max,
        "group_size": group_size,
        "required_interests": required_interests,
        "excluded_categories": excluded_categories,
        "indoor": indoor,
        "food_required": food_required,
        "max_noise_level": max_noise,
    }

    print("\nПодключение к базе...")

    try:
        places = get_places()
    except Exception as error:
        print(f"\nОшибка подключения к базе:")
        print(error)
        return

    print(f"Получено мест из БД: {len(places)}")

    result = filter_places(
        places,
        requirements
    )

    print(f"Подходит мест: {len(result)}\n")

    if not result:
        print("Подходящих мест не найдено.")
        return

    for place in result:
        print(
            f"[{place['id']}] {place['name']}\n"
            f"  Категория: {place['category']}\n"
            f"  Район: {place['district']}\n"
            f"  Цена: {place['price_min']}–{place['price_max']}\n"
            f"  Рейтинг: {place['rating']}\n"
            f"  Интересы: {', '.join(place['interests'] or [])}\n"
        )


if __name__ == "__main__":
    main()
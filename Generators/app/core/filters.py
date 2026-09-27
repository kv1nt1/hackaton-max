def filter_places(places, requirements):
    result = []

    for place in places:

        # Бюджет
        if place["price_max"] > requirements["budget_max"]:
            continue

        # Размер группы
        if not (
            place["min_group_size"]
            <= requirements["group_size"]
            <= place["max_group_size"]
        ):
            continue

        # Интересы
        required_interests = set(
            requirements.get("required_interests", [])
        )

        place_interests = set(
            place["interests"] or []
        )

        if required_interests:
            if not required_interests.intersection(place_interests):
                continue

        # Запрещенные категории
        excluded_categories = set(
            requirements.get("excluded_categories", [])
        )

        if place["category"] in excluded_categories:
            continue

        # В помещении / на улице
        if requirements.get("indoor") is not None:
            if place["indoor"] != requirements["indoor"]:
                continue

        # Нужна еда
        if requirements.get("food_required", False):
            if not place["food_available"]:
                continue

        # Максимальный уровень шума
        max_noise = requirements.get("max_noise_level")

        if max_noise is not None:
            noise_levels = {
                "quiet": 0,
                "medium": 1,
                "loud": 2,
            }

            if noise_levels[place["noise_level"]] > noise_levels[max_noise]:
                continue

        result.append(place)

    return result

# ============================================================
# МЯГКАЯ ОЦЕНКА (для бота)
# ============================================================
#
# filter_places выше — строгий: любое нарушение = место отброшено.
# evaluate_place работает мягче: считает, какие пожелания место НЕ
# выполняет, и сколько это «стоит» (штраф). Так, если строгий отбор
# ничего не дал, можно показать места, которые подходят лучше всего.
#
# Жёсткие (не смягчаются никогда):
#   - размер компании не помещается в место;
#   - категория из списка «точно исключить»;
#   - цена выше бюджета более чем на BUDGET_TOLERANCE.
# Мягкие (штраф): бюджет в пределах допуска, интересы, помещение/улица,
# еда, шум. Время в пути смягчается в recommend.py.

BUDGET_TOLERANCE = 1.5      # до +50% к бюджету ещё показываем (с пометкой)

PENALTY_BUDGET = 3
PENALTY_INTERESTS = 2
PENALTY_FOOD = 2
PENALTY_INDOOR = 1
PENALTY_NOISE = 1

_NOISE_LEVELS = {"quiet": 0, "medium": 1, "loud": 2}


def evaluate_place(place, requirements):
    """
    Возвращает None, если место жёстко не подходит, иначе список
    нарушений [(код, штраф, текст)]. Пустой список = подходит полностью
    (ровно то же, что даёт filter_places).
    """
    # ---- жёсткие
    if not (
        place["min_group_size"]
        <= requirements["group_size"]
        <= place["max_group_size"]
    ):
        return None

    if place["category"] in set(requirements.get("excluded_categories", [])):
        return None

    violations = []

    # ---- бюджет (мягкий, но с потолком)
    budget = requirements["budget_max"]

    if place["price_max"] > budget:
        if place["price_max"] > budget * BUDGET_TOLERANCE:
            return None
        violations.append((
            "budget", PENALTY_BUDGET,
            f"дороже бюджета (до {place['price_max']} ₽)",
        ))

    # ---- интересы
    required = set(requirements.get("required_interests", []))
    if required and not required.intersection(set(place["interests"] or [])):
        violations.append(("interests", PENALTY_INTERESTS, "нет нужных интересов"))

    # ---- помещение / улица
    indoor = requirements.get("indoor")
    if indoor is not None and place["indoor"] != indoor:
        violations.append((
            "indoor", PENALTY_INDOOR,
            "на улице" if not place["indoor"] else "в помещении",
        ))

    # ---- еда
    if requirements.get("food_required", False) and not place["food_available"]:
        violations.append(("food", PENALTY_FOOD, "нет еды"))

    # ---- шум
    max_noise = requirements.get("max_noise_level")
    if max_noise is not None:
        over = _NOISE_LEVELS[place["noise_level"]] - _NOISE_LEVELS[max_noise]
        if over > 0:
            violations.append(("noise", PENALTY_NOISE * over, "шумнее, чем хотелось"))

    return violations

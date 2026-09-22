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
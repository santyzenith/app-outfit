import datetime as dt
import uuid

import pytest

from app.ai.openrouter import AIError
from app.ai.outfits import OutfitChoice
from app.models import Formality, Garment, GarmentCategory, GarmentStatus, Occasion, Warmth
from app.outfits import service
from app.outfits.candidates import MAX_PER_SLOT, select_candidates
from app.outfits.weather import Forecast
from tests.conftest import auth_header

TODAY = dt.date(2026, 10, 13)
HOT = Forecast(min_c=22, max_c=31, rain=False)
COLD = Forecast(min_c=6, max_c=12, rain=False)
MILD = Forecast(min_c=18, max_c=22, rain=False)


def garment(category, warmth=Warmth.MEDIUM, formality=Formality.CASUAL, worn_days_ago=None):
    worn_at = None
    if worn_days_ago is not None:
        worn_at = dt.datetime.combine(TODAY, dt.time(8), dt.UTC) - dt.timedelta(days=worn_days_ago)
    return Garment(
        id=uuid.uuid4(),
        status=GarmentStatus.READY,
        category=category,
        name=f"{category.value} {warmth.value}",
        color="azul",
        warmth=warmth,
        formality=formality,
        original_path="x.jpg",
        last_worn_at=worn_at,
    )


def test_hot_days_leave_out_warm_clothes():
    light = garment(GarmentCategory.TOP, Warmth.LIGHT)
    warm = garment(GarmentCategory.TOP, Warmth.WARM)

    candidates = select_candidates([light, warm], Occasion.CASUAL, HOT, TODAY)

    assert candidates.by_category[GarmentCategory.TOP] == [light]


def test_cold_days_leave_out_light_clothes_and_ask_for_a_layer():
    light = garment(GarmentCategory.BOTTOM, Warmth.LIGHT)
    warm = garment(GarmentCategory.BOTTOM, Warmth.WARM)

    candidates = select_candidates([light, warm], Occasion.CASUAL, COLD, TODAY)

    assert candidates.by_category[GarmentCategory.BOTTOM] == [warm]
    assert candidates.wants_outerwear is True


def test_mild_dry_days_do_not_ask_for_a_layer():
    assert select_candidates([], Occasion.CASUAL, MILD, TODAY).wants_outerwear is False


def test_rain_asks_for_a_layer_even_when_warm():
    rainy = Forecast(min_c=20, max_c=26, rain=True)

    assert select_candidates([], Occasion.CASUAL, rainy, TODAY).wants_outerwear is True


def test_recently_worn_tops_rest_but_shoes_do_not():
    worn_top = garment(GarmentCategory.TOP, worn_days_ago=1)
    rested_top = garment(GarmentCategory.TOP, worn_days_ago=4)
    worn_shoes = garment(GarmentCategory.SHOES, worn_days_ago=0)

    candidates = select_candidates([worn_top, rested_top, worn_shoes], Occasion.CASUAL, MILD, TODAY)

    assert candidates.by_category[GarmentCategory.TOP] == [rested_top]
    assert candidates.by_category[GarmentCategory.SHOES] == [worn_shoes]


def test_occasion_filters_by_formality():
    casual = garment(GarmentCategory.TOP, formality=Formality.CASUAL)
    formal = garment(GarmentCategory.TOP, formality=Formality.FORMAL)

    candidates = select_candidates([casual, formal], Occasion.WORK, MILD, TODAY)

    assert candidates.by_category[GarmentCategory.TOP] == [formal]


def test_a_small_closet_relaxes_formality_before_anything_else():
    only_casual = garment(GarmentCategory.TOP, formality=Formality.CASUAL)

    candidates = select_candidates([only_casual], Occasion.FORMAL, MILD, TODAY)

    assert candidates.by_category[GarmentCategory.TOP] == [only_casual]


def test_weather_is_the_last_rule_to_be_relaxed():
    worn_light = garment(GarmentCategory.TOP, Warmth.LIGHT, worn_days_ago=1)
    rested_warm = garment(GarmentCategory.TOP, Warmth.WARM)

    candidates = select_candidates([worn_light, rested_warm], Occasion.CASUAL, HOT, TODAY)

    assert candidates.by_category[GarmentCategory.TOP] == [worn_light]


def test_the_closet_rotates_least_recently_worn_first():
    old = garment(GarmentCategory.SHOES, worn_days_ago=30)
    recent = garment(GarmentCategory.SHOES, worn_days_ago=2)
    never = garment(GarmentCategory.SHOES)
    many = [garment(GarmentCategory.SHOES, worn_days_ago=5) for _ in range(MAX_PER_SLOT)]

    candidates = select_candidates([recent, old, never, *many], Occasion.CASUAL, MILD, TODAY)

    shoes = candidates.by_category[GarmentCategory.SHOES]
    assert shoes[:2] == [never, old]
    assert len(shoes) == MAX_PER_SLOT
    assert recent not in shoes


def test_missing_lists_what_an_outfit_still_needs():
    only_top = select_candidates([garment(GarmentCategory.TOP)], Occasion.CASUAL, None, TODAY)
    dress_and_shoes = select_candidates(
        [garment(GarmentCategory.ONE_PIECE), garment(GarmentCategory.SHOES)],
        Occasion.CASUAL,
        None,
        TODAY,
    )

    assert only_top.missing == [GarmentCategory.BOTTOM, GarmentCategory.SHOES]
    assert dress_and_shoes.missing == []


@pytest.fixture
def user(client) -> dict[str, str]:
    return auth_header(client.post("/v1/auth/guest").json())


@pytest.fixture
def closet(client, db, user):
    # Two tops, two bottoms and one pair of shoes: four possible outfits.
    user_id = uuid.UUID(client.get("/v1/me", headers=user).json()["id"])
    categories = [
        GarmentCategory.TOP,
        GarmentCategory.TOP,
        GarmentCategory.BOTTOM,
        GarmentCategory.BOTTOM,
        GarmentCategory.SHOES,
    ]
    garments = [garment(category) for category in categories]
    for item in garments:
        item.user_id = user_id
    db.add_all(garments)
    db.commit()
    return garments


@pytest.fixture
def stylist(monkeypatch):
    # Stands in for the model: proposes every top/bottom pair it has not shown yet.
    calls = []

    def suggest(candidates, occasion, forecast, seen, count):
        calls.append(seen)
        shoes = candidates.by_category[GarmentCategory.SHOES][0]
        choices = []
        for top in candidates.by_category[GarmentCategory.TOP]:
            for bottom in candidates.by_category[GarmentCategory.BOTTOM]:
                ids = dict.fromkeys(GarmentCategory)
                ids.update(
                    {
                        GarmentCategory.TOP: top.id,
                        GarmentCategory.BOTTOM: bottom.id,
                        GarmentCategory.SHOES: shoes.id,
                    }
                )
                if frozenset(i for i in ids.values() if i) not in seen:
                    choices.append(OutfitChoice(ids, "Combina bien para hoy."))
        return choices[:count]

    monkeypatch.setattr(service, "sugerir_outfits", suggest)
    monkeypatch.setattr("app.api.outfits.get_forecast", lambda lat, lon, day: MILD)
    return calls


def today(client, headers, occasion="casual", day=TODAY, **params):
    query = {"day": day.isoformat(), "occasion": occasion, **params}
    return client.get("/v1/outfits/today", params=query, headers=headers)


def test_today_returns_a_complete_outfit_with_the_forecast(client, user, closet, stylist):
    response = today(client, user, lat=-0.18, lon=-78.47)

    assert response.status_code == 200
    body = response.json()
    assert body["explanation"] == "Combina bien para hoy."
    assert body["worn"] is False
    assert body["forecast"] == {"min_c": 18.0, "max_c": 22.0, "rain": False}
    worn_slots = {slot for slot, item in body["garments"].items() if item}
    assert worn_slots == {"top", "bottom", "shoes"}


def test_today_is_generated_once_and_then_reused(client, user, closet, stylist):
    first = today(client, user).json()
    second = today(client, user).json()

    assert second["id"] == first["id"]
    assert len(stylist) == 1


def test_each_occasion_has_its_own_outfit(client, user, closet, stylist):
    casual = today(client, user, occasion="casual").json()
    work = today(client, user, occasion="work").json()

    assert casual["id"] != work["id"]
    assert work["occasion"] == "work"


def test_today_says_what_is_missing_when_the_closet_is_too_small(client, user, stylist):
    response = today(client, user)

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "not_enough_garments",
        "missing": ["top", "bottom", "shoes"],
    }


def test_today_still_works_when_the_model_is_down(client, user, closet, monkeypatch):
    def broken(*args):
        raise AIError("model is down")

    monkeypatch.setattr(service, "sugerir_outfits", broken)

    response = today(client, user)

    assert response.status_code == 200
    assert response.json()["explanation"] == service.FALLBACK_EXPLANATION


def test_unwearable_suggestions_from_the_model_are_ignored(client, user, closet, monkeypatch):
    top = closet[0]
    only_a_top = dict.fromkeys(GarmentCategory)
    only_a_top[GarmentCategory.TOP] = top.id
    bad_choice = OutfitChoice(only_a_top, "Solo una camiseta.")
    monkeypatch.setattr(service, "sugerir_outfits", lambda *args: [bad_choice])

    body = today(client, user).json()

    assert body["explanation"] == service.FALLBACK_EXPLANATION
    assert body["garments"]["shoes"] is not None


def test_another_walks_through_different_outfits_until_none_are_left(client, user, closet, stylist):
    current = today(client, user).json()
    seen = [current]

    for _ in range(3):
        current = client.post(f"/v1/outfits/{current['id']}/another", headers=user).json()
        seen.append(current)
    exhausted = client.post(f"/v1/outfits/{current['id']}/another", headers=user)

    combos = {(o["garments"]["top"]["id"], o["garments"]["bottom"]["id"]) for o in seen}
    assert len(combos) == 4
    assert exhausted.status_code == 409
    assert exhausted.json()["detail"] == {"code": "no_more_outfits"}
    # The last outfit stays on screen when there is nothing to replace it.
    assert today(client, user).json()["id"] == current["id"]


def test_wearing_an_outfit_rests_its_top_the_next_day(client, db, user, closet, stylist):
    outfit = today(client, user).json()

    worn = client.post(f"/v1/outfits/{outfit['id']}/wear", headers=user)

    assert worn.json()["worn"] is True
    assert today(client, user).json()["id"] == outfit["id"]
    worn_top = db.get(Garment, uuid.UUID(outfit["garments"]["top"]["id"]))
    worn_top.last_worn_at = dt.datetime.combine(TODAY, dt.time(8), dt.UTC)
    db.commit()
    tomorrow = today(client, user, day=TODAY + dt.timedelta(days=1)).json()
    assert tomorrow["garments"]["top"]["id"] != outfit["garments"]["top"]["id"]


def test_deleting_a_garment_replaces_the_outfit_that_used_it(client, user, closet, stylist):
    outfit = today(client, user).json()

    client.delete(f"/v1/garments/{outfit['garments']['top']['id']}", headers=user)

    replacement = today(client, user).json()
    assert replacement["id"] != outfit["id"]
    assert replacement["garments"]["top"] is not None


def test_outfits_are_private_to_their_owner(client, user, closet, stylist):
    outfit = today(client, user).json()
    stranger = auth_header(client.post("/v1/auth/guest").json())

    assert client.post(f"/v1/outfits/{outfit['id']}/wear", headers=stranger).status_code == 404
    assert client.post(f"/v1/outfits/{outfit['id']}/another", headers=stranger).status_code == 404


def test_history_lists_only_the_outfits_that_were_worn(client, user, closet, stylist):
    skipped = today(client, user).json()
    worn = client.post(f"/v1/outfits/{skipped['id']}/another", headers=user).json()
    client.post(f"/v1/outfits/{worn['id']}/wear", headers=user)
    stranger = auth_header(client.post("/v1/auth/guest").json())

    history = client.get("/v1/outfits/history", headers=user).json()

    assert [outfit["id"] for outfit in history] == [worn["id"]]
    assert history[0]["worn"] is True
    assert client.get("/v1/outfits/history", headers=stranger).json() == []

import datetime as dt
from dataclasses import dataclass

import httpx

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
RAIN_PROBABILITY_THRESHOLD = 50


@dataclass(frozen=True)
class Forecast:
    min_c: float
    max_c: float
    rain: bool


_cache: dict[tuple[float, float, dt.date], Forecast] = {}


def get_forecast(latitude: float, longitude: float, day: dt.date) -> Forecast | None:
    # Rounded coordinates keep the cache small: weather does not change within a few km.
    key = (round(latitude, 1), round(longitude, 1), day)
    if key in _cache:
        return _cache[key]

    try:
        response = httpx.get(
            FORECAST_URL,
            params={
                "latitude": key[0],
                "longitude": key[1],
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                "start_date": day.isoformat(),
                "end_date": day.isoformat(),
                "timezone": "auto",
            },
            timeout=5.0,
        )
        response.raise_for_status()
        daily = response.json()["daily"]
        forecast = Forecast(
            min_c=float(daily["temperature_2m_min"][0]),
            max_c=float(daily["temperature_2m_max"][0]),
            rain=(daily["precipitation_probability_max"][0] or 0) >= RAIN_PROBABILITY_THRESHOLD,
        )
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError):
        # Without weather the outfit is still suggested, just without that filter.
        return None

    _cache[key] = forecast
    return forecast

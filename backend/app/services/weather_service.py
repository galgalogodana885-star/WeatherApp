
import json
from typing import Any

import httpx


class WeatherAPIError(Exception):
    """Raised when the external weather API fails."""


class WeatherService:
    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def get_forecast(
        self,
        latitude: float,
        longitude: float,
    ) -> dict[str, Any]:

        # Validate geographic coordinates
        if not -90 <= latitude <= 90:
            raise ValueError("Latitude must be between -90 and 90.")

        if not -180 <= longitude <= 180:
            raise ValueError("Longitude must be between -180 and 180.")

        params = {
            "latitude": latitude,
            "longitude": longitude,

            "current": (
                "temperature_2m,"
                "relative_humidity_2m,"
                "apparent_temperature,"
                "is_day,"
                "precipitation,"
                "weather_code,"
                "wind_speed_10m,"
                "wind_direction_10m,"
                "wind_gusts_10m"
            ),

            "hourly": (
                "temperature_2m,"
                "relative_humidity_2m,"
                "precipitation_probability,"
                "weather_code,"
                "wind_speed_10m"
            ),

            "daily": (
                "weather_code,"
                "temperature_2m_max,"
                "temperature_2m_min,"
                "sunrise,"
                "sunset,"
                "precipitation_probability_max"
            ),

            "forecast_days": 7,
            "timezone": "auto",
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
        }

        try:
            response = await self.client.get(
                self.BASE_URL,
                params=params,
            )

            response.raise_for_status()

            data = response.json()

            # Validate response structure
            if not isinstance(data, dict):
                raise WeatherAPIError(
                    "Weather API returned an unexpected response."
                )

            # Check API-level errors
            if data.get("error"):
                raise WeatherAPIError(
                    data.get(
                        "reason",
                        "Weather API returned an error."
                    )
                )

            # Validate required forecast sections
            required_sections = ("current", "hourly", "daily")

            for section in required_sections:
                if not isinstance(data.get(section), dict):
                    raise WeatherAPIError(
                        f"Weather API response is missing "
                        f"or has an invalid {section} section."
                    )

            return data

        except httpx.TimeoutException as exc:
            raise WeatherAPIError(
                "Weather API request timed out."
            ) from exc

        except httpx.HTTPStatusError as exc:
            raise WeatherAPIError(
                f"Weather API returned HTTP "
                f"{exc.response.status_code}."
            ) from exc

        except httpx.RequestError as exc:
            raise WeatherAPIError(
                "Unable to connect to the weather provider."
            ) from exc

        except json.JSONDecodeError as exc:
            raise WeatherAPIError(
                "Weather API returned invalid JSON."
            ) from exc

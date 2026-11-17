
import json

import httpx
import pytest

from backend.app.services.weather_service import (
    WeatherService,
    WeatherAPIError,
)


# Sample successful API response
MOCK_WEATHER_DATA = {
    "timezone": "Africa/Addis_Ababa",

    "current": {
        "temperature_2m": 24.5,
        "relative_humidity_2m": 45,
        "apparent_temperature": 25.0,
        "is_day": 1,
        "precipitation": 0.0,
        "weather_code": 1,
        "wind_speed_10m": 12.0,
        "wind_direction_10m": 180,
        "wind_gusts_10m": 18.0,
    },

    "hourly": {
        "temperature_2m": [24.5, 25.0, 26.0],
        "relative_humidity_2m": [45, 43, 40],
        "precipitation_probability": [0, 10, 20],
        "weather_code": [1, 1, 2],
        "wind_speed_10m": [12, 13, 14],
    },

    "daily": {
        "weather_code": [1, 2, 3],
        "temperature_2m_max": [26, 27, 25],
        "temperature_2m_min": [15, 16, 14],
        "sunrise": ["06:00", "06:01", "06:02"],
        "sunset": ["18:00", "18:00", "17:59"],
        "precipitation_probability_max": [10, 20, 30],
    },
}


@pytest.fixture
def mock_client():
    """Create an HTTP client with a mocked API response."""

    def handler(request: httpx.Request):
        return httpx.Response(
            status_code=200,
            json=MOCK_WEATHER_DATA,
        )

    transport = httpx.MockTransport(handler)

    return httpx.AsyncClient(transport=transport)


# 1. Successful API request
@pytest.mark.asyncio
async def test_get_forecast_success(mock_client):
    async with mock_client as client:
        service = WeatherService(client)

        result = await service.get_forecast(
            latitude=9.03,
            longitude=38.74,
        )

        assert result["timezone"] == "Africa/Addis_Ababa"
        assert result["current"]["temperature_2m"] == 24.5
        assert "hourly" in result
        assert "daily" in result


# 2. Invalid latitude
@pytest.mark.asyncio
@pytest.mark.parametrize("latitude", [-91, 91])
async def test_invalid_latitude(mock_client, latitude):
    async with mock_client as client:
        service = WeatherService(client)

        with pytest.raises(ValueError):
            await service.get_forecast(
                latitude=latitude,
                longitude=38.74,
            )


# 3. Invalid longitude
@pytest.mark.asyncio
@pytest.mark.parametrize("longitude", [-181, 181])
async def test_invalid_longitude(mock_client, longitude):
    async with mock_client as client:
        service = WeatherService(client)

        with pytest.raises(ValueError):
            await service.get_forecast(
                latitude=9.03,
                longitude=longitude,
            )


# 4. API timeout
@pytest.mark.asyncio
async def test_api_timeout():
    def handler(request):
        raise httpx.ReadTimeout(
            "Request timed out",
            request=request,
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as client:
        service = WeatherService(client)

        with pytest.raises(
            WeatherAPIError,
            match="timed out",
        ):
            await service.get_forecast(9.03, 38.74)


# 5. Network connection failure
@pytest.mark.asyncio
async def test_connection_error():
    def handler(request):
        raise httpx.ConnectError(
            "Connection failed",
            request=request,
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as client:
        service = WeatherService(client)

        with pytest.raises(
            WeatherAPIError,
            match="Unable to connect",
        ):
            await service.get_forecast(9.03, 38.74)


# 6. HTTP error
@pytest.mark.asyncio
async def test_http_error():
    def handler(request):
        return httpx.Response(
            status_code=500,
            request=request,
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as client:
        service = WeatherService(client)

        with pytest.raises(
            WeatherAPIError,
            match="HTTP 500",
        ):
            await service.get_forecast(9.03, 38.74)


# 7. Invalid JSON response
@pytest.mark.asyncio
async def test_invalid_json():
    def handler(request):
        return httpx.Response(
            status_code=200,
            content=b"invalid json",
            headers={"Content-Type": "application/json"},
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as client:
        service = WeatherService(client)

        with pytest.raises(
            WeatherAPIError,
            match="invalid JSON",
        ):
            await service.get_forecast(9.03, 38.74)


# 8. Unexpected response structure
@pytest.mark.asyncio
async def test_unexpected_response_structure():
    def handler(request):
        return httpx.Response(
            status_code=200,
            json=["unexpected", "data"],
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as client:
        service = WeatherService(client)

        with pytest.raises(
            WeatherAPIError,
            match="unexpected response",
        ):
            await service.get_forecast(9.03, 38.74)


# 9. API-level error
@pytest.mark.asyncio
async def test_api_level_error():
    def handler(request):
        return httpx.Response(
            status_code=200,
            json={
                "error": True,
                "reason": "Invalid coordinates",
            },
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as client:
        service = WeatherService(client)

        with pytest.raises(
            WeatherAPIError,
            match="Invalid coordinates",
        ):
            await service.get_forecast(9.03, 38.74)


# 10. Missing required forecast section
@pytest.mark.asyncio
async def test_missing_forecast_section():
    def handler(request):
        return httpx.Response(
            status_code=200,
            json={
                "current": {},
                "hourly": {},
            },
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as client:
        service = WeatherService(client)

        with pytest.raises(
            WeatherAPIError,
            match="daily",
        ):
            await service.get_forecast(9.03, 38.74)

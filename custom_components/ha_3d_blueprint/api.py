"""API Client for the HA 3D Blueprint Add-on."""
import aiohttp
import logging
import asyncio

_LOGGER = logging.getLogger(__name__)

class ApiConnectionError(Exception):
    """Exception to indicate a connection error."""

class BlueprintApiClient:
    """API Client to handle communication with the Blueprint Engine."""

    def __init__(self, host: str, session: aiohttp.ClientSession):
        """Initialize the API client."""
        # The port is now configured in the add-on, so we assume the default here.
        port = 8124
        self._base_url = f"http://{host}:{port}"
        self._session = session

    async def configure_engine(self, config_data: dict) -> None:
        """Send configuration data to the blueprint engine."""
        await self._request("post", "configure", config_data)

    async def tag_location(self, payload: dict) -> None:
        """Send a location tag to the blueprint engine."""
        # This endpoint name must match the one in your engine.py
        await self._request("post", "tag_location", payload)

    async def _request(self, method: str, endpoint: str, data: dict | None = None) -> any:
        """Make a request to the API."""
        url = f"{self._base_url}/{endpoint}"
        try:
            async with self._session.request(
                method, url, json=data, timeout=10
            ) as response:
                response.raise_for_status()
                if response.status == 204:
                    return None
                if response.content_length and response.content_length > 0:
                    if response.content_type == "application/json":
                        return await response.json()
                    return await response.text()
                return None
        except Exception as exc:
            raise ApiConnectionError(f"Error communicating with the add-on: {exc}") from exc
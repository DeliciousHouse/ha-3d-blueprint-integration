"""API Client for the HA 3D Blueprint Add-on."""
import asyncio
import aiohttp
import logging

_LOGGER = logging.getLogger(__name__)

class ApiConnectionError(Exception):
    """Exception to indicate a connection error."""

class BlueprintApiClient:
    """API Client to handle communication with the Blueprint Engine."""

    def __init__(self, host: str, port: int, session: aiohttp.ClientSession):
        """Initialize the API client."""
        self._base_url = f"http://{host}:{port}"
        self._session = session

    async def configure_engine(self, config_data: dict) -> None:
        """Send configuration data to the blueprint engine."""
        await self._request("post", "configure", config_data)

    async def tag_location(self, payload: dict) -> None:
        """Send a location tag to the blueprint engine."""
        await self._request("post", "tag_location", payload)

    async def _request(self, method: str, endpoint: str, data: dict | None = None) -> any:
        """Make a request to the API."""
        url = f"{self._base_url}/{endpoint}"
        _LOGGER.debug("Sending %s request to %s with data: %s", method, url, data)

        try:
            async with self._session.request(
                method, url, json=data, timeout=10
            ) as response:
                response.raise_for_status()

                # Handle successful responses that have no content to read.
                if response.status == 204: # 204 No Content
                    return None

                # Only try to parse a body if one is expected
                if response.content_length and response.content_length > 0:
                    if response.content_type == "application/json":
                        return await response.json()
                    return await response.text()

                return None # Return None if there's no body

        except Exception as exc:
            # Catch any exception during the request and wrap it in our custom error
            _LOGGER.error(
                "An error occurred while communicating with the Blueprint Engine: %s", exc
            )
            raise ApiConnectionError(
                f"Error communicating with the add-on: {exc}"
            ) from exc
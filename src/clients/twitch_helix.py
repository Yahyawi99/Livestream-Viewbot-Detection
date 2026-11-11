import time
import requests

from src.config.settings import Settings


class TwitchHelixClient:

    def __init__(self):
        Settings.validate()

        self.client_id = Settings.TWITCH_CLIENT_ID
        self.client_secret = Settings.TWITCH_CLIENT_SECRET

        self.session = requests.Session()

        self.access_token = None
        self.token_expires_at = 0

    def authenticate(self):
        """Obtain an application access token."""

        response = self.session.post(
            Settings.TOKEN_URL,
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials"
            },
            timeout=15
        )

        response.raise_for_status()

        token_data = response.json()

        self.access_token = token_data["access_token"]

        # Refresh slightly before actual expiration.
        self.token_expires_at = (
            time.time() + token_data["expires_in"] - 60
        )

        print("Successfully authenticated with Twitch.")

    def _ensure_token(self):
        """Authenticate if no valid token is available."""

        if (
            self.access_token is None
            or time.time() >= self.token_expires_at
        ):
            self.authenticate()

    def _get_headers(self):
        self._ensure_token()

        return {
            "Client-Id": self.client_id,
            "Authorization": f"Bearer {self.access_token}"
        }

    def get_streams(
        self,
        first=100,
        after=None,
        **filters
    ):
        """
        Retrieve one page of currently live streams.

        Supported filters include:
        user_id, user_login, game_id, language, type.
        """

        if not 1 <= first <= 100:
            raise ValueError("first must be between 1 and 100")

        params = {
            "first": first,
            **filters
        }

        if after:
            params["after"] = after

        response = self.session.get(
            f"{Settings.API_BASE_URL}/streams",
            headers=self._get_headers(),
            params=params,
            timeout=30
        )

        # Retry once if Twitch rejects an expired token.
        if response.status_code == 401:
            self.access_token = None
            self.token_expires_at = 0

            response = self.session.get(
                f"{Settings.API_BASE_URL}/streams",
                headers=self._get_headers(),
                params=params,
                timeout=30
            )

        response.raise_for_status()

        return response.json()

    def get_all_streams(self, **filters):
        """
        Retrieve streams across pagination pages.

        Returns a list of stream objects.
        """

        streams = []
        cursor = None

        for _ in range(10):
            result = self.get_streams(
                first=100,
                after=cursor,
                **filters
            )

            streams.extend(result.get("data", []))

            cursor = result.get("pagination", {}).get("cursor")

            if not cursor:
                break


        return streams

    def close(self):
        self.session.close()
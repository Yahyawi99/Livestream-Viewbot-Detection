import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
    TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")

    TOKEN_URL = "https://id.twitch.tv/oauth2/token"
    API_BASE_URL = "https://api.twitch.tv/helix"

    @classmethod
    def validate(cls):
        if not cls.TWITCH_CLIENT_ID:
            raise ValueError("TWITCH_CLIENT_ID is missing")

        if not cls.TWITCH_CLIENT_SECRET:
            raise ValueError("TWITCH_CLIENT_SECRET is missing")
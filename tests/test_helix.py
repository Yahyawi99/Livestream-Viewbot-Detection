from src.clients.twitch_helix import TwitchHelixClient


def main():
    client = TwitchHelixClient()

    try:
        streams = client.get_streams(first=5)

        for stream in streams["data"]:
            print(
                f"Stream ID: {stream['id']}\n"
                f"Streamer: {stream['user_name']}\n"
                f"Game: {stream['game_name']}\n"
                f"Viewers: {stream['viewer_count']}\n"
                f"Started: {stream['started_at']}\n"
                f"{'-' * 40}"
            )

    finally:
        client.close()


if __name__ == "__main__":
    main()
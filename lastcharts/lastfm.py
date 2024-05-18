import os
import time

import pandas as pd
import requests
import requests_cache


class LastFM:
    """Class to retrieve data from the LastFM API"""

    URL_base = "http://ws.audioscrobbler.com/2.0/"
    DB_dir = os.path.join(os.path.dirname(__file__), "..", "db")

    def __init__(self, API_key, USER_AGENT) -> None:
        self.headers = {"user-agent": USER_AGENT}

        self.payload_base = {"api_key": API_key, "format": "json"}

        requests_cache.install_cache()  # Make local cache to limit reapeated API calls

    def lastfm_get(self, payload):
        payload = self.payload_base | payload

        try:
            response = requests.get(self.URL_base, headers=self.headers, params=payload)
            return response
        except Exception as e:
            raise e

    def get_recent_tracks(
        self, user: str = None, page: int = 1, limit: int = 200, start: int = 0
    ):
        """Get recent tracks for user

        Args:
            user    : LastFM username. If None, defaults to config
            page    : Page number (1 indexed). Default = 1
            limit   : Number of results per page. Default = 200 = Max
            start   : Beginning timestamp of range. Default = 0 (1970-01-01)
        """

        if user is None:
            user = self.headers["user-agent"]

        return self.lastfm_get(
            {
                "method": "user.getRecentTracks",
                "user": user,
                "page": page,
                "limit": limit,
                "from": start,
            }
        )

    def get_all_scrobbles(self, user: str = None, start: int = 0, sleep: float = 0.5):
        """Get all scrobbles, save to csv

        Args:
            user    : LastFM username. If None, defaults to config
            start   : Beginning timestamp of range. Default = 0 (1970-01-01)
            sleep   : Break between API calls. Default = 0.5 seconds
        """
        if user is None:
            user = self.headers["user-agent"]

        responses = []

        page = 1
        total_pages = 9999  # Placeholder until first loop

        while page <= total_pages:
            print(f"Requesting page {page}/{total_pages}")

            response = self.get_recent_tracks(
                user=user, page=page, limit=200, start=start
            )

            if response.status_code != 200:
                print(response.text)
                break

            if page == 1:  # Get actual number of pages after first call
                total_pages = int(
                    response.json()["recenttracks"]["@attr"]["totalPages"]
                )

            responses.append(response)

            # If response not from cache, sleep
            if not getattr(response, "from_cache", False):
                time.sleep(sleep)

            page += 1

        df = self.parse_responses(responses)

        if not os.path.exists(self.DB_dir):
            os.mkdir(self.DB_dir)

        df.to_csv(os.path.join(self.DB_dir, f"{user}.csv"), index=False)

        return responses

    def parse_responses(self, responses: list) -> pd.DataFrame:
        cols = ["artist", "album", "track", "datetime", "timestamp", "image"]
        dfs = []

        for response in responses:
            df_r = pd.DataFrame(columns=cols)
            r = response.json()["recenttracks"]["track"]
            df_r["artist"] = [row["artist"]["#text"] for row in r]
            df_r["album"] = [row["album"]["#text"] for row in r]
            df_r["track"] = [row["name"] for row in r]
            df_r["datetime"] = [row["date"]["#text"] for row in r]
            df_r["timestamp"] = [row["date"]["uts"] for row in r]
            df_r["image"] = [row["image"][-1]["#text"] for row in r]
            dfs.append(df_r)

        return pd.concat(dfs)

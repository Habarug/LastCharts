import os
import time
from datetime import timedelta

import pandas as pd
import requests


class LastFM:
    """Class to retrieve data from the LastFM API"""

    URL_base = "http://ws.audioscrobbler.com/2.0/"
    DB_dir = os.path.join(os.path.dirname(__file__), "..", "..", "db", "scrobbles")
    df_cols = ["artist", "album", "track", "datetime", "image"]
    album_cols = [
        "artist",
        "album",
        "tags",
        "listeners",
        "playcount",
        "tracks",
        "image",
        "mbid",
    ]

    def __init__(self, API_key, USER_AGENT) -> None:
        self.headers = {"user-agent": USER_AGENT}

        self.payload_base = {"api_key": API_key, "format": "json"}

    def get_album_info(self, artist: str, album: str):
        """Get info on a specific album, return Dataframe

        Args:
            artist  : Artist
            album   : Album

        Return:
            Dataframe with columns : artist (str), album (str), releasedata (datetime), image, listeners, playcount, toptag
        """

        response = self._lastfm_get(
            {"method": "album.getInfo", "artist": artist, "album": album}
        )

        return response

    def _parse_albuminfo(self, response):
        df = pd.DataFrame(columns=self.album_cols)

        r = response.json()["album"]
        df["artist"] = r["artist"]
        df["album"] = r["name"]
        # df["releasedate"] = pd.to_datetime(r["wiki"]["published"], format="%d %b %Y, %H:%M", utc=True)
        # df["tags"] = df["tags"].astype("object")
        # df.at[1, "tags"] = [[row["name"] for row in r["tags"]["tag"]]]
        df["listeners"] = r["listeners"]
        df["playcount"] = r["playcount"]
        df["tracks"] = r["tracks"]
        df["image"] = r["image"][-1]["#text"]
        df["mbid"] = r["mbid"]

        return df

    def _lastfm_get(self, payload):
        payload = self.payload_base | payload

        try:
            response = requests.get(self.URL_base, headers=self.headers, params=payload)
            return response
        except Exception as e:
            raise e

    def _get_recent_tracks(
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

        return self._lastfm_get(
            {
                "method": "user.getRecentTracks",
                "user": user,
                "page": page,
                "limit": limit,
                "from": start,
            }
        )

    def _get_all_scrobbles(self, user: str = None, start: int = 0, sleep: float = 0.5):
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
            if page > 1:
                print(f"Requesting page {page}/{total_pages}")

            response = self._get_recent_tracks(
                user=user, page=page, limit=200, start=start
            )

            if response.status_code != 200:
                print(response.text)
                break

            if page == 1:  # Get actual number of pages after first call
                total_pages = int(
                    response.json()["recenttracks"]["@attr"]["totalPages"]
                )
                if total_pages == 0:  # Return empty df if no new tracks
                    return pd.DataFrame(columns=self.df_cols)

            responses.append(response)

            # If response not from cache, sleep
            if not getattr(response, "from_cache", False):
                time.sleep(sleep)

            page += 1

        df = self._parse_responses(responses)

        return df

    def _parse_responses(self, responses: list) -> pd.DataFrame:
        dfs = []

        for response in responses:
            df_r = pd.DataFrame(columns=self.df_cols)
            r = response.json()["recenttracks"]["track"]
            df_r["artist"] = [row["artist"]["#text"] for row in r]
            df_r["album"] = [row["album"]["#text"] for row in r]
            df_r["track"] = [row["name"] for row in r]
            # "date" is not in response for currently playing tracks. Set to 1 min after previous afterwards
            df_r["datetime"] = [
                row["date"]["#text"] if "date" in row else None for row in r
            ]
            df_r["image"] = [row["image"][-1]["#text"] for row in r]
            dfs.append(df_r)

        df = pd.concat(dfs)

        if len(df) > 0:
            df["datetime"] = df["datetime"].apply(
                pd.to_datetime, format="%d %b %Y, %H:%M", utc=True
            )
            if df["datetime"].isna().any():  # Set datetime for currently playing tracks
                df.loc[0, "datetime"] = df["datetime"].iloc[1] + timedelta(minutes=3)

            # Dollar signs $ cause trouble with matplotlib, replace with s
            df["artist"] = df["artist"].str.replace("$", "s")
            df["album"] = df["album"].str.replace("$", "s")
            df["track"] = df["track"].str.replace("$", "s")

        return df

    def load_user(self, user: str = None):
        """Load a users data and return df"""

        if user is None:
            user = self.headers["user-agent"]

        if not os.path.exists(self.DB_dir):
            os.makedirs(self.DB_dir)

        print(f"Loading scrobbles for user: {user}")

        print("Checking local database:")
        path = os.path.join(self.DB_dir, f"{user.lower()}.csv")
        if os.path.exists(path):
            df = pd.read_csv(path, header=0)
            df["datetime"] = df["datetime"].apply(
                pd.to_datetime, format="ISO8601", utc=True
            )
            start = int(
                df["datetime"].iloc[0].timestamp() + 60
            )  # +1 was not working, maybe it needs even number
            print("Local database found")
        else:
            df = None
            start = 0

        print("Checking for new scrobbles:")
        # Load any potential new scrobbles, and update csv file if any are found
        df_new = self._get_all_scrobbles(user=user, start=start)
        print(f"{len(df_new)} new scrobbles found")
        if len(df_new) > 0:
            if df is not None:
                df = pd.concat([df_new, df])
            else:
                df = df_new

        df.drop_duplicates()
        df.to_csv(path, index=False)

        print("Scrobbles loaded")

        return df

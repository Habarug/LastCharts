import os
import urllib

import matplotlib.image as mpimg
import pandas as pd
import pyjson5

from .lastfm import LastFM


class LastCharts:
    """Python class to plot charts from LastFM data"""

    COVER_dir = os.path.join(os.path.dirname(__file__), "..", "db", "covers")

    def __init__(self, API_KEY, USER_AGENT):
        """Instiantiate LastCharts class

        Args:
            API_key : LastFM API key (personal)
        """

        # Instantiate LastFM class
        self.lastfm = LastFM(API_KEY, USER_AGENT)

        # Set self.df to None before
        self.df = None

    def load_scobbles(self, user: str = None):
        """Loads all scrobbes for user to self.df

        Args:
            user    : LastFM username. If None, defaults to config
        """
        self.df = self.lastfm.load_user(user)

        # Make some Series available for convenience
        self.topArtists = self.df["artist"].value_counts()[:].index.tolist()
        self.topAlbums = self.df["album"].value_counts()[:].index.tolist()
        self.topTracks = self.df["track"].value_counts()[:].index.tolist()

        # Make a list of all the dates in the range, including dates with no scrobbles
        self.dates = pd.date_range(
            self.df["datetime"].iloc[-1],
            self.df["datetime"].iloc[0],
            freq="d",
        )

    def _get_cover(self, artist, album, force=0):
        if not os.path.exists(self.COVER_dir):
            os.mkdir(self.COVER_dir)

        savePath = os.path.join(self.COVER_dir, f"{artist}_{album}.png")

        if not force:  # If no Force, check local folder first
            if os.path.exists(savePath):
                return mpimg.imread(savePath)

        # If not offline, go online
        url = (
            self.df[(self.df["artist"] == artist) & (self.df["album"] == album)][
                "image"
            ]
            .dropna()
            .iloc[0]
        )
        urllib.request.urlretrieve(url, savePath)
        return mpimg.imread(savePath)


def main():
    with open(
        os.path.join(os.path.dirname(__file__), "..", "config", "PRIVATE.json5")
    ) as f:
        priv = pyjson5.load(f)

    return LastCharts(priv["API_KEY"], priv["USER"])


if __name__ == "__main__":
    main()

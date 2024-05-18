import os

import pyjson5

from .lastfm import LastFM


class LastCharts:
    """Python class to plot charts from LastFM data"""

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


def main():
    with open(
        os.path.join(os.path.dirname(__file__), "..", "config", "PRIVATE.json5")
    ) as f:
        priv = pyjson5.load(f)

    return LastCharts(priv["API_KEY"], priv["USER"])


if __name__ == "__main__":
    main()

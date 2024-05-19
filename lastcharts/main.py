import os
import urllib

import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import pandas as pd
import pyjson5
from PIL import Image

from .lastfm import LastFM
from .utilities import valid_filename


class LastCharts:
    """Python class to plot charts from LastFM data"""

    COVER_dir = os.path.join(os.path.dirname(__file__), "..", "db", "covers")

    # Plotting parameters
    _FONT_SIZE_AXIS_LABELS = 20
    _FONT_SIZE_TITLE = 26
    _FONT_SIZE_TICKS = 14
    _FONT_SIZE_LEGEND = 18
    _FIG_SIZE = (15, 7)

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

    def plot_stacked_bar_plot(self, nArtists=15, artLimitCoefficient=0.02):
        """Plot stacked bar plot with album distribution of the users top artists

        Args:
            nArtists            : Number of artists to plot
            artLimitCoefficient : Minimum number of scrobbles to include covert art, as fraction of highest bar
        """

        plt.rcParams["figure.figsize"] = self._FIG_SIZE
        width = 0.9  # width of bars
        cover = 0.85  # max with of covers. Should not be larger than width above

        # Calculate how many plays an album must have to plot cover art
        artLimit = (
            artLimitCoefficient
            * self.df[self.df["artist"] == self.topArtists[0]].shape[0]
        )
        # Scale factor to set correct size of covers
        scale = (
            self.df[self.df["artist"] == self.topArtists[0]].shape[0]
            / nArtists
            * self._FIG_SIZE[0]
            / self._FIG_SIZE[1]
        )

        fig, ax = plt.subplots()

        for artist in self.topArtists[0:nArtists]:
            filterArtist = self.df[(self.df["artist"] == artist)]
            albums = filterArtist["album"].unique()

            albumsCount = []

            for album in albums:
                albumScrobbles = filterArtist[filterArtist["album"] == album]
                albumsCount.append(albumScrobbles.shape[0])

            # Invert order so most played albums are plotted first, i.e. at the bottom of stack
            albums = [y for x, y in sorted(zip(albumsCount, albums), reverse=True)]
            albumsCount = [x for x, y in sorted(zip(albumsCount, albums), reverse=True)]

            bottom = 0  # Start point for bar. 0 For first
            plt.gca().set_prop_cycle(None)

            for idx, count in enumerate(albumsCount):
                bp = plt.bar(artist, count, width, bottom=bottom)

                patch = bp.patches
                (x, y) = patch[0].get_xy()

                if count >= artLimit:
                    # Size is either max or the height of the bar
                    size = min(count * 0.95, cover * scale)
                    extent = [
                        x + width / 2 - size / (2 * scale),
                        x + width / 2 + size / (2 * scale),
                        bottom + count / 2 - size / 2,
                        bottom + count / 2 + size / 2,
                    ]
                    img = self._get_cover(artist, albums[idx])
                    ax.set_autoscale_on(False)
                    if img is not None:
                        plt.imshow(img, extent=extent, aspect="auto", zorder=3)

                bottom += count  # Set bottom of next bar to top of this one

            # Adjust plot formatting
            plt.xticks(rotation=45, fontsize=self._FONT_SIZE_TICKS)
            plt.yticks(fontsize=self._FONT_SIZE_TICKS)
            plt.ylabel("Scrobble count", fontsize=self._FONT_SIZE_AXIS_LABELS)
            plt.xlim(-0.5, nArtists - 1.5)
            plt.ylim(0, self.df[self.df["artist"] == self.topArtists[0]].shape[0])
            fig.patch.set_facecolor("xkcd:white")
            plt.tight_layout()

    def _get_cover(self, artist, album, force=0):
        if not os.path.exists(self.COVER_dir):
            os.mkdir(self.COVER_dir)

        filename_base = valid_filename(
            f"{artist}_{album}"
        )  # Removes any illegal characters
        savePath = os.path.join(self.COVER_dir, f"{filename_base}.png")

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

        fformat = url.split(".")[-1]
        if fformat != "png":  # jpgs must be converted to png
            DIR_jpg = os.path.join(self.COVER_dir, "jpgs")
            if not os.path.exists(DIR_jpg):
                os.mkdir(DIR_jpg)
            path = os.path.join(DIR_jpg, f"{filename_base}.{fformat}")
            urllib.request.urlretrieve(url, path)
            im = Image.open(path)
            im.save(savePath)
        else:
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

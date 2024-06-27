import math
import os
import urllib

import bar_chart_race as bcr
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import pandas as pd
import pyjson5
from cycler import cycler
from PIL import Image

from . import utils
from .lastfm import LastFM


class LastCharts:
    """Python class to plot charts from LastFM data"""

    COVER_dir = os.path.join(os.path.dirname(__file__), "..", "db", "covers")
    OUTPUT_dir = os.path.join(os.path.dirname(__file__), "..", "output")

    # Plotting parameters
    _FONT_SIZE_AXIS_LABELS = 16
    _FONT_SIZE_TITLE = 26
    _FONT_SIZE_TICKS = 14
    _FONT_SIZE_LEGEND = 18
    _FIG_SIZE_STACKEDBARS = (15, 7)
    _FIG_SIZE_BCR = (6, 3.5)
    _FONT = "Comfortaa"
    _CMAP = "Set2"

    def __init__(self, API_KEY, USER_AGENT):
        """Instiantiate LastCharts class

        Args:
            API_key : LastFM API key (personal)
        """
        # Check inputs
        if not utils.check_API_key(API_KEY):
            raise ValueError("Provided API_KEY not valid")
        if not utils.check_username(USER_AGENT):
            raise ValueError("Provided USER_AGENT not valid")

        # Instantiate LastFM class
        self.lastfm = LastFM(API_KEY, USER_AGENT)

        # Set self.df to None before
        self.df = None

        # Configure matplotlib for stacked bar plot
        plt.rcParams["figure.figsize"] = self._FIG_SIZE_STACKEDBARS
        plt.rcParams["font.family"] = self._FONT
        plt.rcParams["axes.prop_cycle"] = cycler(color=plt.get_cmap(self._CMAP).colors)

    def load_scrobbles(self, user: str = None):
        """Loads all scrobbes for user to self.df

        Args:
            user    : LastFM username. If None, defaults to config
        """
        if user is None:
            user = self.lastfm.headers["user-agent"]
        self.df = self.lastfm.load_user(user)
        self.user = user

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

    def filter_df(self, df: pd.DataFrame, startDate: str = None, endDate: str = None):
        """Filter dataframe to only include dates between startdate and endate

        Args:
            df          : Pandas dataframe with scrobble data
            startDate   : Optional start date for plot, format ISO 8601 (YYYY-MM-DD)
            endDate     : Optional end date for plot, format ISO 8601 (YYYY-MM-DD)
        """

        # Every timestamp is localized to UTC, because pandas to_datetime returns timezone-aware series
        if startDate is None:
            startDate = pd.Timestamp.min.tz_localize("UTC")
        else:
            startDate = pd.Timestamp(startDate, tz="UTC")

        if endDate is None:
            endDate = pd.Timestamp.max.tz_localize("UTC")
        else:
            endDate = pd.Timestamp(endDate, tz="UTC")

        if startDate >= endDate:
            raise ValueError("endDate must be after startDate")

        return self.df[
            (self.df["datetime"] >= startDate) & (self.df["datetime"] <= endDate)
        ].sort_values("datetime", ascending=False)

    def stacked_bar_plot(
        self,
        startDate: str = None,
        endDate: str = None,
        nArtists: int = 15,
        artLimitCoefficient: float = 0.02,
    ):
        """Plot stacked bar plot with album distribution of the users top artists

        Args:
            startDate           : Optional start date for plot, format ISO 8601 (YYYY-MM-DD)
            endDate             : Optional end date for plot, format ISO 8601 (YYYY-MM-DD)
            nArtists            : Number of artists to plot
            artLimitCoefficient : Minimum number of scrobbles to include covert art, as fraction of highest bar
        """

        width = 0.9  # width of bars
        cover = 0.85  # max with of covers. Should not be larger than width above

        # Optional filtering of dataframe to only include scrobbles from specific time period
        df = self.filter_df(self.df, startDate, endDate)
        topArtists = df["artist"].value_counts()[:].index.tolist()

        # Calculate how many plays an album must have to plot cover art
        artLimit = artLimitCoefficient * df[df["artist"] == topArtists[0]].shape[0]
        # Scale factor to set correct size of covers
        scale = (
            df[df["artist"] == topArtists[0]].shape[0]
            / nArtists
            * self._FIG_SIZE_STACKEDBARS[0]
            / self._FIG_SIZE_STACKEDBARS[1]
        )

        fig, ax = plt.subplots()

        for artist in topArtists[0:nArtists]:
            filterArtist = df[(df["artist"] == artist)]
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
        plt.ylim(0, df[df["artist"] == topArtists[0]].shape[0])
        fig.patch.set_facecolor("xkcd:white")
        plt.tight_layout()

        if not os.path.exists(self.OUTPUT_dir):
            os.mkdir(self.OUTPUT_dir)
        plt.savefig(
            os.path.join(self.OUTPUT_dir, f"{self.user}_topArtists_stackedbars.jpg"),
            dpi=600,
        )
        return fig

    def bar_chart_race(
        self,
        column: str = "artist",
        startDate: str = None,
        endDate: str = None,
        length: int = 10,
        f_periods: int = 20,
        format: str = "gif",
        skip_empty_dates: bool = False,
        **bcr_options,
    ):
        """Create a bar chart race for the given column

        Args:
            column          : Column to use ("artist", "album" or "track")
            startDate       : Optional start date for plot, format ISO 8601 (YYYY-MM-DD)
            endDate         : Optional end date for plot, format ISO 8601 (YYYY-MM-DD)
            length          : Length of video in seconds
            f_periods       : Number of dates to plot per second. Is used to filter dates and improve performance
            format          : Data format to save to [mp4, gif, ...]
            skip_empty_dates: Set to true to skip empty dates

            **bcr_options   : Custom arguments for bar_chart_race as dict. Some of these will overwrite length. Notable:
                steps_per_period : Steps to go from one period to the next. Higher = smoother, but increases time and memory use. Default = 2
        """
        # Check inputs
        if column not in ["artist", "album", "track"]:
            raise ValueError(f"Requested column {column} not artist, album or track")

        if not os.path.exists(self.OUTPUT_dir):
            os.mkdir(self.OUTPUT_dir)

        filename = f"{self.user}_BCR_{column}.{format}"

        df = self.filter_df(self.df, startDate, endDate)

        # Potentially skip dates with no scrobbles
        if skip_empty_dates:
            dates = pd.to_datetime(df["datetime"].dt.date.unique(), utc=True)[
                ::-1
            ]  # Reverse order
        else:
            dates = pd.date_range(
                df["datetime"].iloc[-1],
                df["datetime"].iloc[0],
                freq="d",
            )

        # Filter the dates, running with thousands of periods is extremely slow and memory instensive
        # Default: 2 periods per second (f_period = 2)
        # Make sure to get last date included, first not that important
        # Create it backwards and reverse it afterwards, makes sure we include last date
        if len(dates) > (length * f_periods):
            step = math.floor(len(dates) / (length * f_periods))  # index step

            # Only perform date filtering if it is significant enough, otherwise might as well include every data point
            if step >= 5:
                dates_tmp = []
                for idx in range(length * f_periods):
                    dates_tmp.append(dates[-1 - idx * step])

                dates_tmp.reverse()
                dates = dates_tmp

        # Make a new df with correct formatting for bcr:
        df_bcr = self._format_df_for_bcr(df, column, dates, n=200)

        bcr_arguments = {  # Default iptions for bar chart race
            "df": df_bcr,
            "filename": os.path.join(self.OUTPUT_dir, filename),
            "n_bars": 10,
            "steps_per_period": 2,
            "period_length": int(
                length / len(dates) * 1000
            ),  # period length is in miliseconds
            "filter_column_colors": True,
            "colors": self._CMAP,
            "period_template": "%Y-%m-%d",
            "title": f"{self.user} - Top {column}s",
            "shared_fontdict": {"family": self._FONT, "weight": "bold"},
            "fig_kwargs": {"dpi": 100},
        }
        bcr_arguments.update(**bcr_options)  # Add or replace defaults with user options

        bcr.bar_chart_race(**bcr_arguments)

    def _format_df_for_bcr(
        self, df: pd.DataFrame, column: str, dates: list, n: int = None
    ):
        """Returns a df formatted for bar chart race

        Args:
            df      : Dataframe with scrobbles with at least the column specified below
            column  : Column to count (artist, album, track)
            dates   : List of dates to use
            n       : Number of output columns. Setting it low may mean cause some inaccuracies early in the bcr.
        """
        max_label_length = 17

        topList = df[column].value_counts()[:].index.tolist()
        df_bcr = pd.DataFrame(
            index=dates,
            columns=[
                entry[0:max_label_length] for entry in topList[:n]
            ],  # Set max length to 18 for now to avoid label cutoff
        )

        if n is None or n > len(topList):
            n = len(topList)
        for entry in topList[:n]:
            df_filtered = df[df[column] == entry]
            cumSum = []
            for date in dates:
                cumSum.append(sum(df_filtered["datetime"] <= date))
            df_bcr[entry[0:max_label_length]] = cumSum

        return df_bcr

    def _get_cover(self, artist, album, force=0):
        """Finds the cover for an album, saves it to db/covers as png"""

        if not os.path.exists(self.COVER_dir):
            os.makedirs(self.COVER_dir)

        filename_base = utils.valid_filename(
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
        os.path.join(os.path.dirname(__file__), "..", "config", "config.json5")
    ) as f:
        priv = pyjson5.load(f)

    return LastCharts(priv["API_KEY"], priv["USER"])


if __name__ == "__main__":
    main()

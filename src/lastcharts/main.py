import math
import os
import urllib
from datetime import timedelta

import bar_chart_race as bcr
import matplotlib.font_manager as font_manager
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import pandas as pd
import pyjson5
from colorthief import ColorThief
from cycler import cycler
from PIL import Image
from thefuzz import process

from . import utils
from .lastfm import LastFM


class LastCharts:
    """Python class to plot charts from LastFM data"""

    COVER_dir = os.path.join(os.path.dirname(__file__), "..", "..", "db", "covers")
    OUTPUT_dir = os.path.join(os.path.dirname(__file__), "..", "..", "output")

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
        if self._FONT in font_manager.fontManager.get_font_names():
            plt.rcParams["font.family"] = self._FONT
        else:
            print(f"Font {self._FONT} not installed, using default font.")
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
            # Add a single day so that filtering includes the given end date
            endDate = pd.Timestamp(endDate, tz="UTC") + timedelta(days=1)

        if startDate >= endDate:
            raise ValueError("endDate must be after startDate")

        return self.df[
            (self.df["datetime"] >= startDate) & (self.df["datetime"] < endDate)
        ].sort_values("datetime", ascending=False)

    def get_scrobbles_for(
        self,
        query: str,
        column: str = "artist",
        startDate: str = None,
        endDate: str = None,
    ):
        """Prints the number of scrobbles for the given query

        Args:
            query       : Artist/album/track to get the number of scrobbles for
            column      : artist/album/track (default: artist)
            startDate   : Optional start date
            endDate     : Optional end date
        """

        if column not in ["artist", "album", "track"]:
            raise ValueError("Column input has to be artist, album or track.")

        # Optional filtering of scrobbles
        df = self.filter_df(self.df, startDate, endDate)

        querymatch = process.extractOne(query, set(self.df[column]))
        if querymatch[1] < 80:
            print(f"No good match found for {query}, did you mean: {querymatch[0]}?")
            return
        else:
            query = querymatch[0]

        nScrobbles = sum(df[column] == query)

        print(f"Number of scrobbles for {query}: {nScrobbles}")
        return nScrobbles

    def plot_top(
        self,
        column: str = "artist",
        nBars: int = 15,
        startDate: str = None,
        endDate: str = None,
    ):
        """Plot top artist/album/track either all time or for a given time period

        Args:
            column      : artist/album/track (default: artist)
            nBars       : number of bars to plot
            startDate   : Optional start date
            endDate     : Optional end date
        """
        if column not in ["artist", "album", "track"]:
            raise ValueError("Column input has to be artist, album or track.")

        df = self.filter_df(self.df, startDate, endDate)

        topList = df[column].value_counts()[:nBars].index.tolist()

        fig, ax = plt.subplots()

        yMax = 0
        scale = (
            df[df[column] == topList[0]].shape[0]
            / nBars
            * self._FIG_SIZE_STACKEDBARS[0]
            / self._FIG_SIZE_STACKEDBARS[1]
        )
        width = 0.9
        cover = 0.82

        for idm, match in enumerate(topList):
            df_filtered = df[df[column] == match]
            nScrobbles = len(df_filtered)
            yMax = nScrobbles if nScrobbles > yMax else yMax
            bp = ax.bar(match, nScrobbles, width)

            mostCommon = df_filtered[["artist", "album", "track"]].mode()
            img, rgb = self._get_cover(
                mostCommon["artist"].iloc[0], mostCommon["album"].iloc[0]
            )
            if img is not None:
                patch = bp.patches
                (x, y) = patch[0].get_xy()
                size = min(nScrobbles * 0.95, cover * scale)
                extent = [
                    x + width / 2 - size / (2 * scale),
                    x + width / 2 + size / (2 * scale),
                    nScrobbles / 2 - size / 2,
                    nScrobbles / 2 + size / 2,
                ]

                ax.imshow(img, extent=extent, aspect="auto", zorder=3)
                bp[0].set_facecolor(rgb)
                bp[0].set_edgecolor(
                    [1 - c for c in rgb]
                )  # dark border for white and opposite

        xlabels = utils.shorten_strings(
            [label.get_text() for label in ax.get_xticklabels()]
        )
        ax.xaxis.set_ticklabels(xlabels)
        plt.xticks(rotation=45, fontsize=self._FONT_SIZE_TICKS)
        plt.yticks(fontsize=self._FONT_SIZE_TICKS)
        plt.ylabel("Scrobble count", fontsize=self._FONT_SIZE_AXIS_LABELS)
        plt.xlim(-0.5, nBars - 0.5)
        plt.ylim(0, yMax)
        fig.patch.set_facecolor("xkcd:white")
        plt.tight_layout()

        return fig, ax

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
        cover = 0.82  # max with of covers. Should not be larger than width above

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
                    img, rgb = self._get_cover(artist, albums[idx])
                    ax.set_autoscale_on(False)
                    if img is not None:
                        plt.imshow(img, extent=extent, aspect="auto", zorder=3)
                    bp[0].set_facecolor(rgb)
                    bp[0].set_edgecolor(
                        [1 - c for c in rgb]
                    )  # dark border for white and opposite

                bottom += count  # Set bottom of next bar to top of this one

        # Adjust plot formatting
        xlabels = utils.shorten_strings(
            [label.get_text() for label in ax.get_xticklabels()]
        )
        ax.xaxis.set_ticklabels(xlabels)
        plt.xticks(rotation=45, fontsize=self._FONT_SIZE_TICKS)
        plt.yticks(fontsize=self._FONT_SIZE_TICKS)
        plt.ylabel("Scrobble count", fontsize=self._FONT_SIZE_AXIS_LABELS)
        plt.xlim(-0.5, nArtists - 0.5)
        plt.ylim(0, df[df["artist"] == topArtists[0]].shape[0])
        plt.title(
            f"Top artists for {self.user}, {self._format_timeperiod(df)}",
            fontsize=self._FONT_SIZE_AXIS_LABELS,
        )
        fig.patch.set_facecolor("xkcd:white")
        plt.tight_layout()

        if not os.path.exists(self.OUTPUT_dir):
            os.mkdir(self.OUTPUT_dir)
        plt.savefig(
            os.path.join(self.OUTPUT_dir, f"{self.user}_topArtists_stackedbars.jpg"),
            dpi=600,
        )
        return fig, ax

    def bar_chart_race(
        self,
        column: str = "artist",
        startDate: str = None,
        endDate: str = None,
        length: int = 10,
        f_periods: int = 15,
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
            "steps_per_period": 4,
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

    def _get_cover(self, artist: str, album: str = None, force=0):
        """Finds the cover for an album, saves it to db/covers as png. Returns image and dominant color as rgb."""

        if not os.path.exists(self.COVER_dir):
            os.makedirs(self.COVER_dir)

        # If album not provided, use most played album
        if not album:
            album = self.df[self.df["artist"] == artist].album.mode().iloc[0]

        filename_base = utils.valid_filename(
            f"{artist}_{album}"
        )  # Removes any illegal characters
        savePath = os.path.join(self.COVER_dir, f"{filename_base}.png")

        if not force:  # If no Force, check local folder first
            if os.path.exists(savePath):
                ct = ColorThief(savePath)
                rgb = [c / 256 for c in ct.get_color()]
                return mpimg.imread(savePath), rgb

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
            try:
                urllib.request.urlretrieve(url, path)
            except Exception:
                return [[0.5, 0.5], [0.5, 0.5]], [0.5, 0.5, 0.5]
            im = Image.open(path)
            im.save(savePath)
        else:
            try:
                urllib.request.urlretrieve(url, savePath)
            except Exception:
                return [[0.5, 0.5], [0.5, 0.5]], [0.5, 0.5, 0.5]
        ct = ColorThief(savePath)
        rgb = [c / 256 for c in ct.get_color()]
        return mpimg.imread(savePath), rgb

    def _format_timeperiod(self, df) -> str:
        """Returns a string describing the time period used in plots

        Args:
            df: Dataframe used for plotting
        """
        return f"{df["datetime"].iloc[-1].strftime("%Y-%m-%d")} - {df["datetime"].iloc[0].strftime("%Y-%m-%d")}"


def main():
    with open(
        os.path.join(os.path.dirname(__file__), "..", "..", "config", "config.json5")
    ) as f:
        priv = pyjson5.load(f)

    return LastCharts(priv["API_KEY"], priv["USER"])


if __name__ == "__main__":
    main()

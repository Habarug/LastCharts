## LastCharts

Python package to plot charts from a user's LastFM data. LastCharts downloads a users entire listing history using the [LastFM Rest API](https://www.last.fm/api/rest), and includes methods to create pre-defined charts. 

### Implemented charts:
- Bar chart race:

![bcr](./figures/Example_BCR_artist.gif)

- Stacked bar plot of top artists with album distribution:

![bcr](./figures/Example_topArtists_stackedbars.jpg)

## Pre-requisites

- [Python](https://www.python.org/). not sure what is minimum version required. I have used 3.12. 
- To generate bar chart races you need at least one of:
    - [FFmpeg](https://ffmpeg.org/) for exporting video formats like mp4
    - [ImageMagick](https://imagemagick.org/index.php) for exporting gifs
- A [LastFM API account](https://www.last.fm/api/account/create), it is very easy to setup. See your existing LastFM API accounts [here](https://www.last.fm/api/accounts).

## Get started

### Clone the repo

```
https://github.com/Habarug/LastCharts.git
cd LastCharts
```

### Install requirements
```
pip install -r requirements.txt
```

### Import package and instantiate LastCharts
In Jupyter/python shell:
```python
import lastcharts

lc = lastcharts.LastCharts(YOUR API KEY, YOUR USERNAME)
```

### Load scrobbles for a user

```python
lc.load_scrobbles(user = ENTER USERNAME)
```
- If no username is provided it will use your username. 
- Go grab a snack. The first time you run this for a user it may run for a very long time, depending on how long the users history is. You can only load 200 scrobbles at a time from LastFM, and the API is heavily rate limited. The next time you run this command only new scrobbles will be downloaded, and it will be much faster. 

### Plot stacked bar plot

Once the scrobbles are loaded you can start plotting. The first time you plot a stacked bar plot album covers are downloaded to your computer, so it may take a little while to run the first time. 
```python
lc.stacked_bar_plot(
    nArtists = 15,              # Change how many artists are included
    artLimitCoefficient = 0.05  # Cofficient to determine which albums will include cover art. 
                                # 0.05 => only albums with at least 5% of the highest bar will get a cover art
)
```

### Plot bar chart race

This is very cool, but quite slow and memory intensive, so you may have to tweak the parameters a bit to get the results you want. The dates are filtered before plotting if the history is long, as it otherwise made me run out of memory. Adjust length, f_period and **{steps_per_period} to find your ideal tradeoff between length, smoothness and performance. For more information on ```**bcr_options``` check the [bar_chart_race documentation](https://github.com/dexplo/bar_chart_race).

```python
lc.bar_chart_race(
    column              = "artist", # Can select artist, album or track
    length              = 10,       # Length of the resulting video in seconds
    f_period            = 20,       # Number of dates to plot per second
    format              = "gif",    # Format to save, gif, mp4,...
    skip_empty_dates    = False,    # Option to skip dates with no scrobbles           
    **{"steps_per_period" : 2,      # Number of frames per period
    "fig_kwargs": {                 # kwargs for fig
        "dpi": 100},                # dpi of images
    }  # Custom arguments for the bar_chart_race. More available
)
```

## Plans

- Fix formatting of longer artist/album names
- Consider changing default font from Comfortaa to something that is always installed, at least make it easier to change at run time
- Consider adding a way to estimate how long it will take to generate bar chart race based on length, f_period, steps_per_period and dpi. Can save a number to use for estimates to config/config.json5
- Implement time filtering, so the user can for example only plot this year
- Maybe add cover art to bar chart race labels
- Maybe add more charts if I get any good ideas
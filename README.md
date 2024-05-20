## LastCharts

Python package to plot charts from a user's LastFM data. LastCharts downloads a users entire listing history using the [LastFM Rest API](https://www.last.fm/api/rest)

### Implemented chars:
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
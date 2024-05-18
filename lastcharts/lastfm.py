import requests


class LastFM:
    """Class to retrieve data from the LastFM API"""

    URL_base = "http://ws.audioscrobbler.com/2.0/"

    def __init__(self, API_key, USER_AGENT) -> None:
        self.headers = {"user-agent": USER_AGENT}

        self.payload_base = {"api_key": API_key, "format": "json"}

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

import requests


class LastFM:
    """Class to retrieve data from the LastFM API"""

    URL_base = "http://ws.audioscrobbler.com/2.0/"

    def __init__(self, API_key, USER_AGENT) -> None:
        self.headers = {"user-agent": USER_AGENT}

        self.payload_base = {"api_key": API_key, "format": "json"}

    def lastfm_get(self, method):
        payload = self.payload_base | {"method": method}

        try:
            response = requests.get(self.URL_base, headers=self.headers, params=payload)
            return response
        except Exception as e:
            raise e

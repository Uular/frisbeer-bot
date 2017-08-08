import requests

# api_url = "https://ranta.org/frisbeer/API/"
# api_url = "http://localhost:8000/API/"
api_url = "https://t3mu.kapsi.fi/frisbeer/API/"
players = "players/"
games = "games/"


class APIError(Exception):
    pass


class API:
    _default_headers = {
        # 'content-type': 'application/json',
    }

    @staticmethod
    def login(username, password):
        payload = {
            "username": username,
            "password": password
        }
        pl = API._post("token-auth/", payload)
        API._default_headers["Authorization"] = "Token " + pl["token"]

    @staticmethod
    def _get(endpoint, instance_id=None):
        url = api_url + endpoint
        if instance_id:
            url += instance_id
        response = requests.get(url, headers=API._default_headers)
        if not response.ok:
            raise APIError("Error in response. Status {}, message {}", response.status_code, response.content)
        try:
            return response.json()
        except ValueError as e:
            raise APIError(e)

    @staticmethod
    def _post(endpoint, payload):
        url = api_url + endpoint
        response = requests.post(url, headers=API._default_headers, data=payload)
        if not response.ok:
            raise APIError("Error in response. Status {}, message {}", response.status_code, response.content)
        try:
            return response.json()
        except ValueError as e:
            raise APIError(e)

    @staticmethod
    def get_players():
        return API._get(players)

    @staticmethod
    def create_game(name, date):
        payload = {
            "name": name,
            "date": date.isoformat()
        }
        return API._post(games, payload)

    @staticmethod
    def get_games():
        return API._get(games)

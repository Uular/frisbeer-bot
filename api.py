import requests

# api_url = "https://ranta.org/frisbeer/API/"
# api_url = "http://localhost:8000/API/"

api_url = "https://t3mu.kapsi.fi/frisbeer/API/"
players = "players/"
games = "games/"
locations = "locations/"


class APIError(Exception):
    pass


class API:
    _default_headers = {
        'content-type': 'application/json'
    }

    @staticmethod
    def login(username, password):
        payload = {
            "username": username,
            "password": password
        }
        pl = API._post("token-auth/", payload=payload)
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
    def _post(endpoint, id_: int = None, payload=None):
        url = api_url + endpoint
        if id_:
            url += str(id_)
        response = requests.post(url, headers=API._default_headers, json=payload)
        if not response.ok:
            raise APIError("Error in response. Status {}, message {}", response.status_code, response.content)
        try:
            return response.json()
        except ValueError as e:
            raise APIError(e)

    @staticmethod
    def _delete(endpoint: str, id_: int):
        return requests.delete(api_url + endpoint + str(id_) + "/", headers=API._default_headers)

    @staticmethod
    def _patch(endpoint: str, id_: int = None, payload=None):
        url = api_url + endpoint
        if id_:
            url += str(id_) + "/"
        response = requests.patch(url, headers=API._default_headers, json=payload)
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
    def create_game(name: str, date, location: int):
        payload = {
            "name": name,
            "date": date.isoformat(),
            "location": location,
        }
        return API._post(games, payload=payload)

    @staticmethod
    def delete_game(id_: int):
        API._delete(games, id_)

    @staticmethod
    def join_game(game_id, player_id):
        return API._post(games + str(game_id) + "/add_player/", payload={"id": player_id})

    @staticmethod
    def leave_game(game_id, player_id):
        return API._post(games + str(game_id) + "/remove_player/", payload={"id": player_id})

    @staticmethod
    def create_teams(game_id):
        return API._post(games + str(game_id) + "/create_teams/")

    @staticmethod
    def get_games():
        return API._get(games)

    @staticmethod
    def get_locations():
        return API._get(locations)

    @staticmethod
    def create_location(name: str, longitude: float, latitude: float) -> dict:
        return API._post(locations, payload={"name": name, "longitude": longitude, "latitude": latitude})

    @staticmethod
    def submit_score(id_, team1_score, team2_score):
        return API._patch(games, id_=id_, payload={"team1_score": team1_score, "team2_score": team2_score, "state": 2})

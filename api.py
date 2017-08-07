import requests

# api_url = "https://ranta.org/frisbeer/API/"
# api_url = "http://localhost:8000/API/"
api_url = "https://t3mu.kapsi.fi/frisbeer/API/"
players = "players/"
games = "games/"
content_type = {'content-type': 'application/json'}


class APIError(Exception):
    pass


class API:
    @staticmethod
    def _get(endpoint, instance_id=None):
        url = api_url + endpoint
        if instance_id:
            url += instance_id
        response = requests.get(url, headers=content_type)
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
    def create_game(name="asd"):
        payload = {
            "name": name,
        }
        response = requests.post(api_url + games, headers=content_type, data=payload)
        if not response.ok:
            raise APIError("Error in response")
        try:
            return response.json()
        except ValueError as e:
            raise APIError(e)

    @staticmethod
    def get_games():
        return API._get(games)

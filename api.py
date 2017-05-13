import requests

api_url = "http://ranta.org/frisbeer/API/"
# api_url = "http://localhost:8000/API/"
players = "players"


class APIError(Exception):
    pass


class API:
    @staticmethod
    def get_players():
        response = requests.get(api_url + players, headers={'content-type': 'application/json'})
        if not response.ok:
            raise APIError("Error in response")
        try:
            return response.json()
        except ValueError as e:
            raise APIError(e)

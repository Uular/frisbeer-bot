import logging
import click

from action import ActionBuilder
from api import API, APIError
from frisbeerbot import FrisbeerBot

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


@click.command()
@click.argument("apikey", envvar='APIKEY')
@click.argument("api_url", envvar="API_URL")
@click.argument("username", envvar="API_USERNAME")
@click.argument("password", envvar="API_PASSWORD")
@click.argument("redis_host", envvar="REDIS_HOST", required=False, default="localhost")
@click.argument("redis_port", envvar="REDIS_PORT", type=int, required=False, default=6379)
def run(apikey, api_url, username, password, redis_host, redis_port):
    API.setup(api_url)
    ActionBuilder.setup(redis_host, redis_port)
    try:
        API.login(username, password)
    except APIError as e:
        logging.error("Couldn't log in. Commands requiring a valid api key won't work. %s", e)
    bot = FrisbeerBot(apikey)
    bot.start()


if __name__ == '__main__':
    run()

import logging
import click

from api import API
from frisbeerbot import FrisbeerBot

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


@click.command()
@click.argument("apikey", envvar='APIKEY')
@click.argument("api_url", envvar="API_URL")
@click.argument("username", envvar="USERNAME")
@click.argument("password", envvar="PASSWORD")
def run(apikey, api_url, username, password):
    API.setup(api_url)
    API.login(username, password)
    bot = FrisbeerBot(apikey)
    bot.start()

if __name__ == '__main__':
    run()

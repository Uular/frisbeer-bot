import logging
import sys

from frisbeerbot import FrisbeerBot

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

bot = FrisbeerBot(sys.argv[1])
bot.start()

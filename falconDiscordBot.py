#!/usr/bin/env python3
from dotenv import load_dotenv
from os import getenv

# local imports
import configuration as conf
import discordEventHandlers as deh


if __name__ == "__main__": 

    # Start the logger
    logger = conf.DISCORD_BOT_LOGGER

    # Load the discord bot auth token from the .env file
    load_dotenv()
    token = getenv('DISCORD_BOT_AUTH_TOKEN')

    client = deh.FalconClient(
        intents = conf.DISCORD_BOT_INTENTS, 
        path_to_secret_key = conf.DISCORD_BOT_SECRET_KEY_PATH
    )

    # Run the discord bot
    client.run(token)
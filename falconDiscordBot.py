#!/usr/bin/env python3
"""
A discord bot that can speak post-quantum cryptography. Specifically, a bot that can sign and
veryify Falcon signatures. At some point, we may add additional algorithms if requested on GitHub.

Author: Brian Vohaska
"""
from dotenv import load_dotenv
from os import getenv

# local imports
import configuration as conf
import discordEventHandlers as deh


if __name__ == "__main__": 

    # Load the discord bot auth token from the .env file
    load_dotenv()
    token = getenv('DISCORD_BOT_AUTH_TOKEN')

    # Configure the discord bot
    client = deh.FalconClient(
        intents = conf.DISCORD_BOT_INTENTS, 
        path_to_secret_key = conf.DISCORD_BOT_SECRET_KEY_PATH
    )

    # Run the discord bot
    client.run(token)
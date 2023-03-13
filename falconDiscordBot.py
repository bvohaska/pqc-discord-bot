#!/usr/bin/env python3
import discord
from dotenv import load_dotenv
import logging
from os import getenv, path

# local imports
from falcon import falconlib
import discordEventHandlers as deh

# Set bot permissions (can't be more than authorized in the discord bot API)
intents = discord.Intents.default()
intents.message_content = True
#client = discord.Client(intents=intents)
client = deh.FalconClient(intents=intents)

# Start the logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Set the standard text encoding
standardEncoding = 'utf-8'


if __name__ == "__main__": 

    # Load the discord bot auth token from the .env file
    load_dotenv()
    token = getenv('DISCORD_BOT_AUTH_TOKEN')

    # Load secret key if it exists; else create a new secret key
    path_to_secret_key = 'falconSecretKey.key'
    if path.exists(path_to_secret_key):
        client.sk = falconlib.SecretKey(generate=False)
        client.sk.loadSecretKey(path_to_secret_key)
    else:
        securityLevel = 512
        client.sk = falconlib.SecretKey(securityLevel)
        client.sk.saveSecretKey(path_to_secret_key)
    client.pk = falconlib.PublicKey(client.sk)

    # Run the discord bot
    client.run(token)
#!/usr/bin/env python3
"""
A discord bot that can speak post-quantum cryptography. Specifically, a bot that can sign and
veryify Falcon signatures. At some point, we may add additional algorithms if requested on GitHub.

Author: Brian Vohaska
"""

# local imports
import configuration as conf
import discordEventHandlers as deh


if __name__ == "__main__": 

    # Configure the discord bot
    client = deh.FalconClient(
        intents = conf.DISCORD_BOT_INTENTS, 
        path_to_secret_key = conf.DISCORD_BOT_SECRET_KEY_PATH
    )

    # Run the discord bot
    client.run(conf.DISCORD_BOT_TOKEN)
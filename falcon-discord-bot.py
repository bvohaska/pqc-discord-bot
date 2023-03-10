#!/usr/bin/env python3
from base64 import b85decode, b85encode
import discord
from dotenv import load_dotenv
import io
import logging
from os import getenv

# local imports
from falcon import falconlib

# Set bot permissions (can't be more than authorized in the discord bot API)
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Load the discord bot auth token from the .env file
load_dotenv()
token = getenv('DISCORD_BOT_AUTH_TOKEN')

# Start the logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('Falcon-Sig Bot')

def sign_message(message, truncate:int):   

    # Remove the trigger work, convert the message into binary, and sign
    sig = sk.sign(message.content[truncate:].encode('utf-8'))

    logger.info('Signature generation triggered...')
    logger.debug(f'Received message: {message.content}')
    logger.debug(f'Truncated message: {message.content[truncate:]}')
    
    # Remove str() formatting and return
    return str(b85encode(sig))[2:-1]

async def check_for_message_errors(message):
    if len(message.content) > 100:
        await message.channel.send("I don't want to sign a message that long!")
    if len(message.content) < 14:
        await message.channel.send("You have to supply a message!")

# Basic login message for the bot
@client.event
async def on_ready():
    logger.info(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # SIGN MESSAGE
    if message.content.startswith('$falconpunch'):
        check_for_message_errors(message)
        
        # Sign the message
        response = sign_message(message, 13)
        logger.debug(f'Generated response to the message: {response}')

        # Send response
        await message.channel.send(response)
    
    # VERIFY MESSAGE
    if message.content.startswith('$verify'):
        try:
            # Split message into [trigger], [message], [signature]
            message_components = message.content[8:].split(' ')
            sig = b85decode(message_components[-1])
            message_bytes = ' '.join(message_components[:-1]).encode('utf-8')

            # Check if the signature verifies. If yes, send success. If not, send a failure
            if pk.verify(message_bytes, sig):
                await message.channel.send('The signature is legitimate!')
            else:
                await message.channel.send('The signature failed verification!')
        
        except Exception as e:
            logger.error('Ouch. Exception in $verify', exc_info=True)
            await message.channel.send('hmmm...something went wrong :-(')

    if message.content.startswith('$pubkey'):
        await message.channel.send(pk.savePublicKey(out='memory'))

    if message.content.startswith('$qrsign'):
        import pyqrcode
        sigBuffer = io.BytesIO()
        sig = sign_message(message, 8)
        sigQRData = pyqrcode.create(sig)
        sigQRData.png(sigBuffer)
        sigBuffer.seek(0)
        sigImg = discord.File(sigBuffer)
        sigImg.filename = 'sig.png'
        
        await message.channel.send(file=sigImg)
        
    

def load_key():
    return

def save_key():
    return

if __name__ == "__main__": 

    securityLevel = 512

    sk = falconlib.SecretKey(securityLevel)
    pk = falconlib.PublicKey(sk)

    client.run(token)
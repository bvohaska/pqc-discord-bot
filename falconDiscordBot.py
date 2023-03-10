#!/usr/bin/env python3
from base64 import b85decode, b85encode
import discord
from dotenv import load_dotenv
import io
import logging
from os import getenv, path

# local imports
from falcon import falconlib

# Set bot permissions (can't be more than authorized in the discord bot API)
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Start the logger
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('Falcon-Sig Bot')

# Set the standard text encoding
standardEncoding = 'utf-8'

def sign_message(message, truncate:int):   

    # Remove the trigger work, convert the message into binary, and sign
    sig = sk.sign(message.content[truncate:].encode(standardEncoding))

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
            message_bytes = ' '.join(message_components[:-1]).encode(standardEncoding)

            # Check if the signature verifies. If yes, send success. If not, send a failure
            if pk.verify(message_bytes, sig):
                await message.channel.send('The signature is legitimate!')
            else:
                await message.channel.send('The signature failed verification!')
        
        except Exception as e:
            logger.error('Ouch. Exception in $verify', exc_info=True)
            await message.channel.send('hmmm...something went wrong :-(')

    # SEND PUBLIC KEY (as a base85 encoded string)
    if message.content.startswith('$pubkey'):
        await message.channel.send(pk.savePublicKey(out='memory'))

    # SIGN MESSAGE AND SEND AS QR CODE IMAGE
    if message.content.startswith('$qrsign'):
        import pyqrcode

        lenOfTruncation = 8
        sigBuffer = io.BytesIO()
        # TODO: check that this truncation is correct and not including the character ` `
        sig = sign_message(message, lenOfTruncation)

        #Add message bytes so the signature is complete as a standalone
        messageString = message.content[lenOfTruncation:]+'!ENDMSG'

        # Create a QR code and make sure it scales so the image can be read by a camera
        sigQRData = pyqrcode.create(messageString + sig)
        sigQRData.png(sigBuffer, scale=3)

        # Set the read pointer of the buffer to the beginning so it can be read
        sigBuffer.seek(0)

        # Create a file for Discord to use and name it so the file can be readered in the application
        sigImg = discord.File(fp=sigBuffer, filename='sig.png')
        
        await message.channel.send(file=sigImg)
        
    # READ A QR CODE AND VERIFY
    # TODO: add the ability to read and verify a QR code with a Falcon signature
    if message.content.startswith('$qrverify'):
        from PIL import Image
        from pyzbar.pyzbar import decode
        if len(message.attachments) > 0:
            data = await message.attachments[0].read()
            imgData = Image.open(io.BytesIO(data))
            qrData= decode(imgData)[0].data
            messageBytes = qrData[:qrData.find(b'!ENDMSG')]
            verified = pk.verify(messageBytes, b85decode(qrData[qrData.find(b'!ENDMSG')+len(b'!ENDMSG'):]))
            logger.debug(f'QR Code Bytes: {qrData}')
            logger.debug(f'Message Bytes: {messageBytes}')
            logger.info(f'Did the signature verify? {verified}')
            if verified:
                await message.channel.send("Signature verified!")
            else:
                await message.channel.send("Signature verification failed!")
        else:
            await message.channel.send("Didn't see a QR code :`-(")


if __name__ == "__main__": 

    # Load the discord bot auth token from the .env file
    load_dotenv()
    token = getenv('DISCORD_BOT_AUTH_TOKEN')

    path_to_secret_key = 'falconSecretKey.key'
    if path.exists(path_to_secret_key):
        sk = falconlib.SecretKey(generate=False)
        sk.loadSecretKey(path_to_secret_key)
    else:
        securityLevel = 512
        sk = falconlib.SecretKey(securityLevel)
        sk.saveSecretKey(path_to_secret_key)
    pk = falconlib.PublicKey(sk)

    client.run(token)
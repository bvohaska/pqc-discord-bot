from base64 import b85decode, b85encode
import discord
import io
from PIL import Image
from pyzbar.pyzbar import decode

# local imports
from falcon import falconlib
from configuration import STANDARD_ENCODING, MAX_MESSAGE_SIZE, DISCORD_BOT_LOGGER


# Text Trigger Patterns
SIGN_MESSAGE = '$sign '
VERIFY_MESSAGE = '$verify '
QR_SIGN = '$qrsign '
# Length of trigger patters for truncation
SIGN_TRUNCATE = len(SIGN_MESSAGE)
VERIFY_TRUNCATE = len(VERIFY_MESSAGE)
QR_SIGN_TRUNCATE = len(QR_SIGN)


async def check_for_message_errors(message:discord.Message, truncate:int):
    if len(message.content) > MAX_MESSAGE_SIZE:
        await message.channel.send("I don't want to sign a message that long!")
    if len(message.content) < truncate+1:
        await message.channel.send("You have to supply a message!")


def sign_message(message:discord.Message, truncate:int, sk:falconlib.SecretKey) -> str:   

    # Remove the trigger work, convert the message into binary, and sign
    sig = sk.sign(message.content[truncate:].encode(STANDARD_ENCODING))

    # Log all the things
    DISCORD_BOT_LOGGER.info('Signature generation triggered...')
    DISCORD_BOT_LOGGER.debug(f'Received message: {message.content}')
    DISCORD_BOT_LOGGER.debug(f'Truncated message: {message.content[truncate:]}')
    
    # Return base 85 encoded string without python str() prefix/suffixs
    return str(b85encode(sig))[2:-1]


class FalconClient(discord.Client):

    # Basic login message for the bot
    async def on_ready(self):
        DISCORD_BOT_LOGGER.info(f'We have logged in as {self.user}')


    async def on_message(self,message:discord.Message):
        # DO NOTHING IF THE BOT SENT THE MESSAGE WE ARE LOOKING AT
        if message.author == self.user:
            return

        # SIGN MESSAGE
        if message.content.startswith(SIGN_MESSAGE):
            check_for_message_errors(message=message, truncate=SIGN_TRUNCATE)
            
            # Sign the message
            response = sign_message(message=message, truncate=SIGN_TRUNCATE, sk=self.sk)
            DISCORD_BOT_LOGGER.debug(f'Generated response to the message: {response}')

            # Send response
            await message.channel.send(response)
        
        # VERIFY SIGNATURE
        if message.content.startswith('$verify'):
            lenOfTruncation = len()
            try:
                if len(message.attachments) > 0:
                    data = await message.attachments[0].read()
                    imgData = Image.open(io.BytesIO(data))
                    qrData= decode(imgData)[0].data
                    messageBytes = qrData[:qrData.find(b'!ENDMSG')]
                    verified = self.pk.verify(messageBytes, b85decode(qrData[qrData.find(b'!ENDMSG')+len(b'!ENDMSG'):]))
                else:
                    # Split message into [trigger], [message], [signature]
                    message_components = message.content[8:].split(' ')
                    sig = b85decode(message_components[-1])
                    message_bytes = ' '.join(message_components[:-1]).encode(STANDARD_ENCODING)

                # Check if the signature verifies. If yes, send success. If not, send a failure
                if self.pk.verify(message_bytes, sig):
                    await message.channel.send('The signature is legitimate!')
                else:
                    await message.channel.send('The signature failed verification!')
            
            except Exception as e:
                DISCORD_BOT_LOGGER.error('Ouch. Exception in $verify', exc_info=True)
                await message.channel.send('hmmm...something went wrong :-(')

        # SIGN MESSAGE AND SEND MSG+SIG AS QR CODE
        if message.content.startswith('$qrsign'):
            import pyqrcode

            lenOfTruncation = 8
            sigBuffer = io.BytesIO()
            # TODO: check that this truncation is correct and not including the character ` `
            sig = sign_message(message, lenOfTruncation, self.sk)

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
            
        # READ QR CODE AND VERIFY SIG
        if message.content.startswith('$qrverify'):
            if len(message.attachments) > 0:

                data = await message.attachments[0].read()
                imgData = Image.open(io.BytesIO(data))
                qrData= decode(imgData)[0].data
                messageBytes = qrData[:qrData.find(b'!ENDMSG')]
                verified = self.pk.verify(messageBytes, b85decode(qrData[qrData.find(b'!ENDMSG')+len(b'!ENDMSG'):]))

                DISCORD_BOT_LOGGER.debug(f'QR Code Bytes: {qrData}')
                DISCORD_BOT_LOGGER.debug(f'Message Bytes: {messageBytes}')
                DISCORD_BOT_LOGGER.info(f'Did the signature verify? {verified}')
                if verified:
                    await message.channel.send(f"Message was: \"{messageBytes.decode(STANDARD_ENCODING)}\"\nSignature verified!")
                else:
                    await message.channel.send("Signature verification failed!")
            else:
                await message.channel.send("Didn't see a QR code :`-(")

        # SEND PUBLIC KEY (as a base85 encoded string)
        if message.content.startswith('$pubkey'):
            await message.channel.send(self.pk.savePublicKey(out='memory'))
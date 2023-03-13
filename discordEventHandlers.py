from base64 import b85decode, b85encode
import discord
import io
from PIL import Image
import pyqrcode
from pyzbar.pyzbar import decode

# local imports
import configuration as conf
from falcon import falconlib


async def check_for_message_errors(message:discord.Message, truncate:int):
    if len(message.content) > conf.MAX_MESSAGE_SIZE:
        await message.channel.send("I don't want to sign a message that long!")
    if len(message.content) < truncate+1:
        await message.channel.send("You have to supply a message!")


def sign_message(message:discord.Message, truncate:int, sk:falconlib.SecretKey) -> str:   

    # Remove the trigger work, convert the message into binary, and sign
    sig = sk.sign(message.content[truncate:].encode(conf.STANDARD_ENCODING))

    # Log all the things
    conf.DISCORD_BOT_LOGGER.info('Signature generation triggered...')
    conf.DISCORD_BOT_LOGGER.debug(f'Received message: {message.content}')
    conf.DISCORD_BOT_LOGGER.debug(f'Truncated message: {message.content[truncate:]}')

    encoded_sig = str(b85encode(sig))

    conf.DISCORD_BOT_LOGGER.debug(f'Encoded Signature w/ python formatting: {encoded_sig}')
    
    # Return base 85 encoded string without python str() prefix/suffixs
    return encoded_sig[2:-1]


class FalconClient(discord.Client):

    # Basic login message for the bot
    async def on_ready(self):
        conf.DISCORD_BOT_LOGGER.info(f'We have logged in as {self.user}')


    async def on_message(self,message:discord.Message):
        # DO NOTHING IF THE BOT SENT THE MESSAGE WE ARE LOOKING AT
        if message.author == self.user:
            return

        # SIGN MESSAGE
        if message.content.startswith(conf.SIGN_MESSAGE):
            check_for_message_errors(message=message, truncate=conf.SIGN_TRUNCATE)
            
            # Sign the message
            response = sign_message(message=message, truncate=conf.SIGN_TRUNCATE, sk=self.sk)
            # Quick Fix: Add code block quotes to escape the ` character; won't work in general 
            #   (i.e if there is a ``` in the signature)
            # TODO: .replace('`','\`'); add to VERIFY as well.
            response = '```' + response + '```'

            conf.DISCORD_BOT_LOGGER.debug(f'Generated response to the message: {response}')

            # Send response
            await message.channel.send(response)
        
        # VERIFY SIGNATURE
        if message.content.startswith((conf.VERIFY_MESSAGE, conf.VERIFY_MESSAGE[:-1])):
            lenOfTruncation = conf.VERIFY_TRUNCATE
            try:
                # PEP 8: check if list contains elements; this means the message is a QR code
                if message.attachments:
                    # Read the image attachment as bytes
                    raw_bytes_data = await message.attachments[0].read()
                    # Decode the QR code into a PNG for processing
                    img_data = Image.open(io.BytesIO(raw_bytes_data))
                    # Recover the base 85 encoded data from the QR code (the result will be bytes)
                    qr_data= decode(img_data)[0].data
                    # Parse the data into a message (bytes) and signature (bytes)
                    message_bytes = qr_data[:qr_data.find(b'!ENDMSG')]
                    signature_bytes = b85decode(qr_data[qr_data.find(b'!ENDMSG')+len(b'!ENDMSG'):])
                else:
                    # TODO: check that the message has a space between the trigger and actual message
                    # Split message into [message] and [signature]
                    message_components = message.content[lenOfTruncation:].split(' ')
                    # Decode the base 85 encoded signature into bytes
                    signature_bytes = b85decode(message_components[-1])
                    # Convert the message into bytes
                    message_bytes = ' '.join(message_components[:-1]).encode(conf.STANDARD_ENCODING)

                conf.DISCORD_BOT_LOGGER.debug(f"Message Bytes: {message_bytes}")
                conf.DISCORD_BOT_LOGGER.debug(f"Signature Bytes: {signature_bytes}")

                # Determine if the signature is valid. If yes, send success. If not, send a failure
                if self.pk.verify(message_bytes, signature_bytes):
                    await message.channel.send('The signature is legitimate!')
                else:
                    await message.channel.send('The signature failed verification!')
            
            # TODO: catch different flavors of exceptions
            except Exception as e:
                conf.DISCORD_BOT_LOGGER.error('Ouch. Exception in $verify', exc_info=True)
                await message.channel.send('hmmm...something went wrong :-(')

        # SIGN MESSAGE AND SEND MSG+SIG AS QR CODE
        if message.content.startswith(conf.QR_SIGN):
            
            lenOfTruncation = conf.QR_SIGN_TRUNCATE
            
            # TODO: check that this truncation is correct and not including the character ` `
            sig = sign_message(message, lenOfTruncation, self.sk)

            #Add message bytes so the signature is complete as a standalone
            message_string = message.content[lenOfTruncation:]+'!ENDMSG'

            # Create a QR code and make sure it scales so the image can be read by a camera
            sig_buffer = io.BytesIO()
            sig_QR_data = pyqrcode.create(message_string + sig)
            sig_QR_data.png(sig_buffer, scale=conf.QR_CODE_SIZE)

            # Set the read pointer of the buffer to the beginning so it can be read
            sig_buffer.seek(0)

            # Set the filename
            filename_pattern = f'sig.png'

            # Create a file for Discord to use and name it so the file can be readered in the application
            sig_img = discord.File(fp=sig_buffer, filename=filename_pattern)
            
            await message.channel.send(file=sig_img)
            
        # READ QR CODE AND VERIFY SIG
        if message.content.startswith(conf.QR_VERIFY):
            if len(message.attachments) > 0:

                raw_bytes_data = await message.attachments[0].read()
                img_data = Image.open(io.BytesIO(raw_bytes_data))
                qr_data= decode(img_data)[0].data
                message_bytes = qr_data[:qr_data.find(b'!ENDMSG')]
                verified = self.pk.verify(message_bytes, b85decode(qr_data[qr_data.find(b'!ENDMSG')+len(b'!ENDMSG'):]))

                conf.DISCORD_BOT_LOGGER.debug(f'QR Code Bytes: {qr_data}')
                conf.DISCORD_BOT_LOGGER.debug(f'Message Bytes: {message_bytes}')
                conf.DISCORD_BOT_LOGGER.info(f'Did the signature verify? {verified}')
                if verified:
                    await message.channel.send(f"Message was: \"{message_bytes.decode(conf.STANDARD_ENCODING)}\"\nSignature verified!")
                else:
                    await message.channel.send("Signature verification failed!")
            else:
                await message.channel.send("Didn't see a QR code :`-(")

        # SEND PUBLIC KEY (as a base85 encoded string)
        if message.content.startswith('$pubkey'):
            await message.channel.send(self.pk.savePublicKey(out='memory'))
from base64 import b85decode, b85encode
import discord
import io
from os import path
from PIL import Image
import pyqrcode
from pyzbar.pyzbar import decode
from typing import Any, Coroutine

# local imports
import configuration as conf
from falcon import falconlib


def sign_and_encode_message(
        message:str, 
        truncate:int, 
        secret_key:falconlib.SecretKey
    ) -> str:   
    """Use the Falcon algorithm to sign a string encoded message

    Args:
        message (str): A string encoded message. Our discord bot currently supports UTF-8 and ASCII
        truncate (int): A number of characters that represents the trigger word (which caused the 
            bot to gobble up this message) and a single space that seperates the message from the 
            trigger.
        secret_key (falconlib.SecretKey): A Falcon secret key. This key is serialized and deserialized
            naively due to lack of standards. This will change in the future.
   
    Returns:
        str: The resulting signature encoded as a base 85 string

    """
    conf.DISCORD_BOT_LOGGER.info('Signature generation triggered...')
    conf.DISCORD_BOT_LOGGER.debug(f'Received message: {message}')
    conf.DISCORD_BOT_LOGGER.debug(f'Truncated message: {message[truncate:]}')
    
    # Convert the message string into bytes
    message_bytes = message[truncate:].encode(conf.STANDARD_ENCODING)
    
    # Remove the trigger work, convert the message into binary, and sign
    sig = secret_key.sign(message_bytes)

    # Encode the signature into a base 85 encoded string
    encoded_sig = str(b85encode(sig))

    conf.DISCORD_BOT_LOGGER.debug(f'Encoded Signature w/ python formatting: {encoded_sig}')
    
    # Return base 85 encoded string without python str() prefix/suffixs
    return encoded_sig[2:-1]


class FalconClient(discord.Client):
    """ A wrapper for our discord bot that allows us to do PQC
    
    Attributes:
        security_level (int): The security level of the falcon signature
        secret_key (falconLib.SecretKey): Our bot's Falcon secret key
        public_key (falconLib.PublicKey): Our bot's Falcon public key
        Inherits discord.Client

    TODO:
        * move the security level into falconLib and make sure the value is serialized 
            with the signature
    """
    
    def __init__(self, 
        *,
        path_to_secret_key:str, 
        intents: discord.Intents, 
        **options: Any
    ) -> None:
        """init our new class and inherit discord.Client

        Load secret key from a PATH if it exists; else create a new secret key. Load the associated 
        public key. Ensure that the discord.Client super class is initialized.
        
        Args:
            path_to_secret_key (str):
            intents (discord.Intents):

        """
        self.security_level = 512
        if path.exists(path_to_secret_key):
            self.secret_key = falconlib.SecretKey(generate=False)
            self.secret_key.loadSecretKey(path_to_secret_key)
        else:
            self.secret_key = falconlib.SecretKey(self.security_level)
            self.secret_key.saveSecretKey(path_to_secret_key)
        self.public_key = falconlib.PublicKey(self.secret_key)

        super().__init__(intents=intents, **options)


    async def _check_for_message_errors(self,
            message:discord.Message, 
            truncate:int
        ) -> Coroutine:
        '''Check received discord messages for any issues (defined here)

        Args:
            message (discord.Message): A message object received by discord and given to this function
            truncate (int): A number of characters that represents the trigger word (which caused the 
                bot to gobble up this message) and a single space that seperates the message from the 
                trigger.
        Returns:
            awaitable (Coroutine): An error message we want to send to discord
        
        TODO:
            * Convert this to use a standard error class
        '''
        # Error 1: Message too long
        if len(message.content) > conf.MAX_MESSAGE_SIZE:
            await message.channel.send("I don't want to sign a message that long!")
        # Error 2: No message content (just the trigger word and a space)
        if len(message.content) < truncate+1:
            await message.channel.send("You have to supply a message!")
    

    def _make_text_copiable(unsafe_text:str) -> str:
        """Ensure text can be copied exactly by a user (no rendering out ` or other characters)
            
        TODO:
            * Quick Fix: Add code block quotes to escape the ` character; won't work in general 
                (i.e if there is a ``` in the signature)
            *.replace('`','\`'); add to VERIFY as well.
        """
        return '```' + unsafe_text + '```'


    async def on_ready(self):
        """Basic login message for the bot
        """
        conf.DISCORD_BOT_LOGGER.info(f'We have logged in as {self.user}')


    async def on_message(self,message:discord.Message):
        """
        """
        # DO NOTHING IF THE BOT SENT THE MESSAGE WE ARE LOOKING AT
        if message.author == self.user:
            return

        # SIGN MESSAGE
        if message.content.startswith(conf.SIGN_MESSAGE):
            """Sign the content of a discord message when triggered
            
                Only when the SIGN_MESSAGE trigger has been used should this event trigger
            """
            self._check_for_message_errors(message=message, truncate=conf.SIGN_TRUNCATE)
            response = sign_and_encode_message(
                message=message.content, 
                truncate=conf.SIGN_TRUNCATE, 
                secret_key=self.secret_key
            )
            response = self._make_text_copiable(response)
            conf.DISCORD_BOT_LOGGER.debug(f'Generated response to the message: {response}')

            await message.channel.send(response)
        
        # VERIFY SIGNATURE
        if message.content.startswith((conf.VERIFY_MESSAGE, conf.VERIFY_MESSAGE[:-1])):
            """ Verify 
            """
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
                if self.public_key.verify(message_bytes, signature_bytes):
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
            sig = sign_and_encode_message(message.content, lenOfTruncation, self.secret_key)

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
                verified = self.public_key.verify(message_bytes, b85decode(qr_data[qr_data.find(b'!ENDMSG')+len(b'!ENDMSG'):]))

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
            await message.channel.send(self.public_key.savePublicKey(out='memory'))
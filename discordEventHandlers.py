from base64 import b85decode, b85encode
from datetime import datetime
import discord
from discord.ext import tasks
import io
from logging import getLogger, basicConfig
from os import path
from PIL import Image
import pyqrcode
from pyzbar.pyzbar import decode
from typing import Any, Tuple

# local imports
import configuration as conf
from falcon import falconlib

# Configure the logging level and create the logger for this module
basicConfig(level=conf.DISCORD_BOT_LOG_LEVEL)
DISCORD_BOT_LOGGER = getLogger(__name__)


def serialize_qr_code_for_discord(
        message_string:str, 
        message_terminator:str,
        signature_string:str,
        filename:str,
        filename_pattern:Any) -> discord.File:
    """Create a QR code from some data and return a discord file

    The logic for this function is as follows:
        (1) Append a terminator string to the encoded bytes so we know when to 
            stop reading the message when deserializing. This is done in a naive way
        (2) Create a QR code (scaled properly so the image can be read by a regular camera)
        (3) Save the QR code into a memory buffer
        (4) Convert the bytes in the memory buffer into a PNG
        (5) Set a filename pattern (what the file will be called when a user downloads the file)
        (6) Save the memory buffer as a discord file object and send to the server

    Args:
        message_string (str):
        message_terminator (str):
        signature_string (str):
        filename (str):
        filename_pattern (Any):

    Returns:
        discord.File:

    """
    sig_QR_data = pyqrcode.create(message_string + message_terminator + signature_string)
    sig_buffer = io.BytesIO()
    sig_QR_data.png(sig_buffer, scale=conf.QR_CODE_SIZE)

    # Set the read pointer of the buffer to the beginning so it can be read
    sig_buffer.seek(0)

    if filename == 'sig.png':
        if filename_pattern != None:
            filename = filename_pattern()
        else:
            filename = f'sig{datetime.now().strftime("%d/%m/%Y-%H:%M:%S")}.png'
    sig_img = discord.File(fp=sig_buffer, filename=filename)

    return sig_img


def serialize_text_for_discord(unsafe_text:str) -> str:
    """Ensure text can be copied exactly by a user 
        
        base 85 encoding uses a larger map of characters then base 64. Some of these characters
        are used by discord to render text as Markdown.

        Sometimes discord likes to replace certain characters with a rendering in Markdown. For
        example, the character ` will be rendered as a clock comment if followed by another ` char-
        -acter. In a similar fashion, ``` will create a code block when match with another ```. 
        This is bad because the user copying this string will not be able to copy the rendered `
        or ``` characters and will cause signature verification to fail.
            
        Args:
            unsafe_text (str): A string that might not be rendered correctly to the user

        Returns:
            str: a string with text that should render safely to a discord user

        TODO:
            * Quick Fix: Add code block quotes to escape the ` character; won't work in general 
                (i.e if there is a ``` in the signature)
            *.replace('`','\`'); add to VERIFY as well.
    """
    return '```' + unsafe_text.replace('`','\`') + '```'


def deserialize_qr_code_for_discord(
    raw_bytes:bytes, 
    message_terminator:bytes = conf.END_MSG
) -> Tuple[bytes, bytes]:
    """
    """    
    img_data = Image.open(io.BytesIO(raw_bytes))
    qr_data_byte_string= decode(img_data)[0].data

    message_start = qr_data_byte_string.find(message_terminator)+len(message_terminator)
    encoded_signature = qr_data_byte_string[message_start:]
    message_bytes = qr_data_byte_string[:qr_data_byte_string.find(message_terminator)]
    
    signature_bytes = b85decode(encoded_signature)

    return message_bytes, signature_bytes


def deserialize_text_for_discord(safe_text:str) -> str:
    """Ensure safe text is properly deserialized
    """
    return safe_text.replace('\`','`')


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
    DISCORD_BOT_LOGGER.info('Signature generation triggered...')
    DISCORD_BOT_LOGGER.debug(f'Received message: {message}')
    DISCORD_BOT_LOGGER.debug(f'Truncated message: {message[truncate:]}')
    
    # Convert the message string into bytes
    message_bytes = message[truncate:].encode(conf.STANDARD_ENCODING)
    
    # Remove the trigger work, convert the message into binary, and sign
    sig = secret_key.sign(message_bytes)

    # Encode the signature into a base 85 encoded string
    encoded_sig = str(b85encode(sig))

    DISCORD_BOT_LOGGER.debug(f'Encoded Signature w/ python formatting: {encoded_sig}')
    
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
            path_to_secret_key (str): the path to the Falcon secret key file
            intents (discord.Intents): a set of discord intents that tells the bot what it can do

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

    def _check_for_message_errors(self,
            content:str, 
            truncate:int
        ) -> str:
        '''Check received discord messages for any issues (defined here)

        Args:
            message (discord.Message): A message object received by discord and given to this function
            truncate (int): A number of characters that represents the trigger word (which caused the 
                bot to gobble up this message) and a single space that seperates the message from the 
                trigger.
        Returns:
            str: An error message we want to send to discord
        
        TODO:
            * Convert this to use a standard error class
        '''
        # Error 1: Message too long
        if len(content) > conf.MAX_MESSAGE_SIZE:
            return "I don't want to sign a message that long!"
        # Error 2: No message content (just the trigger word and a space)
        if len(content) < truncate+1:
            return "You have to supply a message!"
    
    def _sign_discord_qrcode_message(self, 
        message: discord.Message, 
        truncate: int, 
        filename:str = 'sig.png',
        filename_pattern: str = None
    ) -> discord.File:
        """Sign a message and return the result as a QR code

        The logic of this function is as follows:
            (1) Sign the text component of the discord message (we only accept text)
            (2) Create and return QR code as a discord file object

        Args:
            message (discord.Message):
            truncate (int):
            filename (str):
            filename_pattern (callable):

        Returns:
            discord.File:

        TODO:
            * check that truncation is correct and is not including the character ` `
        """

        sig = sign_and_encode_message(message.content, truncate, self.secret_key)
        message_string = message.content[truncate:]
        sig_img = serialize_qr_code_for_discord(
            message_string = message_string,
            message_terminator = conf.END_MSG.decode('utf-8'),
            signature_string = sig,
            filename = filename,
            filename_pattern = filename_pattern
        )
        
        return sig_img

    def _sign_discord_text_message(self, message: str, truncate:int) -> str:
        """Sign the content of a discord message when triggered
        
            Only when the SIGN_MESSAGE trigger has been used should this event trigger

            Args:
                message (discord.Message):

            Returns:
                Coroutine: A discord message with a base85 encoded signature

        """
        has_errors = self._check_for_message_errors(content=message, truncate=truncate)
        if has_errors != None:
            return has_errors
        
        response = sign_and_encode_message(
            message=message, 
            truncate=truncate, 
            secret_key=self.secret_key
        )
        response = serialize_text_for_discord(response)
        DISCORD_BOT_LOGGER.debug(f'In sign discord message (message): {message}')
        DISCORD_BOT_LOGGER.debug(f'Generated response to the message: {response}')

        return response

    async def _verify_discord_message(self, message: discord.Message, truncate: int) -> str:
        """Determine if the signature is valid for a given message

        The logic of this function is as follows:
            (1) does the message have attachments? If list contains elements => the attachment should be a QR code
                (a) Read the image attachment as bytes
                (b) Try to decode the QR code into a PNG for processing
                (c) Parse the data into a message (bytes) and signature (bytes)
                (d) Result will comply with interface (which is not recorded yet)
            (2) If not, this is a text signature
                (a) Split message into [message] and [signature]
                (b) Decode the base 85 encoded signature into bytes
                (c) Convert the message into bytes
            (3) Determine if the signature is valid
                (a) If yes, send success
                (b) If not, send a failure

        Args:
            message (discord.Message): 
            A number of characters that represents the trigger word (which caused the 
            bot to gobble up this message) and a single space that seperates the message from the 
            trigger.

        Returns:
            Couroutine: a discord message with the result of the verification OR an error message

        TODO:
            * check that the message txt has a space between the trigger and actual message
            * catch different flavors of exceptions
        """
        try:
            # HAS QRCODE?
            if message.attachments:
                DISCORD_BOT_LOGGER.debug(f"Verifying QR Code signature...")
                attachment_as_bytes = await message.attachments[0].read()
                message_bytes, signature_bytes = deserialize_qr_code_for_discord(attachment_as_bytes, conf.END_MSG)
            # NOPE, JUST TXT
            else:
                DISCORD_BOT_LOGGER.debug(f"Verifying text signature...")
                deserialized_message = deserialize_text_for_discord(message.content[truncate:])
                message_components = deserialized_message.split(' ')
                message_bytes = ' '.join(message_components[:-1]).encode(conf.STANDARD_ENCODING)
                signature_bytes = b85decode(message_components[-1])

            DISCORD_BOT_LOGGER.debug(f"Message Bytes: {message_bytes}")
            DISCORD_BOT_LOGGER.debug(f"Signature Bytes: {signature_bytes}")

            # IS VALID?
            if self.public_key.verify(message_bytes, signature_bytes):
                return 'The signature is legitimate!'
            else:
                return 'The signature failed verification!'
        
        except Exception as e:
            DISCORD_BOT_LOGGER.error('Ouch. Exception in $verify', exc_info=True)
            return 'hmmm...something went wrong :-('

    async def on_ready(self):
        """Basic login message for the bot

        Log that the bot has successfully connected to discord
        
        Args:
            None
        Returns:
            None
        """
        DISCORD_BOT_LOGGER.info(f'We have logged in as {self.user}')

    async def on_message(self,message:discord.Message):
        """Return a response if a message contains a bot command we recognize

        Args:
            message (discord.Message): a discord message object that also includes text content and
                a list of attachments if they exist.
        """

        # DO NOTHING IF THE BOT SENT THE MESSAGE WE ARE LOOKING AT
        if message.author == self.user:
            return

        # SIGN MESSAGE
        if message.content.startswith(conf.SIGN_MESSAGE):
            DISCORD_BOT_LOGGER.info('Reached Sign Text Message')
            response = self._sign_discord_text_message(message=message.content, truncate=conf.SIGN_TRUNCATE)
            await message.channel.send(response)

        # VERIFY SIGNATURE
        if message.content.startswith((conf.VERIFY_MESSAGE, conf.VERIFY_MESSAGE[:-1])):
            DISCORD_BOT_LOGGER.info('Reached Verify Message')
            response = await self._verify_discord_message(message=message, truncate=conf.VERIFY_TRUNCATE)
            await message.channel.send(response)

        # SIGN MESSAGE AND SEND MSG+SIG AS QR CODE
        if message.content.startswith(conf.QR_SIGN):
            DISCORD_BOT_LOGGER.info('Reached QR Sign Message')
            qr_code_file = self._sign_discord_qrcode_message(message=message, truncate=conf.QR_SIGN_TRUNCATE)
            await message.channel.send(file = qr_code_file)

        # SEND PUBLIC KEY (as a base85 encoded string)
        if message.content.startswith(conf.PUBKEY):
            response = self.public_key.savePublicKey(out='memory')
            message.channel.send(response)

    async def setup_hook(self) -> None:
        self.read_nfc_chip_background_task.start()
    
    @tasks.loop(seconds=20)
    async def read_nfc_chip_background_task(self):
        #print("I have reached the background task")
        channel = self.get_channel(int(conf.DISCORD_TEST_CHANNEL_ID))
        # This isn't an event trigger; we will need to save nfc bytes to memory/disk 
        # and read them into a buffer. We will then verify the signature and message
        # and send the message and a welcome text to discord
        #await channel.send("I am a background test that Brian just built")

    @read_nfc_chip_background_task.before_loop
    async def wait_for_ready(self):
        print("Waiting...")
        await self.wait_until_ready()
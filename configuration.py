from discord import Intents
from dotenv import load_dotenv
import logging
from os import getenv
##########################################################
#                Discord Bot Configuration               #
##########################################################

load_dotenv('secrets.env')

############################
#       Load Secrets       #
############################

DISCORD_BOT_TOKEN = getenv('DISCORD_BOT_AUTH_TOKEN')
DISCORD_TEST_CHANNEL_ID = getenv('DISCORD_TEST_CHANNEL_ID')

############################
#   Constants & Literals   #
############################
# Set the size of the QR code
QR_CODE_SIZE = 3

# Set the standard text encoding; this is used for converting back and forth from strings to bytes
STANDARD_ENCODING = 'utf-8'

# Define the maximum number of characters we will accept in a discord text message
MAX_MESSAGE_SIZE = 100

############################
#       File Paths         #
############################
# Path to the bot's Falcon secret key
DISCORD_BOT_SECRET_KEY_PATH = 'falconSecretKey.key'

############################
#         Logging          #
############################
# Set the logging level
DISCORD_BOT_LOG_LEVEL = logging.INFO

############################
# Discord Bot Permissions  #
############################
# Set the default discord intents; intents are a subset of permissions granted to the bot that
#    represent a subset of the total granted permissions; "what do you intend to use"
# Set bot permissions (can't be more than authorized in the discord bot API)
DISCORD_BOT_INTENTS = Intents.default()

# Set message content to true b/c we need to read new messages
DISCORD_BOT_INTENTS.message_content = True

############################
# Discord Message Patterns #
############################
# Text Trigger Patterns
PUBKEY = ('$pubkey ', '$publickey')
SIGN_MESSAGE = '$sign '
VERIFY_MESSAGE = '$verify '
QR_SIGN = '$qrsign '
QR_VERIFY = '$qrverify '

# QR Code Message Terminator String
END_MSG = b'!ENDMSG'

# Length of trigger patters for truncation
SIGN_TRUNCATE = len(SIGN_MESSAGE)
VERIFY_TRUNCATE = len(VERIFY_MESSAGE)
QR_SIGN_TRUNCATE = len(QR_SIGN)
QR_VERIFY_TRUNCATE = len(QR_VERIFY)


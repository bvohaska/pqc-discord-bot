from discord import Intents
import logging
##########################################################
#                Discord Bot Configuration               #
##########################################################

############################
#   Constants & Literals   #
###########################
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

# Configure the logging level
logging.basicConfig(level=DISCORD_BOT_LOG_LEVEL)

# Create a default logger with this configuration
DISCORD_BOT_LOGGER = logging.getLogger(__name__)

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
SIGN_MESSAGE = '$sign '
VERIFY_MESSAGE = '$verify '
QR_SIGN = '$qrsign '
QR_VERIFY = '$qrverify '
END_MSG = '!ENDMSG'

# Length of trigger patters for truncation
SIGN_TRUNCATE = len(SIGN_MESSAGE)
VERIFY_TRUNCATE = len(VERIFY_MESSAGE)
QR_SIGN_TRUNCATE = len(QR_SIGN)
QR_VERIFY_TRUNCATE = len(QR_VERIFY)


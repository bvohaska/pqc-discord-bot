import logging
##########################################################
#                Discord Bot Configuration               #
##########################################################

###########
# Logging #
###########

# Set the logging level
DISCORD_BOT_LOG_LEVEL = logging.INFO

# Configure the logging level
logging.basicConfig(level=DISCORD_BOT_LOG_LEVEL)

# Create a default logger with this configuration
DISCORD_BOT_LOGGER = logging.getLogger(__name__)

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

########################
# Constants & Literals #
########################
# Set the size of the QR code
QR_CODE_SIZE = 3

# Set the standard text encoding; this is used for converting back and forth from strings to bytes
STANDARD_ENCODING = 'utf-8'

# Define the maximum number of characters we will accept in a discord text message
MAX_MESSAGE_SIZE = 100
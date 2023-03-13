import logging
##########################################################
#                Discord Bot Configuration               #
##########################################################

###########
# Logging #
###########

# Set the logging level
DISCORD_BOT_LOG_LEVEL = logging.DEBUG

# Configure the logging level
logging.basicConfig(level=DISCORD_BOT_LOG_LEVEL)

# Create a default logger with this configuration
DISCORD_BOT_LOGGER = logging.getLogger(__name__)


########################
# Constants & Literals #
########################

# Set the standard text encoding; this is used for converting back and forth from strings to bytes
STANDARD_ENCODING = 'utf-8'

# Define the maximum number of characters we will accept in a discord text message
MAX_MESSAGE_SIZE = 100
import logging
from slack_sdk import WebClient
import os
from slack_sdk.errors import SlackApiError
from json import dumps

logger = logging.getLogger(__name__)
slack_bot_token = os.environ.get("SLACK_BOT_TOKEN")
client = WebClient(token=os.environ.get("SLACK_BOT_TOKEN"))

users_store = []
# replace channel's name
channel = "C026JUXSRM2"

def save_users(users_array):
    it = iter(users_array)
    for user in it:
        if user["is_bot"] == False:
            if user["id"] == "U01FBR9HE2E" or user["id"] == "USLACKBOT":
                next(it)
            else:
                users_store.append(user["id"])


try:
    result = client.users_list()
    save_users(result["members"])
    print(client.conversations_invite(channel=channel, users=users_store))
except SlackApiError as e:
    logger.error("Error creating conversation: {}".format(e))

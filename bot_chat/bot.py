from json import dumps
from typing import Dict, Optional
from os import getenv
from sys import exit as sys_exit
from logging import Logger, getLogger, basicConfig, INFO, DEBUG
from requests import post
from requests.exceptions import ConnectionError, Timeout, RequestException
from slackeventsapi import SlackEventAdapter
from slack import WebClient

SERVICEDESK_AUTH: str = getenv("SERVICEDESK_AUTH")
SLACK_BOT_TOKEN: str = getenv("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET: str = getenv("SLACK_SIGNING_SECRET")
if any([not SLACK_BOT_TOKEN, not SLACK_SIGNING_SECRET, not SERVICEDESK_AUTH]):
    print("Environment variables missing")
    sys_exit(-1)
SLACK_EVENTS_ADAPTER: SlackEventAdapter = SlackEventAdapter(SLACK_SIGNING_SECRET, "/slack/events")
SLACK_CLIENT: WebClient = WebClient(SLACK_BOT_TOKEN)
CHANNEL: str = "C0262AMAY72"


def is_second_reply(thread_ts: str) -> bool:
    """
    Check if it is users second reply

    :param thread_ts:  thread parent timestamp
    :type thread_ts: str
    :return: True or false
    :rtype: bool
    """
    result = SLACK_CLIENT.conversations_history(channel=CHANNEL, limit=10)
    for message in result["messages"]:
        if all([message["ts"] == thread_ts, message["reply_count"] == 2]):
            return True
    return False


def post_to_service(text: str) -> Optional[str]:
    """
    Post message to Servicedesk

    :param text: message text
    :type text: str
    :return: String with issue
    :rtype: Optional[str]
    """
    url = "https://servicedesk.cardpay-test.com/rest/servicedeskapi/request"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {SERVICEDESK_AUTH}",  # aS5rYWl1a292YTo1Nzg2OTEwMDkwYjI0OEIl
    }
    data = {
        "serviceDeskId": "12",
        "requestTypeId": "108",
        "requestFieldValues": {
            "summary": "Request raised via service REST API via script",
            "description": text,
        },
    }
    log: Logger = getLogger("bot")
    issue: Optional[str] = None
    try:
        req = post(url, data=dumps(data), headers=headers)
        issue = req.json()["issueKey"]
    except ConnectionError as err:
        log.error("Connection error: %s", err)
    except Timeout as err:
        log.error("Request timed out: %s", err)
    except RequestException as err:
        log.error("Request error: %s", err)
    except ValueError as err:
        log.error("Invalid json in response: %s", err)
    except KeyError as err:
        log.error('No "issueKey" in message: %s', err)
    return issue


@SLACK_EVENTS_ADAPTER.on("message")
def handle_message(event_data: Dict) -> None:
    """
    Handle incoming slack chat messages

    :param event_data: slack event dict
    :type event_data: Dict
    :return:
    """
    log: Logger = getLogger("bot")
    data: Dict = event_data["event"]
    message: str = data.get("text", "")
    if "thread_ts" not in data:
        log.debug("Thread ts not in data")
        if "vpn" in message.lower() or "впн" in message.lower():
            channel: str = data["channel"]
            thread_ts: str = data["ts"]
            user: str = data["user"]
            SLACK_CLIENT.chat_postMessage(
                channel=channel,
                text="Hi <@{}>! There is an article where you can find some tips".format(user),
                thread_ts=thread_ts,
            )
        else:
            channel: str = data["channel"]
            thread_ts: str = data["ts"]
            user: str = data["user"]
            SLACK_CLIENT.chat_postMessage(
                channel=channel,
                text="Hi <@{}>! I'm bot. Please, describe your question briefly".format(user),
                thread_ts=thread_ts,
            )
    else:
        log.debug("Thread ts in data")
        if is_second_reply(
            data["thread_ts"],
        ):
            log.debug("Is second reply")
            channel: str = data["channel"]
            thread_ts: str = data["thread_ts"]
            user: str = data["user"]
            if issue := post_to_service(data["text"]):
                SLACK_CLIENT.chat_postMessage(
                    channel=channel,
                    text=f"Hi <@{user}>! ticket has been created, you can track it here "
                    + "https://servicedesk.cardpay-test.com/servicedesk/customer/portal/12/"
                    + issue.format(user),
                    thread_ts=thread_ts,
                )


@SLACK_EVENTS_ADAPTER.on("error")
def error_handler(err):
    log: Logger = getLogger("bot")
    log.error(str(err))


def init() -> None:
    log_format: str = "%(asctime)s %(levelname)12s: %(message)s"
    basicConfig(level=DEBUG, format=log_format)


def main():
    init()
    SLACK_EVENTS_ADAPTER.start(host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()

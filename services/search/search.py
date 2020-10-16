#!/usr/bin/env python3
import json
import logging
import os
import sys

import redis

import shared.util as util
from shared.exceptions import AlreadyProcessed, CurrentlyProcessing


def main():
    for message in reddit.inbox.stream():
        search(message)


def search(message):
    bot_mention = util.contains_username(config['BOT_NAME'], message.body)
    link = util.contains_link(message.body)

    if bot_mention or link:
        try:
            search_request(message)
        except (AlreadyProcessed, CurrentlyProcessing) as pe:
            util.open_lock(redis, message.id)
            message.mark_read()
            logging.error(f"{pe} Trying to mark as read.")
        except Exception as e:
            util.open_lock(redis, message.id)

            logging.error(f"{type(e).__name__} occurred while searching for request {message.id}: {e}")


def search_request(message):
    # Create request
    request = {
        "id": message.id,
        "type": "comment" if message.was_comment else "message",
        "author": str(message.author),
        "link": f"https://www.reddit.com{message.context}" if message.was_comment else f"https://www.reddit.com/message/messages/{message.id}",
        "retries": 0
    }

    # Check for duplicates
    util.already_processed_check(redis, request)

    lock = util.get_lock(request['id'])
    if redis.exists(lock):
        raise CurrentlyProcessing(request['link'])

    # Lock request to avoid duplicates
    redis.set(lock, "")

    request_json = json.dumps(request)

    # Enqueue for filtering
    redis.sadd(config['REDIS_REQUESTS_FILTER'], request_json)
    message.mark_read()

    logging.info(f"Found new request {request['id']} : {request['link']}.")


if __name__ == '__main__':
    util.log("search")
    config = util.load_configuration()
    reddit = util.authenticate()
    redis = redis.Redis(host=os.environ['REDIS_HOST'], port=os.environ['REDIS_PORT'])

    main()

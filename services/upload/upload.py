#!/usr/bin/env python3
import json
import logging
import os
import redis
import requests
import sys

import shared.util as util
from shared.exceptions import InvalidRequest, AlreadyProcessed


def main():
    request_json = redis.spop(current_set)
    if request_json:
        request = json.loads(request_json.decode('utf-8'))
        try:
            upload_request(request)
        except InvalidRequest as ie:
            util.open_lock(redis, request['id'])

            logging.info(f"Invalid upload request {request['id']} : {request['link']}: {ie}")
        except AlreadyProcessed as ape:
            util.open_lock(redis, request['id'])
            logging.error(ape)
        except Exception as e:
            util.handle_failed_request(redis, request, current_set, e)

            logging.error(
                f"{type(e).__name__} occurred while uploading request {request['id']} : {request['link']} : {e}")


def upload_request(request):
    # Check for duplicates
    util.already_processed_check(redis, request)

    # Create request
    uploaded_link = upload(request['reddit_link'])

    request.update(
        uploaded_link=uploaded_link
    )
    request_json = json.dumps(request)

    # Enqueue for replying
    if uploaded_link:
        success = redis.sadd(next_set, request_json)
        logging.info(f"Uploaded request {request['id']} : {request['link']}.")

    else:
        raise Exception("Invalid upload link.")


def upload(link):
    try:
        response_json = upload_via_reddittube(link)

        if response_json['status'] == 'ok':
            return response_json['share_url']
        else:
            raise Exception(f"Invalid response status: {response_json['status']}")

    except Exception as e:
        raise Exception(f"Couldn't upload to reddittube: {e}")


def upload_via_reddittube(link):
    site_url = "https://reddit.tube/parse"
    response = requests.get(site_url, params={
        'url': link
    }, timeout=250)
    return response.json()


if __name__ == '__main__':
    util.log("upload")
    config = util.load_configuration()
    redis = redis.Redis(host=os.environ['REDIS_HOST'], port=os.environ['REDIS_PORT'])
    current_set = config['REDIS_REQUESTS_UPLOAD']
    next_set = config['REDIS_REQUESTS_REPLY']
    while True:
        main()

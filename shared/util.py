import json
import logging
import os
import re
import sys
import urllib.parse
from urllib.error import HTTPError, URLError
from urllib.request import Request

import praw
import requests
import yaml

from shared.exceptions import AlreadyProcessed


def load_configuration():
    conf_file = os.path.join(os.path.dirname(__file__), os.environ['CONFIG'])
    with open(conf_file, encoding='utf8') as f:
        config = yaml.safe_load(f)
    # load dependent configuration
    config['FOOTER'] = "\n\n ***  \n" + config['INFO_LINK'] + "&#32;|&#32;" + config[
        'CONTACT_LINK'] 

    return config


CONFIG = load_configuration()


def authenticate():
    """Authenticate via praw.ini file, look at praw documentation for more info"""
    authentication = praw.Reddit(site_name=CONFIG['BOT_NAME'])
    logging.info(f'Authenticated as {authentication.user.me()}')
    return authentication


def log(service, stdout=False):
    if stdout:
        logging.basicConfig(
            stream=sys.stdout,
            level=logging.INFO,
            format=f'{service:<6}: %(asctime)s  %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        logging.basicConfig(
            filename=f"shared/logs/bot.log",
            level=logging.INFO,
            format=f'{service:<6}: %(asctime)s  %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


def get_reddit_item(reddit, request):
    if request['type'] == "message":
        return reddit.inbox.message(request['id'])
    else:
        return reddit.comment(request['id'])


def contains_link(string):
    """Returns link or empty string"""
    match_link = re.search(
        r"https?://(www\.)?[-a-zA-Z0-9@:%._+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_+.~#?&/=]*)", string)

    return match_link[0] if match_link else ""


def contains_username(name, string):
    """Returns regex search"""
    return re.search(r"(?i)u/" + name, string)


def get_lock(request_id):
    return f"{CONFIG['REDIS_REQUESTS_LOCKED']}:{request_id}"


def open_lock(redis, request_id):
    # Remove redundant lock to free up space
    lock = get_lock(request_id)
    redis.delete(lock)


def handle_failed_request(redis, request, current_set, exception):
    if request['retries'] > 10:
        open_lock(redis, request['id'])
        request.update(
            error=str(exception)
        )
        next_set = CONFIG['REDIS_REQUESTS_FAILED']
        logging.error(f"Reached retry limit. Pushing request {request['id']} : {request['link']} to failed requests.")
    else:
        request['retries'] += 1
        next_set = current_set

    request_json = json.dumps(request)
    redis.sadd(next_set, request_json)


def is_link_valid(link):
    # Check if download is valid without downloading
    if "reddit.tube" in link:
        if requests.head(link, timeout=10).ok:
            return True
        return False

    try:
        status_code = urllib.request.urlopen(link, timeout=2).getcode()
        return status_code == 200
    except (HTTPError, URLError, ValueError):
        return False


def already_processed_check(redis, request):
    if redis.sismember(CONFIG['REDIS_REQUESTS_SUCCESS'], request['id']):
        raise AlreadyProcessed(request['link'])

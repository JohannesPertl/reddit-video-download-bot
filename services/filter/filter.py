import json
import logging
import os
import re
import redis
import requests
import sys
from praw.exceptions import ClientException, InvalidURL
from prawcore import NotFound

import shared.util as util
from shared.exceptions import InvalidRequest, AlreadyProcessed


def main():
    request_json = redis.spop(CURRENT_SET)

    if request_json:
        request = json.loads(request_json.decode('utf-8'))
        try:
            filter_request(request)
        except (InvalidRequest, InvalidURL, NotFound) as ie:
            util.open_lock(redis, request['id'])

            logging.info(f"{ie}. Ignoring.")
        except AlreadyProcessed as ape:
            util.open_lock(redis, request['id'])
            logging.error(ape)
        except ClientException as ce:
            # Comment is too new, Reddit API doesn't send the comment data yet
            redis.sadd(CURRENT_SET, request_json)
            logging.debug(f"{ce} Retrying..")
        except Exception as e:

            util.handle_failed_request(redis, request, CURRENT_SET, e)
            logging.error(
                f"{type(e).__name__} occurred while filtering request {request['id']} : {request['link']}: {e}")


def filter_request(request):
    # Check for duplicates
    util.already_processed_check(redis, request)

    request_type = request['type']
    reddit_item = util.get_reddit_item(reddit, request)

    # Get submission
    submission = reddit_item.submission if request_type == "comment" else get_submission_from_message(reddit_item.body)

    if not submission:
        raise Exception(f"Invalid submission.")

    if not valid_requirements(submission, reddit_item):
        raise InvalidRequest(request['link'], f"Invalid requirements.")

    # Create request
    reddit_link = "https://www.reddit.com" + submission.permalink

    request.update(
        submission_id=submission.id,
        sub=str(submission.subreddit),
        created_utc=reddit_item.created_utc,
        reddit_link=reddit_link,
        banned=True if submission.subreddit.user_is_banned else False,
        blacklisted=True if submission.author in config['BLACKLIST_SUBMISSION_AUTHORS'] else False,
        nsfw=True if submission.over_18 else False
    )

    # Monitoring
    if request['banned']:
        success = redis.sadd(config["REDIS_BANNED_SUBS"], request['sub'])
        if success:
            logging.info(f"New banned sub found: {request['sub']}!")

    if request['author'] == 'AutoModerator':
        success = redis.sadd(config['REDIS_AUTOMODERATOR_SUBS'], request['sub'])
        if success:
            logging.info(f"New AutoModerator sub found: {request['sub']}!")

    request_json = json.dumps(request)

    # Enqueue for uploading or replying if request was blacklisted by submission author
    next_set = config['REDIS_REQUESTS_REPLY'] if request['blacklisted'] else NEXT_SET
    add_success = redis.sadd(next_set, request_json)

    if add_success:
        logging.info(f"Filtered request {request['id']} : {request['link']}.")


def get_submission_from_message(message):
    link = util.contains_link(message)
    link = re.sub('DASH.*', '', link)
    return reddit.submission(url=requests.get(link, timeout=5).url)


def valid_requirements(submission, message):
    return not submission.is_self and submission.subreddit not in config[
        'BLACKLIST_SUBS'] and message.author not in config['BLACKLIST_USERS']


if __name__ == '__main__':
    util.log("filter")

    config = util.load_configuration()
    reddit = util.authenticate()
    redis = redis.Redis(host=os.environ['REDIS_HOST'], port=os.environ['REDIS_PORT'])
    CURRENT_SET = config['REDIS_REQUESTS_FILTER']
    NEXT_SET = config['REDIS_REQUESTS_UPLOAD']
    while True:
        main()

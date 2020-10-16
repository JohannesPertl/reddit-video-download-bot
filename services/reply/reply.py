import demoji
import json
import logging
import os
import redis
from datetime import date
from praw.exceptions import RedditAPIException

import shared.util as util
from shared.exceptions import InvalidRequest, AlreadyProcessed, CommentingFailed


def main():
    request_json = redis.spop(current_set)
    if request_json:
        request = json.loads(request_json.decode('utf-8'))
        try:
            reply_to_request(request)
        except InvalidRequest as ir:
            util.open_lock(redis, request['id'])

            logging.info(ir)
        except AlreadyProcessed as ap:
            util.open_lock(redis, request['id'])
            logging.error(ap)
        except CommentingFailed as cf:
            util.handle_failed_request(redis, request, current_set, cf)
            logging.error(cf)
        except RedditAPIException as rae:
            if "NOT_WHITELISTED_BY_USER_MESSAGE" in str(rae):
                redis.sadd(config['REDIS_NOT_WHITELISTED_USERS'], request['author'])
                util.open_lock(redis, request['id'])
                logging.error(
                    f"User {request['author']} needs to whitelist me. Adding to {config['REDIS_NOT_WHITELISTED_USERS']}")
            else:
                util.handle_failed_request(redis, request, current_set, rae)
                logging.error(
                    f"{type(rae).__name__} occurred while replying to request {request['id']} : {request['link']} : {rae}.")
        except Exception as e:
            util.handle_failed_request(redis, request, current_set, e)
            logging.error(
                f"{type(e).__name__} occurred while replying to request {request['id']} : {request['link']} : {e}.")


def reply_to_request(request):
    # Check for duplicates
    util.already_processed_check(redis, request)

    if request['blacklisted']:
        reply_blacklisted(request)
    elif should_send_message(request):
        reply_per_message(request)
    else:
        reply_per_comment(request)

    # Add request to processed
    redis.sadd(next_set, request['id'])

    # Monitoring
    redis.incr(f"{config['REDIS_REQUESTS']}:{date.today()}")
    redis.incr(config['REDIS_REQUESTS'])
    redis.sadd(config['REDIS_USERS'], request['author'])

    util.open_lock(redis, request['id'])
    logging.info(f"Finished with request {request['id']}. Opening lock..")


def reply_blacklisted(request):
    reply = config['HEADER_BLACKLISTED'] + config['FOOTER']
    user = reddit.redditor(request['author'])
    author = reddit.submission(request['submission_id']).author
    subject = f"{author} doesn't allow video downloads"
    user.message(subject, reply)
    logging.info(f"replied to blacklisted request {request['id']} : {request['link']}.")


def build_reply(request, reply_type):
    uploaded_link = request['uploaded_link']
    submission = reddit.submission(request['submission_id'])

    nsfw_warning = ''
    if submission.over_18:
        nsfw_warning = '**NSFW** '

    reply = f"###[{nsfw_warning}{config['DOWNLOAD_TEXT']}]({uploaded_link})"

    header = ''
    announcement = ''
    if request['type'] == 'comment' and reply_type == 'comment':
        announcement = config['ANNOUNCEMENT_COMMENT']
        header = config['HEADER']
    elif request['type'] == 'comment' and reply_type == 'message':
        announcement = config['ANNOUNCEMENT_PM']

    reply = header + reply + announcement

    # Footer
    footer = config['FOOTER']
    if request['sub'] in config['NO_FOOTER_SUBS']:
        footer = ""

    # Emojis
    if request['sub'] in config['NO_EMOJI_SUBS']:
        reply = demoji.replace(reply, "")

    return reply + reddit_tube_ad + footer


def should_send_message(request):
    return request['banned'] or request['sub'] in config[
        'PM_SUBS']  # Uncomment for replying only once per submission
    # or redis.sismember(config['REDIS_SUBMISSIONS'], request['submission_id'])


def reply_to_submission(request):
    reply = build_reply(request, "comment")

    submission = reddit.submission(id=request['submission_id'])
    try:
        submission.reply(reply)

        redis.sadd(config['REDIS_SUBMISSIONS'], request['submission_id'])
        logging.info(
            f"replied to submission of request {request['id']} : {request['link']}.")
    # Send PM if replying to the comment went wrong
    except Exception as e:
        print(e)


def reply_per_comment(request):
    reply = build_reply(request, "comment")

    reddit_item = util.get_reddit_item(reddit, request)
    try:
        reddit_item.reply(reply)
        redis.sadd(config['REDIS_SUBMISSIONS'], request['submission_id'])
        logging.info(
            f"replied to request {request['id']} : {request['link']} per comment.")
    # Send PM if replying to the comment went wrong
    except Exception as e:
        # Don't send PM to AutoModerator
        if request['author'] == 'AutoModerator':
            raise CommentingFailed(request['link'])

        logging.info(f"Couldn't reply per comment: {e}. Replying per PM.")
        reply_per_message(request)


def reply_per_message(request):
    reply = build_reply(request, "message")

    user = reddit.redditor(request['author'])
    subject = config['PM_SUBJECT']
    user.message(subject, reply)
    logging.info(f"Replied to request {request['id']} : {request['link']} per PM.")


if __name__ == '__main__':
    util.log("reply")

    config = util.load_configuration()
    reddit = util.authenticate()
    redis = redis.Redis(host=os.environ['REDIS_HOST'], port=os.environ['REDIS_PORT'])

    current_set = config['REDIS_REQUESTS_REPLY']
    next_set = config['REDIS_REQUESTS_SUCCESS']
    while True:
        main()

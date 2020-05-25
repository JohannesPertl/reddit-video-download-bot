#!/usr/bin/env python3
"""Reddit Bot that provides downloadable links for v.redd.it videos"""

import os
import re
import time
import urllib.parse
from urllib.error import HTTPError, URLError
from urllib.request import Request

import praw
import requests
import yaml


def run_bot():
    # Search mentions in inbox
    inbox = list(reddit.inbox.unread(limit=config['INBOX_LIMIT']))
    inbox.reverse()
    for message in inbox:
        try:
            process_message(message)
        except Exception as e:
            print(e)


def process_message(message):
    submission = get_user_request_submission(message)

    if not valid_requirements(submission, message):
        message.mark_read()
        return

    # Upload
    reddit_link = "https://www.reddit.com" + submission.permalink
    uploaded_link = upload(message, reddit_link)
    if uploaded_link:
        reply = f"##[{config['DOWNLOAD_TEXT']}]({uploaded_link})"
    else:
        return

    announcement = ''
    if message.was_comment:
        announcement = config['ANNOUNCEMENT_PM']
    reply = config['HEADER'] + reply + announcement

    reply_to_user(message, reply, message.author)


def get_user_request_submission(message):
    body = str(message.body)
    match_request = re.search(r"(?i)u/" + config['BOT_NAME'], body)
    match_link = re.search(
        r"https?://(www\.)?[-a-zA-Z0-9@:%._+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_+.~#?&/=]*)", body)

    if message.was_comment and match_request:
        return message.submission

    elif match_link:
        try:
            link = re.sub('DASH.*', '', match_link[0])
            return reddit.submission(url=requests.get(link).url)
        except:
            return ""

    return ""


def valid_requirements(submission, message):
    return submission and "v.redd.it" in submission.url and submission.subreddit not in config[
        'BLACKLIST_SUBS'] and message.author not in config['BLACKLIST_USERS']


def upload(message, link):
    request_age = time.time() - message.created_utc
    if request_age > config['REQUEST_AGE_LIMIT'] * 60:
        print("Bot is too slow, switching to fast upload methods")
        return fast_upload(link)

    return slow_upload(link)


def fast_upload(link):
    print("Linking directly to https://reddit.tube")
    return link.replace(".com", ".tube")


def slow_upload(link):
    try:
        print("Uploading..")
        uploaded_url = upload_via_reddittube(link)
        if is_link_valid(uploaded_url):
            return uploaded_url
    except Exception as e:
        print(e)

    return fast_upload(link)


def upload_via_reddittube(link):
    site_url = "https://reddit.tube/parse"
    response = requests.get(site_url, params={
        'url': link
    })
    response_json = response.json()
    return response_json['share_url']


def is_link_valid(link):
    # Check if download is valid without downloading
    if "reddit.tube" in link:
        if requests.head(link).ok:
            return True
        return False

    try:
        status_code = urllib.request.urlopen(link, timeout=2).getcode()
        return status_code == 200
    except (HTTPError, URLError, ValueError):
        return False


def reply_to_user(message, reply, user):
    if str(message.subreddit) in config['NO_FOOTER_SUBS']:
        footer = ""
    else:
        footer = config['FOOTER']

    if str(message.subreddit) in config['PM_SUBS']:
        reply_per_pm(message, reply, user)
    else:
        try:
            message.reply(reply + footer)
            message.mark_read()
            print(f'Replied to {user} \n')
        # Send PM if replying to the comment went wrong
        except:
            try:
                reply_per_pm(message, reply, user)
                print(f'Sent PM to {user} \n')
            except Exception as e:
                print(e)


def reply_per_pm(message, reply, user):
    pm = reply + config['FOOTER']
    subject = config['PM_SUBJECT']
    user.message(subject, pm)
    message.mark_read()


def load_configuration():
    conf_file = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(conf_file, encoding='utf8') as f:
        configuration = yaml.safe_load(f)
    # load dependent configuration
    configuration['FOOTER'] = "\n\n ***  \n" + configuration['INFO_LINK'] + "&#32;|&#32;" + configuration[
        'DONATION_LINK'] + "&#32;|&#32;" + configuration['GITHUB_LINK']
    return configuration


def authenticate():
    """Authenticate via praw.ini file, look at praw documentation for more info"""
    print('Authenticating...\n')
    authentication = praw.Reddit(site_name=config['BOT_NAME'], user_agent=config['USER_AGENT'])
    print(f'Authenticated as {authentication.user.me()}\n')
    return authentication


if __name__ == '__main__':
    config = load_configuration()
    reddit = authenticate()
    while True:
        run_bot()

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


def load_configuration():
    conf_file = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(conf_file, encoding='utf8') as f:
        settings = yaml.safe_load(f)
    # load dependent configuration
    settings['FOOTER'] = "\n\n ***  \n" + settings['INFO_LINK'] + "&#32;|&#32;" + settings[
        'DONATION_LINK'] + "&#32;|&#32;" + settings['GITHUB_LINK']
    return settings


SETTINGS = load_configuration()


def run_bot(reddit):
    # Search mentions in inbox
    inbox = list(reddit.inbox.unread(limit=SETTINGS['INBOX_LIMIT']))
    inbox.reverse()
    for request in inbox:

        # Determine type
        request_type = type_of_request(request)

        if not request_type:
            continue

        elif request_type == "comment":
            submission = request.submission
            announcement = SETTINGS['ANNOUNCEMENT_PM']
        else:  # request_type is message
            submission = get_original_submission(reddit, request_type)
            announcement = ""

        # Check requirements
        try:
            if not submission or "v.redd.it" not in submission.url \
                    or submission.subreddit in SETTINGS['BLACKLIST_SUBS'] or request.author in SETTINGS['BLACKLIST_USERS']:
                request.mark_read()
                continue
        except:
            continue

        # Upload
        reddit_link = "https://www.reddit.com" + submission.permalink
        uploaded_link = upload(request, reddit_link)
        if uploaded_link:
            reply = f'#[Download]({uploaded_link})'
        else:
            continue

        reply = SETTINGS['HEADER'] + reply + announcement
        print(reply)

        reply_to_user(request, reply, reddit, request.author)


def authenticate():
    """Authenticate via praw.ini file, look at praw documentation for more info"""
    print('Authenticating...\n')
    reddit = praw.Reddit('ExampleBot', user_agent=SETTINGS['USER_AGENT'])
    print(f'Authenticated as {reddit.user.me()}\n')
    return reddit


def type_of_request(item):
    """Check if item to reply to is comment or private message"""
    body = str(item.body)
    match_request = re.search(r"(?i)" + SETTINGS['BOT_NAME'], body)
    match_link = re.search(
        r"https?://(www\.)?[-a-zA-Z0-9@:%._+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_+.~#?&/=]*)", body)

    if item.was_comment and match_request:
        return "comment"

    elif match_link:
        return match_link[0]

    return ""


def get_original_submission(reddit, link):
    """Gets the original reddit submission, as the link sometimes is a crosspost"""
    try:
        link = re.sub('DASH.*', '', link)
        return reddit.submission(url=requests.get(link).url)
    except Exception as e:
        print(e)
        return ""


def upload(item, link):
    request_age = time.time() - item.created_utc
    if request_age > SETTINGS['REQUEST_AGE_LIMIT'] * 60:
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


def reply_to_user(item, reply, reddit, user):
    if str(item.subreddit) in SETTINGS['NO_FOOTER_SUBS']:
        footer = ""
    else:
        footer = SETTINGS['FOOTER']

    if str(item.subreddit) in SETTINGS['PM_SUBS']:
        reply_per_pm(item, reply, reddit, user)
    else:
        try:
            item.reply(reply + footer)
            item.mark_read()
            print(f'Replied to {user} \n')
        # Send PM if replying to the comment went wrong
        except:
            try:
                reply_per_pm(item, reply, reddit, user)
                print(f'Sent PM to {user} \n')
            except Exception as e:
                print(e)


def reply_per_pm(item, reply, reddit, user):
    pm = reply + SETTINGS['FOOTER']
    subject = SETTINGS['PM_SUBJECT']
    reddit.redditor(user).message(subject, pm)
    item.mark_read()


if __name__ == '__main__':
    reddit = authenticate()
    while True:
        run_bot(reddit)

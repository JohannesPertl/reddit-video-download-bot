#!/usr/bin/env python3
"""Reddit Bot that provides downloadable links for v.redd.it videos"""

import os
import re
import urllib.parse
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import praw
import requests
import yaml
from praw.models import Comment, Message


def load_configuration():
    conf_file = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(conf_file, encoding='utf8') as f:
        settings = yaml.safe_load(f)
    # load dependent configuration
    settings['FOOTER'] = "\n\n&nbsp;\n ***  \n ^" + settings['INFO'] + "&#32;|&#32;" + settings['DONATE']
    return settings


SETTINGS = load_configuration()


def main():
    reddit = authenticate()
    while True:
        # Search mentions in inbox
        inbox = list(reddit.inbox.unread(limit=SETTINGS['INBOX_LIMIT']))
        inbox.reverse()
        for item in inbox:
            author = str(item.author)

            # Check requirements
            match_type = type_of_item(item)
            if not match_type:
                continue
            elif match_type == "comment":
                submission = item.submission
                announcement = SETTINGS['ANNOUNCEMENT_PM']
            else:  # match_type is message
                submission = get_real_reddit_submission(reddit, match_type)
                announcement = ""

            try:
                if not submission or "v.redd.it" not in str(submission.url) or str(
                        submission.subreddit) in SETTINGS['BLACKLIST_SUBS'] or author in SETTINGS['BLACKLIST_USERS']:
                    continue
            except Exception as e:
                print(e)
                continue

            # Get media and audio URL
            vreddit_url = create_vreddit_url(submission, reddit)
            if not vreddit_url:
                vreddit_url = submission.url
                reply_no_audio = ""
            else:
                reply_no_audio = f'* [**Downloadable video link**]({vreddit_url})'

            audio_url = vreddit_url.rpartition('/')[0] + '/audio'
            has_audio = check_audio(audio_url)
            reply_audio_only = ""
            if has_audio:
                reply_audio_only = f'* [Audio only]({audio_url})'
                reply_no_audio = f'* [Downloadable soundless link]({vreddit_url})'

            reply = reply_no_audio
            if SETTINGS['ALWAYS_UPLOAD'] or has_audio or vreddit_url == submission.url:

                upload_path = SETTINGS['DATA_PATH'] + f'uploaded/{submission.id!s}.txt'

                # Upload
                uploaded_url = upload(submission, upload_path)
                if uploaded_url:
                    # Create log file with uploaded link, named after the submission ID
                    create_log(upload_path, uploaded_url)
                    if "viddit" in uploaded_url:
                        direct_link = "* [**Download** via https://viddit.red]("
                    elif "vreddit" in uploaded_url:
                        direct_link = "* [**Download** via https://vreddit.cc]("
                    else:
                        direct_link = "* [**Download**]("
                    try:
                        reply_audio = direct_link + uploaded_url + ")"
                        reply = f'{reply_audio}\n\n{reply_no_audio}\n\n{reply_audio_only}'
                    except Exception as e:
                        print(e)
                elif has_audio:
                    reply = "Sry, I can only provide a soundless video at the moment. Please try again later. \n\n" + reply_no_audio

            reply = reply + announcement
            reply_to_user(item, reply, reddit, author)


def authenticate():
    """Authenticate via praw.ini file, look at praw documentation for more info"""
    print('Authenticating...\n')
    reddit = praw.Reddit('vreddit', user_agent='vreddit')
    print(f'Authenticated as {reddit.user.me()}\n')
    return reddit


def upload(submission, upload_path):
    """Check if already uploaded before"""
    print("Check uploaded log")
    uploaded_url = uploaded_log_exists(upload_path)
    if uploaded_url:
        return uploaded_url

    permalink = "https://www.reddit.com" + submission.permalink

    try:
        print("Uploading via vreddit.cc")
        uploaded_url = upload_via_vredditcc(permalink)
        if is_url_valid(uploaded_url):
            return uploaded_url
    except Exception as e:
        print(e)

    try:
        print("Uploading via viddit.red")
        uploaded_url = upload_via_viddit(permalink)
        print(uploaded_url)
        if is_url_valid(uploaded_url):
            return uploaded_url
    except Exception as e:
        print(e)

    return uploaded_url


def upload_via_viddit(url):
    """Upload video via https://viddit.red"""
    parsed_url = urllib.parse.quote(url, safe='')
    return f'https://viddit.red/?url={parsed_url}'


def upload_via_vredditcc(url):
    """Generate video link for https://vreddit.cc"""
    vreddit_video = re.compile(r'https?://v\.redd\.it/(\w+)')
    vreddit_id = vreddit_video.findall(url)[0]
    return "https://vreddit.cc/" + vreddit_id


def check_audio(url):
    """Check if v.redd.it link has audio"""
    try:
        req = Request(url)
        resp = urlopen(req)
        resp.read()
        return True
    except:
        return False


def create_log(file, content):
    """Create .txt file that contains uploaded url"""
    try:
        print('Creating txt file.')
        with open(file, "w+") as f:
            f.write(content)
    except Exception as e:
        print(e)
        print("ERROR: Can't create txt file.")


def reply_per_pm(item, reply, reddit, user):
    pm = reply + SETTINGS['FOOTER']
    subject = "I couldn't reply to your comment so you get a PM instead :)"
    print("Can't comment. Replying per PM.")
    reddit.redditor(user).message(subject, pm)
    item.mark_read()


def reply_to_user(item, reply, reddit, user):
    """Reply per comment"""
    if str(item.subreddit) in SETTINGS['NO_FOOTER_SUBS']:
        footer = ""
    else:
        footer = SETTINGS['FOOTER']

    print('Replying... \n')
    if str(item.subreddit) in SETTINGS['PM_SUBS']:
        reply_per_pm(item, reply, reddit, user)
    else:
        try:
            item.reply(reply + footer)
            item.mark_read()

        # Send PM if replying to the comment went wrong
        except Exception as e:
            print(e)
            try:
                reply_per_pm(item, reply, reddit, user)
            except Exception as f:
                print(f)


def is_url_valid(url):
    try:
        status_code = urllib.request.urlopen(url, timeout=2).getcode()
        return status_code == 200
    except (HTTPError, URLError, ValueError):
        return False


def create_vreddit_url(submission, reddit):
    """Read video url from reddit submission"""
    try:
        return str(submission.media['reddit_video']['fallback_url'])
    except Exception as e:
        # Submission is a crosspost
        try:
            crosspost_id = submission.crosspost_parent.split('_')[1]
            s = reddit.submission(crosspost_id)
            return s.media['reddit_video']['fallback_url']
        except Exception as f:
            print(f)
            print("Can't read vreddit url, skipping")
            return ""


def get_real_reddit_submission(reddit, url):
    try:
        link = re.sub('DASH.*', '', url)
        return reddit.submission(url=requests.get(link).url)
    except Exception as e:
        print(e)
        return ""


def type_of_item(item):
    """Check if item to reply to is comment or private message"""
    body = str(item.body)
    match_text = re.search(r"(?i)" + SETTINGS['BOT_NAME'], body)
    match_link = re.search(
        r"https?://(www\.)?[-a-zA-Z0-9@:%._+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_+.~#?&/=]*)", body)

    if isinstance(item, Comment) and match_text:
        return "comment"

    elif isinstance(item, Message) and match_link:
        return match_link[0]

    return ""


def uploaded_log_exists(upload_path):
    """Check if video has been uploaded before"""
    if not os.path.exists(upload_path):
        return ""

    try:
        with open(upload_path, 'r') as content_file:
            uploaded_url = content_file.read()
            if not is_url_valid(uploaded_url):
                print("Old URL not valid anymore, deleting..")
                os.remove(upload_path)
                return ""
            return uploaded_url
    except Exception as e:
        print(e)
        print("Couldn't get URL, continuing..")
        return ""


if __name__ == '__main__':
    main()

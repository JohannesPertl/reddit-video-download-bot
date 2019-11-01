#!/usr/bin/env python3
"""Reddit Bot that provides downloadable links for v.redd.it videos"""

import os
import re
import time
from urllib.request import Request, urlopen

import certifi
import praw
import requests
import yaml
from praw.models import Comment
from praw.models import Message


def load_configuration():
    conf_file = os.path.join(os.path.dirname(__file__), "configuration.yml")
    with open(conf_file) as f:
        settings = yaml.safe_load(f)
    # load dependent configuration
    settings['FOOTER'] = "\n\n&nbsp;\n ***  \n ^" + settings['INFO'] + "&#32;|&#32;" + settings[
        'CONTACT'] + "&#32;|&#32;" + settings['DONATE']
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
            media_url = create_media_url(submission, reddit)
            if not media_url:
                media_url = submission.url
                reply_no_audio = ""
            else:
                reply_no_audio = '* [**Downloadable video link**](' + media_url + ')'

            audio_url = media_url.rpartition('/')[0] + '/audio'
            has_audio = check_audio(audio_url)
            reply_audio_only = ""
            if has_audio:
                reply_audio_only = '* [Audio only](' + audio_url + ')'
                reply_no_audio = '* [Downloadable soundless link](' + media_url + ')'

            reply = reply_no_audio
            if SETTINGS['ALWAYS_UPLOAD'] or has_audio or media_url == submission.url:

                upload_path = SETTINGS['DATA_PATH'] + 'uploaded/' + str(submission.id) + '.txt'

                # Upload
                uploaded_url = upload(submission, upload_path)
                if uploaded_url:
                    # Create log file with uploaded link, named after the submission ID
                    create_log(upload_path, uploaded_url)
                    if "ripsave" in uploaded_url:
                        direct_link = "* [**Download** via https://ripsave.com**]("
                        announcement = SETTINGS['ANNOUNCEMENT_RIPSAVE']
                    elif "lew.la" in uploaded_url:
                        direct_link = "* [**Download** via https://lew.la]("
                    else:
                        direct_link = "* [**Download**]("
                    try:
                        reply_audio = direct_link + uploaded_url + ")"
                        reply = reply_audio + '\n\n' + reply_no_audio + '\n\n' + reply_audio_only
                    except Exception as e:
                        print(e)
                elif has_audio:
                    reply = "Sry, I can only provide a soundless video at the moment. Please try again later. \n\n" + reply_no_audio

            reply = reply + announcement
            reply_to_user(item, reply, reddit, author)

            time.sleep(2)


def authenticate():
    """Authenticate via praw.ini file, look at praw documentation for more info"""
    print('Authenticating...\n')
    reddit = praw.Reddit('vreddit', user_agent='vreddit')
    print('Authenticated as {}\n'.format(reddit.user.me()))
    return reddit


def upload(submission, upload_path):
    """Check if already uploaded before"""
    print("Check uploaded log")
    uploaded_url = uploaded_log_exists(upload_path)
    if uploaded_url:
        return uploaded_url

    permalink = "https://www.reddit.com" + submission.permalink

    try:
        print("Uploading via lew.la")
        uploaded_url = upload_via_lewla(permalink)
        if is_url_valid(uploaded_url):
            return uploaded_url
    except Exception as e:
        print(e)

    try:
        print("Uploading via Ripsave")
        uploaded_url = upload_via_ripsave(permalink, submission)
        if is_url_valid(uploaded_url):
            return uploaded_url
    except Exception as e:
        print(e)

    return uploaded_url


def upload_via_lewla(url_to_upload):
    """Upload video via https://lew.la"""
    site_url = "https://lew.la/reddit/download"
    response = requests.post(site_url, data={
        'url': url_to_upload
    })

    uploaded_link = "https://lew.la/reddit/clips/" + response.text + ".mp4"
    return uploaded_link


def upload_via_ripsave(url_to_upload, submission):
    """Upload video via https://ripsave.com"""
    site_url = "https://ripsave.com"
    post_link = site_url + "/getlink"
    upload_request = requests.post(post_link, data={
        'url': url_to_upload
    })

    if upload_request.status_code != 200:
        return ""

    dash_video = str(submission.url)
    dash_video_id = dash_video.replace('https://v.redd.it/', '')

    # Choose best quality available
    quality_list = ["1080", "720", "480", "360", "240", "96"]
    quality = ""
    create_download_link = ""
    for q in quality_list:
        create_download_link = "https://ripsave.com/genlink?s=reddit" + "&v=" + dash_video + "/DASH_" + q + "&a=" + dash_video + "/audio&id=" + dash_video_id + "&q=" + q + "&t=" + dash_video_id

        if (requests.get(create_download_link)).status_code == 200:
            quality = q
            break

    if not quality:
        return ""

    # Create log to keep links active via external script
    link_to_update = SETTINGS['DATA_PATH'] + 'ripsave/' + dash_video_id + '.txt'
    create_log(link_to_update, create_download_link)

    # Generate download link
    download_link = site_url + "/download?t=" + dash_video_id + "&f=" + dash_video_id + "_" + quality + ".mp4"

    return download_link


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
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        urlopen(req, cafile=certifi.where())
    except:
        return False
    else:
        return True


def create_media_url(submission, reddit):
    """Read video url from reddit submission"""
    media_url = "False"
    try:
        media_url = submission.media['reddit_video']['fallback_url']
        media_url = str(media_url)
    except Exception as e:
        print(e)
        try:
            crosspost_id = submission.crosspost_parent.split('_')[1]
            s = reddit.submission(crosspost_id)
            media_url = s.media['reddit_video']['fallback_url']
        except Exception as f:
            print(f)
            print("Can't read media_url, skipping")

    return media_url


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

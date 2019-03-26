# !/usr/bin/env python3

# Reddit Bot that provides downloadable links for v.redd.it videos (Audio)


import praw
import time
import re
import random
import os.path
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import urllib.request, urllib.error
import certifi
from urllib.request import Request, urlopen
import youtube_dl
import pomf
import requests
from praw.models import Comment
from praw.models import Message


# Constants
BOT_NAME = "u/vreddit_bot"
DATA_PATH = '/home/pi/bots/vreddit/data/'
VIDEO_FORMAT = '.mp4'
COMMENTED_PATH = DATA_PATH + 'commented.txt'
BLACKLIST_USERS = ['null', 'AutoModerator']
ANNOUNCEMENT = "\n\nUse your mobile browser if your app has problems opening my links."
FOOTER = ("  \n ***  \n ^I\'m&#32;a&#32;Bot&#32;*bleep*&#32;*bloop*&#32;|&#32;[**Contact&#32;Developer**](https://np.reddit.com/message/compose?to=/u/Synapsensalat)&#32;|&#32;[**Info**](https://np.reddit.com/r/vredditDownloader/comments/9h41sx/info)&#32;|&#32;[**Donate**](https://np.reddit.com/r/vredditDownloader/wiki/index)")
INBOX_LIMIT = 25
RATELIMIT = 2000000
MAX_FILESIZE = int('200000000')


def main():
    reddit = authenticate()
    while True:
        # Search mentions in inbox
        inbox = list(reddit.inbox.unread(limit=INBOX_LIMIT))
        inbox.reverse()
        for item in inbox:
            author = str(item.author)

            # Check requirements
            match_type = type_of_item(item)
            if not match_type:
                continue
            elif match_type == "comment":
                submission = item.submission
            else:
                submission = get_real_reddit_submission(reddit, match_type)

            if "v.redd.it" not in submission.url:
                continue

            # Get media and audio URL
            media_url = create_media_url(submission, reddit)
            if not media_url:
                media_url = submission.url
                reply_no_audio = ""
            else:
                reply_no_audio = '* [**Soundless video**](' + media_url + ')'

            audio_url = media_url.rpartition('/')[0] + '/audio'
            reply = reply_no_audio
            header = "#Downloadable link:\n\n"
            
            if media_url == submission.url or has_audio(audio_url):
                if media_url == submission.url:
                    reply_audio_only = ""
                else:
                    reply_audio_only = '* [**Audio only**](' + audio_url + ')'

                download_path = DATA_PATH + 'downloaded/' + str(submission.id) + VIDEO_FORMAT
                upload_path = DATA_PATH + 'uploaded/' + str(submission.id) + '.txt'

                # Upload
                uploaded_url = upload(media_url, submission.url, download_path, upload_path)
                if uploaded_url:
                    # Create log file with uploaded link, named after the submission ID
                    create_uploaded_log(upload_path, uploaded_url)
                    try:
                        reply_audio = "* [**Video with sound**](" + uploaded_url + ")"
                        reply = reply_audio + '\n\n' + reply_no_audio + '\n\n' + reply_audio_only
                        header = "#Downloadable links:\n\n"
                    except Exception as e:
                        print(e)

            reply = header + reply + ANNOUNCEMENT

            reply_to_user(item, reply, reddit, author)

        time.sleep(2)


def upload_pomf(file_path, site):
    if site == 'catbox':
        files = {
            'reqtype': (None, 'fileupload'),
            'fileToUpload': (file_path, open(file_path, 'rb')),
        }
        response = requests.post('https://catbox.moe/user/api.php', files=files)
        return response.text

    elif site == 'mixtape':
        host = pomf.get_host('mixtape')
        ret = host.upload(open(file_path, 'rb'))
        return ret['url']


def download(download_url, download_path):

    try:
        ydl_opts = {
            'outtmpl': download_path,
            'max_filesize': MAX_FILESIZE,
            'ratelimit': RATELIMIT,
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([download_url])
        return download_path

    except Exception as e:
        print('ERROR: Downloading failed.')
        print(e)
        return ""
    
    
# Authenticate via praw.ini file, look at praw documentation for more info
def authenticate():
    print('Authenticating...\n')
    reddit = praw.Reddit('vreddit', user_agent='vreddit')
    print('Authenticated as {}\n'.format(reddit.user.me()))
    return reddit


# Upload Video via vredd.it
def upload_via_vreddit(url):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(chrome_options=options)
    webpage_url = 'https://vredd.it'
    driver.get(webpage_url)

    url_box = driver.find_element_by_id('r_url')

    url_box.send_keys(url)

    login_button = driver.find_element_by_id('submit_url')
    login_button.click()

    counter = 0
    while counter < 100:
        try:
            driver.find_element_by_xpath("//*[text()='Play Video']")
            break
        except:
            counter += 1
            continue
    uploaded_url = driver.find_element_by_class_name('btn').get_attribute('href')
    driver.quit()
    return uploaded_url


def check_url_valid(url):
    try:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        urllib.request.urlopen(req, cafile=certifi.where())
        return True
    except:
        return False


def has_audio(url):
    # Workaround to check if v.redd.it link has audio
    try:
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req)
        resp.read()
        return True
    except:
        return False


def create_uploaded_log(upload_path, uploaded_url):
    try:
        print('Creating txt file.')
        f = open(upload_path, "w+")
        f.write(uploaded_url)
        f.close()
    except Exception as e:
        print(e)
        print("ERROR: Can't create txt file.")


def reply_to_user(item, reply, reddit, user):
    print('Replying... \n')
    try:
        item.reply(reply + FOOTER)
        item.mark_read()

    # Send PM if replying went wrong (Should only happen if the bot is banned)
    except Exception as e:
        print(e)
        try:
            pm = reply + FOOTER
            subject = "I couldn't reply to your comment so you get a PM instead :)"
            print('Can\'t comment, probably banned. Replying per PM.')
            reddit.redditor(user).message(subject, pm)
            item.mark_read()
        except Exception as f:
            print(f)


def is_url_valid(url):
    req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        urllib.request.urlopen(req, cafile=certifi.where())
    except Exception as e:
        return False
    else:
        return True


def create_media_url(submission, reddit):
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
    link = re.sub('DASH.*', '', url)
    s = reddit.submission(url=requests.get(link).url)
    return s


def type_of_item(item):
    body = str(item.body)
    match_text = re.search(r"(?i)" + BOT_NAME, body)
    match_link = re.search(
        r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)", body)

    if isinstance(item, Comment) and match_text:
        return "comment"

    elif isinstance(item, Message) and match_link:
        return match_link[0]

    return ""


def uploaded_log_exists(upload_path):

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


def upload(media_url, download_url, download_path, upload_path):
    # Check if already uploaded before
    uploaded_url = uploaded_log_exists(upload_path)
    if uploaded_url:
        return uploaded_url

    try:
        uploaded_url = upload_via_vreddit(media_url)
        # Sometimes vredd.it returns invalid url
        if is_url_valid(uploaded_url):
            return uploaded_url

    except Exception as e:
        print(e)

    print("Couldn't upload to https://vredd.it, downloading..")
    try:
        download_path = download(download_url, download_path)
    except:
        return ""

    try:
        uploaded_url = upload_pomf(download_path, 'catbox')
    except:
        try:
            uploaded_url = upload_pomf(download_path, 'mixtape')
        except Exception as e:
            print(e)
            print("Couldn't upload")
            return ""

    os.remove(download_path)
    return uploaded_url


if __name__ == '__main__':
    main()

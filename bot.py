
#!/usr/bin/env python3
#############################################################################
## Reddit Bot that provides downloadable links for v.redd.it videos (Audio)##
#############################################################################

import praw
import time
import re
import sys
import random
import os.path
import os
import smtplib
from selenium import webdriver
import urllib.request, urllib.error
import certifi
from urllib.request import Request, urlopen
from pyvirtualdisplay import Display
import youtube_dl
import pomf
import requests
from praw.models import Comment
from praw.models import Message
import sqlite3
display = Display(visible=0, size=(800, 600))
display.start()


#GLOBAL VARIABLES
npSubs = 'furry_irl', 'pcmasterrace'
gifSubs = 'gifsthatkeepongiving'
donate = 'https://www.reddit.com/r/vreddit_bot/wiki/index'
botPath = '/home/pi/bots/vreddit/'
format = '.mp4'
commentedPath = botPath + 'commented.txt'
blacklistSubs = ['The_Donald']
blacklistUsers = ['cyXie', 'airboy1021', 'null']

#Upload on catbox.moe or mixtape.moe
def uploadPomf(filePath, site):
    if site == 'catbox':
        files = {
            'reqtype': (None, 'fileupload'),
            'fileToUpload': (filePath, open(filePath, 'rb')),
        }

        response = requests.post('https://catbox.moe/user/api.php', files=files)
        return response.text

    elif site == 'mixtape':
        host = pomf.get_host('mixtape')
        ret = host.upload(open(filePath, 'rb'))
        return ret['url']
        # {'hash': 'f6bb5ef07fe63759ecfac1c81193c5912b96c45b', 'name': 'hearts.png', 'url': 'https://my.mixtape.moe/hsoali.png', 'size': 25553}


def download(downloadedPath,submissionURL):
        try:
            ydl_opts = {
            'outtmpl': downloadedPath,
            #'format': 'bestvideo',        #uncomment for video without audio only, see youtube-dl documentation
            'max_filesize': int('200000000'),
            'ratelimit': 2000000,
            }
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([submissionURL])
            return True

        except Exception as e:
            print('ERROR: Downloading failed.')
            print(e)
            return False


#Authenticate via praw.ini file, look at praw documentation for more info
def authenticate():
    print('Authenticating...\n')
    reddit = praw.Reddit('vreddit', user_agent = 'vreddit')
    print('Authenticated as {}\n'.format(reddit.user.me()))
    return reddit

# Upload Video via vreddi.it
def uploadVreddit(url):

    driver = webdriver.Chrome('/usr/lib/chromium-browser/chromedriver')
    webpage_url = 'https://vredd.it'
    driver.get(webpage_url)

    urlBox = driver.find_element_by_id('r_url')

    urlBox.send_keys(url)

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
    uploadedURL = driver.find_element_by_class_name('btn').get_attribute('href')
    driver.quit()
    return uploadedURL


#############
## RUN BOT ##
#############

def run_bot(reddit):
    #Search mentions in inbox
    inbox = list(reddit.inbox.unread(limit = 10))
    inbox.reverse()
    for item in inbox:
        s = ''
        matchLink = False
        body = str(item.body)
        author = str(item.author)
        matchText = re.search(r"(?i)u/vreddit_bot", body)
        footer = ("  \n ***  \n ^^I\'m&#32;a&#32;Bot&#32;*bleep*&#32;*bloop*&#32;|&#32;[**Contact**](https://np.reddit.com/message/compose?to=/u/Synapsensalat)&#32;|&#32;[**Info**](https://np.reddit.com/r/vreddit_bot/comments/9h41sx/info)&#32;|&#32;[**Donate**](https://np.reddit.com/r/vreddit_bot/wiki/index)")

        if isinstance(item, Comment) and matchText:
            mention = item
            s = item.submission
            if str(mention.subreddit) in npSubs:
                footer = ''
        elif isinstance(item, Message):
            message = item
            matchLink = re.search(r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)", body)

        reply = ''
        vredditSite = False
        uploadedURL = ''
        replyWithAudio = False
        createTxtFile = False

        try:
            if matchLink:
                link = re.sub('DASH.*', '', matchLink[0])
                s = reddit.submission(url=requests.get(link).url)

            submissionURL = s.url
            submissionID = s.id
            blacklisted = s.subreddit in blacklistSubs or author in blacklistUsers

            matchVreddit = 'v.redd.it' in submissionURL
        except Exception as e:
            matchVreddit = False


        if matchVreddit and (matchText or matchLink) and not blacklisted:
            #Check if the file was downloaded or uploaded before
            downloadedPath = botPath + 'downloaded/' + str(submissionID) + format
            uploadedPath = botPath + 'uploaded/' + str(submissionID) + '.txt'
            downloadedFileExists = os.path.exists(downloadedPath)
            uploadedLogExists = os.path.exists(uploadedPath)

            #Check if file has already been uploaded (if the .txt file with the link was generated before, to avoid uploading the same video multiple times)
            if uploadedLogExists:
                try:
                    with open(uploadedPath, 'r') as content_file:
                        uploadedURL = content_file.read()
                        uploadedTxt = True

                except Exception as e:
                    print(e)
                    print("Couldn't get URL, continuing..")
            else:
                uploadedTxt = False

            #Generate downloadable v.redd.it URL
            try:
                mediaURL = s.media['reddit_video']['fallback_url']
                mediaURL = str(mediaURL)
                audioURL = mediaURL.rpartition('/')[0] + '/audio'
                # vreddit = True
            except Exception as e:
                try:
                    crosspostID = s.crosspost_parent.split('_')[1]
                    s = reddit.submission(crosspostID)
                    mediaURL = s.media['reddit_video']['fallback_url']
                    mediaURL = str(mediaURL)
                    audioURL = mediaURL.rpartition('/')[0] + '/audio'
                except Exception as f:
                    continue

             #Workaround to check if v.redd.it link has audio
            try:
                req = urllib.request.Request(audioURL)
                resp = urllib.request.urlopen(req)
                respData = resp.read()
                hasAudio= True
            except:
                hasAudio= False

            if not uploadedTxt and hasAudio:
                try:
                    uploadedURL = uploadVreddit(mediaURL)

                    req = Request(uploadedURL, headers={'User-Agent': 'Mozilla/5.0'})
                    try:
                        conn = urllib.request.urlopen(req, cafile=certifi.where())
                    except urllib.error.HTTPError as e:
                        # Return code error (e.g. 404, 501, ...)
                        # ...
                        print('HTTPError: {}'.format(e.code))
                    except urllib.error.URLError as e:
                        # Not an HTTP-specific error (e.g. connection refused)
                        # ...
                        print('URLError: {}'.format(e.reason))
                    else:
                        # 200
                        vredditSite = True
                        createTxtFile = True
                        replyWithAudio = True

                except Exception as e:
                    print("Couldn't upload: ")
                    vredditSite = False
                    print(e)

                if not vredditSite:
                    print("vredd.it didn't work, downloading..")
                    downloaded = download(downloadedPath, submissionURL)
                    if downloaded:
                        try:
                            uploadedURL = uploadPomf(downloadedPath, 'catbox')
                            replyWithAudio = True
                            createTxtFile = True
                            os.remove(downloadedPath)
                        except:
                            try:
                                uploadedURL = uploadPomf(downloadedPath, 'mixtape')
                                replyWithAudio = True
                                createTxtFile = True
                                os.remove(downloadedPath)
                            except:
                                replyWithAudio = False

                    else:
                        replyWithAudio = False

            elif not hasAudio:
                replyWithAudio = False
            else:
                replyWithAudio = True


            replyAudio = "* [**Video with sound**]("+ uploadedURL + ")"
            replyNoAudio = '* [**GIF**](' + mediaURL + ')'
            replyAudioOnly = '* [**Audio only**](' + audioURL + ')'

            if replyWithAudio:
                reply = replyAudio + '\n\n' + replyNoAudio + '\n\n' + replyAudioOnly
            else:
                reply = replyNoAudio

            announcement = "\n\nUse your mobile browser if your app has problems opening my links."
            if matchText:
                announcementPM = "\n\nIf you don't want to mention my name you can also send me a private message (chat messages don't work, sorry) containing the link."
                announcement = random.choice([announcement,announcementPM])
            reply = "#Downloadable links:\n\n" + reply + announcement

            print('Replying... \n')
            try:
                item.reply(reply + footer)

            #Send PM if replying went wrong (Should only happen if the bot is banned)
            except:
                sub = str(mention.subreddit)
                pm = reply + footer
                subject = 'I\'m probably banned in r/' + sub + ', so you get a PM instead ;)'
                print('Can\'t comment, probably banned. Replying per PM.')
                reddit.redditor(author).message(subject, pm)


            item.mark_read()

            #Create .txt file with uploaded link, named after the submission ID
            if createTxtFile:
                try:
                    print('Creating txt file.')
                    f = open(uploadedPath,"w+")
                    f.write(uploadedURL)
                    f.close()
                except Exception as e:
                    print(e)
                    print("ERROR: Can't create txt file.")


    time.sleep(2)


def main():
    reddit = authenticate()
    while True:
        run_bot(reddit)



if __name__ == '__main__':
        main()

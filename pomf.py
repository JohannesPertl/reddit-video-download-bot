"""
Pomf.se uploader tool writen in Python
for python 3.5+. 
This tool was made by Cerulean. If you wish to know
more or see other utils by me: 
https://github.com/AggressivelyMeows/
I can be found on Discord at Cerulean#7014
My email is cerulean.connor@gmail.com
"""

import asyncio
import requests
import aiohttp
import functools

try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    # asyncio allows us to change
    # the event loop used.
    # if UVLOOP is avalible, lets use it

    USING_UVLOOP = True
except ImportError:
    # no UVLOOP
    USING_UVLOOP = False


class Host():
    def __init__(self, name, url):
        self.name = name
        self.url = url
        
    def upload_url(self):
        return self.url + '/upload.php'

    def upload(self, file):
        return uploader.upload(self, file)

    def upload_async(self, file):
        return uploader.upload_async(self, file)


class Uploader():
    def __init__(self, session=None, loop=None):
        self.hosts = {}

        self.loop = loop if loop else asyncio.get_event_loop()
        self.http_session = session

    def get_host(self, host_name):
        try:
            return self.hosts[host_name]
        except:
            raise ValueError('Host name does not exist')

    def register_host(self, host_name, host_url):
        # wrap the host details into a host
        # object. This object allows you to 
        # upload directly without having to
        # pass a host object to the uploader

        host = Host(host_name, host_url)
        self.hosts[host_name] = host
        return host

    def get_file(self, filename):
        return open(filename, 'rb')

    def upload(self, host, file):
        
        if isinstance(host, str):
            # not a host object, try finding by
            # str in the self.hosts dict
            try:
                host = self.hosts[host]
            except:
                raise ValueError('Host does not exist')

        # for this non-async version, we use requests

        # check if the file being uploaded
        # is a file object or not
        if hasattr(file, 'seek'):
            file.seek(0)
            file_object = file
            # Find out the file type.
            # If its a file-like object seek the object
            # If not, read the file location
        else:
            file_object = self.get_file(file)

        # now we upload
        response = requests.post(host.upload_url(),
                                 files={'files[]': file_object})

        # any errors that happen while unloading from
        # the uploader will be thrown to the
        # end user.
        return response.json()['files'][0]

    async def upload_async(self, host, file):
        # asyncio based upload 
        # for concurrency and 
        # faster stuff

        try:
            self.http_session
        except:
            # no http session
            self.http_session = aiohttp.ClientSession()

        # check if the file being uploaded
        # is a file object or not
        if hasattr(file, 'seek'):
            file.seek(0)
            file_object = file
            # Find out the file type.
            # If its a file-like object seek the object
            # If not, read the file location
        else:
            file_object = self.get_file(file)
        
        #async with self.http_session.post(host.upload_url(),
        #                                  data={'files[]':file_object}) as resp:
        #    print(await resp.json())

        # Look, as far as i know, AIOHTTP cannot upload multipart files in
        # the way that POMF that allows. 
        # If anyone wants to help me out with this, im always open to 
        # any help!

        prepared_request = functools.partial(requests.post,
                                             host.upload_url(),
                                             files={'files[]': file_object})

        response = await self.loop.run_in_executor(None, prepared_request)
        return response.json()['files'][0]


def add_host(host_name, host_url):
    return uploader.register_host(host_name,
                                  host_url)


def get_host(host_name):
    """
    Get a POMF host.
    Returns NONE if no hosts were found
    """
    try:
        return uploader.hosts[host_name]
    except KeyError:
        return None

uploader = Uploader()

# add hosts
add_host('mixtape', 'https://mixtape.moe')
add_host('safe', 'https://safe.moe/')
add_host('void', 'https://void.cat/')
# pre-built in hosts
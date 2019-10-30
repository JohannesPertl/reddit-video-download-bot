import os
import time
import requests
from concurrent.futures import ThreadPoolExecutor

# Constants
PATH = "/home/pi/bots/vreddit/data/ripsave/"
HOURS_TO_KEEP_ALIVE = 6


def update_ripsave_links():
    """Updates previously posted ripsave links. To keep them alive, run this script every few minutes"""
    with ThreadPoolExecutor() as executor:
        for filename in os.listdir(PATH):
            file_path = PATH + filename
            executor.submit(update_file, file_path)


def update_file(file_path):
    seconds = file_age(file_path)
    minutes = int(seconds) / 60
    hours = minutes / 60

    if hours > HOURS_TO_KEEP_ALIVE:
        # Stop keeping link online
        os.remove(file_path)

    else:
        # Update link
        with open(file_path, 'r') as file:
            link = file.read()
            requests.get(link)


def file_age(file_path):
    return time.time() - os.path.getmtime(file_path)


if __name__ == "__main__":
    update_ripsave_links()

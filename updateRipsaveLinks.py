import os
import time
import requests

now = time.time()
path = '/home/pi/bots/vreddit/data/ripsave/'

hours_to_keep_alive = 6


def keep_ripsave_links_alive():
    while True:
        for filename in os.listdir(path):
            file_path = path + filename
            creation_date = os.path.getmtime(file_path)
            age_in_hours = (now-creation_date)/3600

            if age_in_hours > hours_to_keep_alive:
                os.remove(file_path)
            else:
                update_link_in_file(file_path)

        time.sleep(5)


def update_link_in_file(file_path):
    with open(file_path, 'r') as file:
        link = file.read()
        requests.get(link)


if __name__ == "__main__":
    keep_ripsave_links_alive()

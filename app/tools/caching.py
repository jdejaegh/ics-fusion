import json
import os
import threading
import time
from hashlib import sha256

import arrow
import requests
from ics import Calendar


def cache(entry: dict) -> None:
    if not os.path.isdir('cache'):
        os.mkdir('cache')

    url = entry['url']
    path = "cache/" + sha256(url.encode()).hexdigest() + ".ics"

    r = requests.get(entry["url"], allow_redirects=True)
    if "encoding" in entry:
        cal = Calendar(imports=r.content.decode(encoding=entry["encoding"]))
    else:
        cal = Calendar(imports=r.content.decode())

    cal = horodate(cal, 'Cached at')
    open(path, 'w').writelines(cal)


def get_from_cache(entry: dict) -> Calendar:
    url = entry['url']
    path = "cache/" + sha256(url.encode()).hexdigest() + ".ics"
    if not os.path.isfile(path):
        print("Not cached")
        raise FileNotFoundError("The calendar is not cached")

    with open(path, 'r') as file:
        data = file.read()

    return Calendar(imports=data)


def load_cal(entry: dict) -> Calendar:
    if "cache" in entry and entry["cache"]:
        print("Getting", entry["name"], "from cache")
        return get_from_cache(entry)

    else:
        print("Getting", entry["name"], "from remote")
        r = requests.get(entry["url"], allow_redirects=True)
        if "encoding" in entry:
            cal = Calendar(imports=r.content.decode(encoding=entry["encoding"]))
        else:
            cal = Calendar(imports=r.content.decode())

        cal = horodate(cal, 'Downloaded at')
        return cal


def horodate(cal: Calendar, prefix='') -> Calendar:
    now = arrow.now().format("YYYY-MM-DD HH:mm:ss")
    for event in cal.events:
        event.description = event.description + '\n' + prefix + ' ' + now \
            if event.description is not None else prefix + ' ' + now

    return cal


def background_cache() -> None:
    path = "config"
    files = [os.path.join(path, f) for f in os.listdir(path)
             if os.path.isfile(os.path.join(path, f)) and f.endswith('.json')]

    for file in files:
        with open(file, 'r') as config_file:
            config = json.loads(config_file.read())

        for entry in config:
            if 'cache' in entry and entry['cache']:
                cache(entry)
    print('Cache renewed', arrow.now().format("YYYY-MM-DD HH:mm:ss"))


class CacheThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        print("Starting cache process")
        while True:
            background_cache()
            time.sleep(10*60)

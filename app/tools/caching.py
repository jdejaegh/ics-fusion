import json
import os
import sched
import threading
import time
from hashlib import sha256

import arrow
import requests
from ics import Calendar


def cache(entry: dict, scheduler: sched.scheduler = None) -> None:
    """Cache an .ics feed in the app/cache directory.
    Different entries with the same URL will be cached in the same file.
    The cached calendar contains a new line in the description with the current time when cached prefixed by the
    'Cached at' mention



    :param entry: representation of the entry to cache.  This is the Python representation of the corresponding entry
    in the config file
    :type entry: dict

    :param scheduler: scheduler used to relaunch the caching task in the future.  If not scheduler is specified,
    the task will not be relaunched
    :type scheduler: sched.scheduler
    """

    if not os.path.isdir('app/cache'):
        os.mkdir('app/cache')

    url = entry['url']
    path = "app/cache/" + sha256(url.encode()).hexdigest() + ".ics"

    try:
        r = requests.get(entry["url"], allow_redirects=True)
    except Exception as e:
        print(arrow.now().format("YYYY-MM-DD HH:mm:ss"), "Could not cache", entry)
        print(e)
    else:
        if "encoding" in entry:
            cal = Calendar(imports=r.content.decode(encoding=entry["encoding"]))
        else:
            cal = Calendar(imports=r.content.decode())

        cal = horodate(cal, 'Cached at')
        open(path, 'w').writelines(cal)
        print(arrow.now().format("YYYY-MM-DD HH:mm:ss"), "Cached", entry['name'])
    finally:
        if scheduler is not None:
            delay = entry['cache'] if entry['cache'] > 0 else 10
            delay *= 60
            scheduler.enter(delay=delay, priority=1, action=cache, argument=(entry, scheduler))


def get_from_cache(entry: dict) -> Calendar:
    """Retrieve the entry from cache.  If the entry is not found, an exception is raised


    :param entry: representation of the entry to cache.  This is the Python representation of the corresponding entry
    in the config file
    :type entry: dict


    :return: the corresponding calendar in cache
    :rtype: Calendar


    :raises FileNotfoundError: if the entry has not been cached before
    """

    url = entry['url']
    path = "app/cache/" + sha256(url.encode()).hexdigest() + ".ics"
    if not os.path.isfile(path):
        print("Not cached")
        raise FileNotFoundError("The calendar is not cached")

    with open(path, 'r') as file:
        data = file.read()

    return Calendar(imports=data)


def load_cal(entry: dict) -> Calendar:
    """Load the calendar from the cache or from remote according to the entry.  If the calendar is supposed to be in
    cached but could not be found in cache, an error is thrown


    :param entry: representation of the entry to cache.  This is the Python representation of the corresponding entry
    in the config file
    :type entry: dict


    :return: the calendar corresponding to the entry
    :rtype: Calendar


    :raises FileNotfoundError: if the entry was supposed to be cached but has not been cached before
    """

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
    """Add a new line at the end of the description of every event in the calendar with the current time prefixed by
    the prefix parameter and a space
    The date is added with the following format: YYYY-MM-DD HH:mm:ss


    :param cal: calendar to process
    :type cal: Calendar

    :param prefix: the prefix to add in front of the date
    :type prefix: str


    :return: the modified calendar
    :rtype: Calendar
    """
    now = arrow.now().format("YYYY-MM-DD HH:mm:ss")
    for event in cal.events:
        event.description = event.description + '\n' + prefix + ' ' + now \
            if event.description is not None else prefix + ' ' + now

    return cal


def start_scheduler(scheduler: sched.scheduler) -> None:
    """Start the caching of every config file found in the app/config directory


    :param scheduler: scheduler object to use to schedule the caching
    :type scheduler: sched.scheduler
    """

    path = "app/config"
    files = [os.path.join(path, f) for f in os.listdir(path)
             if os.path.isfile(os.path.join(path, f)) and f.endswith('.json')]

    for file in files:
        with open(file, 'r') as config_file:
            config = json.loads(config_file.read())

        for entry in config:
            if 'cache' in entry:
                scheduler.enter(delay=0, priority=1, action=cache, argument=(entry, scheduler))

    scheduler.run()


class CacheThread(threading.Thread):
    """Child class of the threading.Thread class to run the caching process every 10 minutes
    """

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        print("Starting cache process")
        start_scheduler(sched.scheduler(time.time, time.sleep))

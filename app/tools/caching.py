import json
import os
import sched
import threading
import time
from hashlib import sha256

import traceback
import arrow
import requests
from ics import Calendar
from tatsu.exceptions import FailedParse
from tools.tools import horodate, process


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

    try:
        if not os.path.isdir('app/cache'):
            os.mkdir('app/cache')

        url = entry['url']
        path = "app/cache/" + sha256(url.encode()).hexdigest() + ".ics"

        r = requests.get(entry["url"], allow_redirects=True)

        if "encoding" in entry:
            cal = Calendar(imports=r.content.decode(encoding=entry["encoding"]))
        else:
            cal = Calendar(imports=r.content.decode())

        cal = horodate(cal, 'Cached at')
        open(path, 'w').writelines(cal)
        print(arrow.now().format("YYYY-MM-DD HH:mm:ss"), "Cached", entry['name'])

    except FailedParse:
        print("Could not parse", entry['name'])

    # Save stack trace when an unknown error occurs
    except Exception as e:
        with open("error " + arrow.now().format("YYYY-MM-DD HH:mm:ss")+".txt", 'w') as file:
            file.write(arrow.now().format("YYYY-MM-DD HH:mm:ss") + "\nCould not cache : " + str(entry))
            file.write(str(e))
            file.write(str(traceback.format_exc()))
    finally:
        if scheduler is not None:
            delay = entry['cache'] if entry['cache'] > 0 else 10
            delay *= 60
            scheduler.enter(delay=delay, priority=1, action=cache, argument=(entry, scheduler))


def precompute(config: str, scheduler: sched.scheduler = None) -> None:
    """Precompute a configuration file result to serve it faster when it is requested.  This function
    should be used with a scheduler to be repeated over time.

    :param config: name of the configuration file to precompute the result for
    :type config: str

    scheduler used to relaunch the precomputing task in the future.  If not scheduler is specified,
    the task will not be relaunched
    :type scheduler: sched.scheduler
    """
    try:
        cal = process(os.path.basename(config), False)
        path = "app/cache/" + os.path.basename(config).rstrip('.json') + ".ics"
        open(path, 'w').writelines(cal)
        print(arrow.now().format("YYYY-MM-DD HH:mm:ss"), "Precomputed", os.path.basename(config).rstrip('.json'))

    except Exception as e:
        with open("error " + arrow.now().format("YYYY-MM-DD HH:mm:ss")+".txt", 'w') as file:
            file.write(arrow.now().format("YYYY-MM-DD HH:mm:ss") + "\nCould not precompute : " + str(config))
            file.write(str(e))
            file.write(str(traceback.format_exc()))
    finally:
        if scheduler is not None:
            delay = get_min_cache(config)
            delay *= 60
            scheduler.enter(delay=delay, priority=1, action=precompute, argument=(config, scheduler))


def get_min_cache(path: str) -> float:
    """Get the minimum caching time of all the entries in a config file.

    :param path: path of the config file to use
    :type path: str

    :return: float number representing the smallest caching time.
    """
    result = float('inf')

    with open(path, 'r') as config_file:
        file = json.loads(config_file.read())

    for entry in file:
        if 'cache' in entry and entry['cache'] < result:
            result = entry['cache']

    return result


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

        if get_min_cache(file) < float('inf'):
            scheduler.enter(delay=get_min_cache(file)*60, priority=1, action=precompute, argument=(file, scheduler))

    scheduler.run()


class CacheThread(threading.Thread):
    """Child class of the threading.Thread class to run the caching process every 10 minutes
    """

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        print("Starting cache process")
        start_scheduler(sched.scheduler(time.time, time.sleep))

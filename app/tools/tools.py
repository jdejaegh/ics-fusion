"""This module provides methods to combines multiples .ics feeds into a single object.

The methods allow to filter the events to keep in the final object and to modify the remaining event
according to a configuration file.

The JSON configuration file used in this module has the following structure

[
    {
        "url":"str",
        "name":"str",
        "encoding":"str",
        "filters":{
            "name":{
                "exclude":"RegEx",
                "includeOnly":"RegEx",
                "ignoreCase":true
            },
            "description":{
                "exclude":"RegEx",
                "includeOnly":"RegEx",
                "ignoreCase":true
            }
        },
        "modify":{
            "time":{
                "shift":{
                    "year":0,
                    "month":0,
                    "day":0,
                    "hour":0,
                    "minute":0
                }
            },
            "name":{
                "addPrefix":"str",
                "addSuffix":"str",
                "redactAs":"str"
            },
            "description":{
                "addPrefix":"str",
                "addSuffix":"str",
                "redactAs":"str"
            },
            "location":{
                "addPrefix":"str",
                "addSuffix":"str",
                "redactAs":"str"
            }
        }
    }
]

Only the url and the name field are mandatory.
- url: specify the url to find the calendar
- name: name to identify the calendar
- encoding: specify the encoding to use

- filters: structure defining the filters to apply to the calendar
- name: filters to apply to the name field of the events
- description: filters to apply to the name field of the events
- exclude: RegEx to describe the events to exclude - cannot be specified with includeOnly
- includeOnly: RegEx to describe the events to include - cannot be specified with exclude
- ignoreCase: if true the RegEx will ignore the case of the field

- modify: structure defining the modifications to the events of the calendar
- time: describe the modifications to apply to the timing of the event
- shift: shift the event of a certain amount of time
- year, month, day, hour, minute: amount of time to add to the events
- name: modifications to apply to the name of the events
- description: modifications to apply to the description of the events
- location: modification to apply to the location of the events
- addPrefix: string to add at the beginning of the field
- addSuffix: string to add at the end of the field
- redactAs: string to replace the field with
"""

import json
import re
import arrow
import os
from hashlib import sha256
from typing import List

import requests
from ics import Calendar
from pathvalidate import sanitize_filename


def filtering(cal: Calendar, filters: dict, field_name: str) -> Calendar:
    """Filter the event of a calendar according to the filters and the field_name


    :param cal: the calendar to apply filters to
    :type cal: Calendar

    :param filters: the filters to apply to the calendar
    :type filters: dict

    :param field_name: the of the field in the filters to consider
    :type field_name: str


    :return: the modified cal argument after filtering out the events
    :rtype: Calendar


    :raises SyntaxError: if both exclude and includeOnly are specified in the filters
    """

    if field_name in filters:
        field = filters[field_name]

        if ("exclude" in field) and ("includeOnly" in field):
            raise SyntaxError("Cannot specify both exclude and includeOnly")

        if ("exclude" not in field) and ("includeOnly" not in field):
            return cal

        new = Calendar()

        ignore_case = True if ("ignoreCase" in field and field["ignoreCase"]) else False

        if "exclude" in field:
            p = re.compile(field["exclude"], re.IGNORECASE | re.DOTALL) \
                if ignore_case else re.compile(field["exclude"], re.DOTALL)

            for event in cal.events:
                if event.name is None or (field_name == "name" and p.match(event.name) is None):
                    new.events.add(event)
                elif event.description is None or (field_name == "description" and p.match(event.description) is None):
                    new.events.add(event)

        if "includeOnly" in field:
            p = re.compile(field["includeOnly"], re.IGNORECASE | re.DOTALL) \
                if ignore_case else re.compile(field["includeOnly"], re.DOTALL)

            for event in cal.events:
                if field_name == "name" and event.name is not None and p.match(event.name) is not None:
                    new.events.add(event)
                elif field_name == "description" and event.description is not None \
                        and p.match(event.description) is not None:
                    new.events.add(event)

        cal = new
        return cal

    else:
        return cal


def apply_filters(cal: Calendar, filters: dict) -> Calendar:
    """Apply all the filters to a calendar and returns the resulting calendar


    :param cal: the calendar to apply filters to
    :type cal: Calendar

    :param filters: the filters to apply
    :type filters: dict


    :return: the modified cal parameter to satisfy the filters
    :rtype: Calendar

    :raises SyntaxError:  if both exclude and includeOnly are specified for the same field in the filters
    """

    cal = filtering(cal, filters, "name")
    cal = filtering(cal, filters, "description")

    return cal


def modify_time(cal: Calendar, modify: dict) -> Calendar:
    """Modify the time of all the events in a calendar as specified in the modify structure


    :param cal: the calendar where it is needed to modify the time of the events
    :type cal: Calendar

    :param modify: the structure defining how to modify the time
    :type modify: dict


    :return: the modified cal parameter
    :rtype: Calendar
    """

    if ("time" in modify) and ("shift" in modify["time"]):
        shift = modify["time"]["shift"]

        year = 0 if not ("year" in shift) else shift["year"]
        month = 0 if not ("month" in shift) else shift["month"]
        day = 0 if not ("day" in shift) else shift["day"]
        hour = 0 if not ("hour" in shift) else shift["hour"]
        minute = 0 if not ("minute" in shift) else shift["minute"]

        shift_minutes = (year * 365 * 24 * 60) + (month * 30 * 24 * 60) + (day * 24 * 60) + (hour * 60) + minute
        
        if shift_minutes > 0:
            for event in cal.events:
                event.end = event.end.shift(minutes=shift_minutes)
                event.begin = event.begin.shift(minutes=shift_minutes)
        elif shift_minutes < 0:
            for event in cal.events:
                event.begin = event.begin.shift(minutes=shift_minutes)
                event.end = event.end.shift(minutes=shift_minutes)

    return cal


def modify_text(cal: Calendar, modify: dict, field_name: str) -> Calendar:
    """Modify one text field (name, location, description) of all the events in the cal parameter
    according to the modify structure and the field_name


    :param cal: the calendar where it is needed to modify the text field
    :type cal: Calendar

    :param modify: the structure defining how to modify the time
    :type modify: dict

    :param field_name: the name of the field to modify
    :type field_name: str


    :return: the modified cal parameter
    :rtype: Calendar
    """

    if field_name in modify:
        change = modify[field_name]

        if "addPrefix" in change:
            for event in cal.events:

                if field_name == "name":
                    event.name = change["addPrefix"] + event.name \
                        if event.name is not None else change["addPrefix"]

                elif field_name == "description":
                    event.description = change["addPrefix"] + event.description \
                        if event.description is not None else change["addPrefix"]

                elif field_name == "location":
                    event.location = change["addPrefix"] + event.location \
                        if event.location is not None else change["addPrefix"]

        if "addSuffix" in change:
            for event in cal.events:

                if field_name == "name":
                    event.name = event.name + change["addSuffix"] \
                        if event.name is not None else change["addSuffix"]

                elif field_name == "description":
                    event.description = event.description + change["addSuffix"] \
                        if event.description is not None else change["addSuffix"]

                elif field_name == "location":
                    event.location = event.location + change["addSuffix"] \
                        if event.location is not None else change["addSuffix"]
                        
        if "redactAs" in change:
            for event in cal.events:

                if field_name == "name":
                    event.name = change["redactAs"]

                elif field_name == "description":
                    event.description = change["redactAs"]

                elif field_name == "location":
                    event.location = change["redactAs"]

    return cal


def apply_modify(cal: Calendar, modify: dict) -> Calendar:
    """Apply all the needed modifications to a calendar and returns the resulting calendar


    :param cal: the calendar to apply modifications to
    :type cal: Calendar

    :param modify: the structure containing the modifications to apply
    :type modify: dict


    :return: the modified cal parameter
    :rtype: Calendar
    """

    cal = modify_time(cal, modify)
    cal = modify_text(cal, modify, "name")
    cal = modify_text(cal, modify, "description")
    cal = modify_text(cal, modify, "location")
    return cal


def merge(cals: List[Calendar]) -> Calendar:
    """Merge a list of calendars into a single calendar
    Only takes the event into account, not the tasks or the alarms


    :param cals: the list of calendars to merge
    :type cals: List[Calendar]


    :return: the calendar containing the union of the events contained in the cals list
    :rtype: Calendar


    :raises ValueError: if an element of the list is not a Calendar
    """

    result = Calendar()

    for cal in cals:
        if not isinstance(cal, Calendar):
            raise ValueError("All elements should be Calendar")
        result.events = result.events.union(cal.events)

    return result


def process(path: str, from_cache: bool = True) -> Calendar:
    """Open a config file from the specified path, download the calendars,
    apply the filters, modify and merge the calendars as specified in the config file


    :param from_cache:
    :param path: name of the file to open.  The file should be in the config/ folder
    :type path: str


    :return: the resulting calendar
    :rtype: Calendar
    """
    print("app/cache/" + sanitize_filename(path).rstrip(".json") + ".ics")
    if from_cache and os.path.isfile("app/cache/" + sanitize_filename(path).rstrip(".json") + ".ics"):
        with open("app/cache/" + sanitize_filename(path).rstrip(".json") + ".ics") as file:
            data = file.read()
        print("Serving precomputed file")
        return Calendar(imports=data)

    else:
        o = "app/config/" + sanitize_filename(path)
        print("Try to open " + o)
        file = open(o, "r")
        config = json.loads(file.read())
        file.close()

        data = []
        
    for entry in config:
        if "conf" in entry:
            if entry.get("extends", None) is not None:
                try:
                    o = "app/config/" + sanitize_filename(entry["extends"]) + ".json"
                    print("Try to open " + o)
                    file = open(o, "r")
                    baseConfig = json.loads(file.read())
                    file.close()
                    extendingConfig = config
                    try:
                        config = merge_json(baseConfig, extendingConfig)
                    except:
                        config = extendingConfig
                    
                except:
                    if entry.get("extendFail", "fail") == "fail":
                        raise FileNotFoundError("The calendar is not cached")
                    else:
                        pass
        

    for entry in config:
        if "conf" not in entry:
            cal = load_cal(entry)

            if "filters" in entry:
                cal = apply_filters(cal, entry["filters"])

            if "modify" in entry:
                cal = apply_modify(cal, entry["modify"])

            data.append(cal)

    return merge(data)


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
        try:
            return get_from_cache(entry)
        except FileNotFoundError:
            return Calendar()

    else:
        print("Getting", entry["name"], "from remote")
        r = requests.get(entry["url"], allow_redirects=True)
        if "encoding" in entry:
            cal = Calendar(imports=r.content.decode(encoding=entry["encoding"]))
        else:
            cal = Calendar(imports=r.content.decode())

        cal = horodate(cal, 'Event last fetched: ')
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

def merge_json(base, extension):
    """Merges two config files by updating the value of base with the values in extension.

    :param base: the base config file
    :type base: dict

    :param extension: the config file to merge with the base
    :type extension: dict

    :return: the merged config file
    :rtype: dict
    """

    new_json = base.copy()

    def update_json(base_set, updates):
        for key, value in updates.items():
            if not key == "conf":
                if isinstance(value, dict) and key in base_set and isinstance(base_set[key], dict):
                    update_json(base_set[key], value)
                else:
                    base_set[key] = value

    for base_dataset in new_json:
        if "conf" not in base_dataset:
            for ext_dataset in extension:
                if base_dataset.get("name") == ext_dataset.get("name"):
                    update_json(base_dataset, ext_dataset)

    return new_json

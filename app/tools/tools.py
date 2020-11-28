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
                "addSuffix":"str"
            },
            "description":{
                "addPrefix":"str",
                "addSuffix":"str"
            },
            "location":{
                "addPrefix":"str",
                "addSuffix":"str"
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
"""

import json
import re
from typing import List

from ics import Calendar
from pathvalidate import sanitize_filename
from tools.caching import load_cal


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

        for event in cal.events:
            event.end = event.end.shift(years=year, months=month, days=day, hours=hour, minutes=minute)
            event.begin = event.begin.shift(years=year, months=month, days=day, hours=hour, minutes=minute)

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


def process(path: str) -> Calendar:
    """Open a config file from the specified path, download the calendars,
    apply the filters, modify and merge the calendars as specified in the config file


    :param path: name of the file to open.  The file should be in the config/ folder
    :type path: str


    :return: the resulting calendar
    :rtype: Calendar
    """

    o = "app/config/" + sanitize_filename(path)
    print("Try to open " + o)
    file = open(o, "r")
    config = json.loads(file.read())
    file.close()

    data = []

    for entry in config:

        cal = load_cal(entry)

        if "filters" in entry:
            cal = apply_filters(cal, entry["filters"])

        if "modify" in entry:
            cal = apply_modify(cal, entry["modify"])

        data.append(cal)

    return merge(data)

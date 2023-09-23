# ICS Fusion  
Forked from [https://github.com/jdejaegh/ics-fusion](https://github.com/jdejaegh/ics-fusion)
## Introduction
ICS Fusion is a tool to merge multiple ics feed into a single ics calendar. Filters and modifications may be applied on the incoming feeds.  The resulting ics can be accessed via an HTTP endpoint.

## Installation
ICS Fusion is written in Python and using `Flask` to provide the HTTP endpoint.  Make sure to install all the modules listed in the `requirements.txt` file before launching the tool.

Launch the `app/server.py` file to start the application.

### Building the image
ICS Fusion can be built as a Docker image. To do so, type :

`docker build --tag ics-fusion:1.0 .`

in the main folder of Fusion ICS.

### Running the container
To run the container, type:

`docker run --publish PORT:8088 --detach --name ics --volume DIRECTORY:/usr/src/ics/app/config ics-fusion:1.0`

Where:
* `PORT` is the port you want to expose on your host machine.
* `DIRECTORY` is the path to your config directory.

## Configuration
To create a new feed in the application, create a file with the `.json` extension in the  `app/config` folder.  The name of the configuration file will be used to create a new endpoint to serve the feed.

The JSON configuration file should look like the following.

```json
[
    {
        "conf": true,
        "extends": "str",
        "extendFail": "str",
    },
    {
        "url":"str",
        "name":"str",
        "cache": 10,
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
```

Only the `url` and the `name` field are mandatory.  
- `url`: specify the url to find the calendar  
- `name`: name to identify the calendar
- `cache`: if present cache the remote calendar according to the interval set in minutes
- `encoding`: specify the encoding to use  
  

- `filters`: structure defining the filters to apply to the calendar  
- `name`: filters to apply to the name field of the events
- `description`: filters to apply to the name field of the events
- `exclude`: RegEx to describe the events to exclude - cannot be specified with includeOnly
- `includeOnly`: RegEx to describe the events to include - cannot be specified with exclude
- `ignoreCase`: if true the RegEx will ignore the case of the field  
  

- `modify`: structure defining the modifications to the events of the calendar
- `time`: describe the modifications to apply to the timing of the event
- `shift`: shift the event of a certain amount of time
- `year`, `month`, `day`, `hour`, `minute`: amount of time to add to the events
- `name`: modifications to apply to the name of the events
- `description`: modifications to apply to the description of the events
- `location`: modification to apply to the location of the events
- `addPrefix`: string to add at the beginning of the field
- `addSuffix`: string to add at the end of the field
- `redactAs`: Replaces the content of the field with the specified string
  
If multiple calendars are specified in the configuration list, their events will be merged in the resulting ics feed.
The first dataset with {"conf": "true",} specifies options that are globally applied to all calenders in the conf. Omit this set to disable. Options
- `extends`: string specifying the name (excluding .json) of another config file to extend.
- `extendFail`: string speciying the action to take if an extend fails, either "fail" or "ignore". Default is "fail".

## Usage
Once the config file is created, the corresponding HTTP endpoint is accessible.  For example, if the file `app/config/my-calendar.json` contains the configuration, the HTTP endpoint will be `http://localhost:8088/my-calendar`.

A config can extend another config file, to do this the extended config should contain begin with`{
        "conf": true,
        "extends": <name of calendar>,
        "extendFail": "fail",
    },`
For an extend to work calendars MUST share the same name between the configs
An extending config cannot remove data from a base calendar but can modify fields

## Limitations
Currently, the application only merges events of the ics feeds, the alarms and todos are not supported.  

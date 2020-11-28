from flask import Flask, make_response

from tools.caching import CacheThread
from tools.tools import *

app = Flask(__name__)


@app.route('/<calendar>')
def main(calendar):
    conf = calendar + ".json"

    print("Opening " + conf)

    try:
        result = str(process(conf))
        response = make_response(result, 200)
        response.headers["Content-Disposition"] = "attachment; filename=calendar.ics"
    except FileNotFoundError:
        response = make_response("Calendar not cached", 425)

    return response


thread = CacheThread()
thread.start()

app.run(host='0.0.0.0', port=8088)

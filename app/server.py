from app.tools.tools import *
from app.tools.caching import *
from flask import Flask, make_response

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


# TODO find better way to launch periodic caching
#   Maybe try with https://docs.python.org/3/library/sched.html
thread = CacheThread()
thread.start()
app.run(host='0.0.0.0', port=8088)
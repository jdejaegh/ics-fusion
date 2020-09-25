from tools.tools import *
from flask import Flask, make_response

app = Flask(__name__)


@app.route('/<calendar>')
def main(calendar):
    conf = calendar + ".json"

    print("Opening " + conf)

    result = str(process(conf))
    response = make_response(result, 200)
    response.headers["Content-Disposition"] = "attachment; filename=calendar.ics"
    return response


app.run(host='0.0.0.0', port=8088)

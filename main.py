# import datetime
# import functions_framework
# import time


# @functions_framework.http
# def copilotWaitSec(request):
#     """HTTP Cloud Function. 
#     functions-framework-python --target copilotWaitSec
#     http://localhost:8080?seconds=1 
#     Args:
#         request (flask.Request): The request object.
#         <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>
#     Returns:
#         The response text, or any set of values that can be turned into a
#         Response object using `make_response`
#         <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
#     """
#     request_json = request.get_json(silent=True)
#     request_args = request.args

#     if request_json and "seconds" in request_json:
#         seconds: float = float(request_json["seconds"])
#     elif request_args and "seconds" in request_args:
#         seconds: float = float(request_args["seconds"])
#     else:
#         seconds = 1
#     if seconds > 10 :
#         seconds = 10
#     time.sleep(seconds)
#     start_time: datetime.datetime = datetime.datetime.today()
#     finish_time: datetime.datetime = start_time + datetime.timedelta(seconds=seconds)
#     print(float("0.1"))

#     return {"finished": True, "start_time": start_time, "finish_time": finish_time}


import signal
import sys
from types import FrameType

from flask import Flask

from utils.logging import logger

app = Flask(__name__)


@app.route("/")
def copilotWaitSec() -> str:
    # Use basic logging with custom fields
    logger.info(logField="custom-entry", arbitraryField="custom-entry")

    # https://cloud.google.com/run/docs/logging#correlate-logs
    logger.info("Child logger with trace Id.")

    return "Hello, BUDDY AGAIN!"


def shutdown_handler(signal_int: int, frame: FrameType) -> None:
    logger.info(f"Caught Signal {signal.strsignal(signal_int)}")

    from utils.logging import flush

    flush()

    # Safely exit program
    sys.exit(0)


if __name__ == "__main__":
    # Running application locally, outside of a Google Cloud Environment

    # handles Ctrl-C termination
    signal.signal(signal.SIGINT, shutdown_handler)

    app.run(host="localhost", port=8080, debug=True)
else:
    # handles Cloud Run container termination
    signal.signal(signal.SIGTERM, shutdown_handler)

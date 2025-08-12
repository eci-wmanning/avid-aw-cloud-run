import datetime
import time


def copilotWaitSec(request):
    request_json = request.get_json(silent=True)
    request_args = request.args

    if request_json and "seconds" in request_json:
        seconds: float = float(request_json["seconds"])
    elif request_args and "seconds" in request_args:
        seconds: float = float(request_args["seconds"])
    else:
        seconds = 1
    if seconds > 10 :
        seconds = 10
    time.sleep(seconds)
    start_time: datetime.datetime = datetime.datetime.today()
    finish_time: datetime.datetime = start_time + datetime.timedelta(seconds=seconds)
    print(float("0.1"))

    return {"finished": True, "start_time": start_time, "finish_time": finish_time}

__all__ = ["copilotWaitSec"]
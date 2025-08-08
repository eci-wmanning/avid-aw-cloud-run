import datetime
import functions_framework
import time


@functions_framework.http
def copilotWaitSec(request):
    """HTTP Cloud Function. 
    functions-framework-python --target copilotWaitSec
    http://localhost:8080?seconds=1 
    Args:
        request (flask.Request): The request object.
        <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """
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


from re import sub
import functions_framework
import yaml


from markupsafe import escape

def getIntents(request):
    """HTTP Cloud Function. 
    Find PID on 8080: lsof -n -i4TCP:8080
    Terminate Process: kill -9 {{PID FROM ABOVE}}
    Navigate to DIR: cd GoogleCloudFunctions/TopTopicIntents
    Start Local: functions-framework-python --target getIntents
    In PostMan: http://localhost:8080
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

    selected = []
    copilot = "common"
    if request_args:
        env = request_args["env"] if "env" in request_args else "Dev"
        copilot = request_args["copilot"] if "copilot" in request_args else "common"
        subtopic = request_args["subtopic"] if "subtopic" in request_args else ""
        options_limit = int(request_args["limit"] if "limit" in request_args else 5)
        print(''.join(["Using COPILOT: ", copilot, " In ENV: ", env, "Selected SubTopic: ", subtopic]))
    with open("TopicIntents.yaml", 'r') as stream:
        intent_yaml = yaml.safe_load(stream)
        count = 0 
    for request_item in sorted(request_json, key=lambda kv: kv["confidenceScore"], reverse=True):
        for intent_item in intent_yaml[copilot]["Topics"]:
            if intent_item['ExternalIntentId'] == request_item["category"]:
                if "ShowInUncertainOptions" not in intent_item or intent_item["ShowInUncertainOptions"] is not False:
                    if count < options_limit and (subtopic in intent_item["SubTopics"] or not subtopic):
                        response_item = {
                            "DisplayName": intent_item["DisplayName"],
                            "TriggerId": intent_item["TriggerId"],
                            "TopicId": intent_item["TopicId"],
                            "ExternalIntentId": request_item["category"],
                            "ConfidenceScore": request_item["confidenceScore"],
                            "TriggerId": "main",
                            "Category": request_item["category"]
                        }
                        selected.append(response_item)
                        count += 1
                    else:
                        break
                else:
                    pass

    return selected

import datetime
from typing import Any, Optional, Self
import pymsteams
from .models import RequestSchema

WEBHOOK_URL="https://ecisolutions.webhook.office.com/webhookb2/d6378769-2918-47bc-b632-08790a115754@3876dbb5-741c-4fe6-9981-06fa00a6d682/IncomingWebhook/7abbc8603b8c4e1c92f8b2c3c2d097c4/0a01f6cb-2c49-49fd-a9d9-b5a0ee1003b4/V21W7Sb9RnE7ySYW0w8pSfwJVEl_4aaFbNFK3ER7dgfXA1"

date = datetime.datetime.now()
format = '%H:%M %p %m/%d/%Y'
TIMESTAMP = date.strftime(format)

EXAMPLE_JSON = {
    "user_request_text": "Could not submit warranty request",
    "timestamp": "12:00",
    "topic": "Doors",
    "subtopic": "Frame",
    "mention_users": False,
    "build_env": "dev",
    "request_origin": "Copilot",
    "system_error_message": {
        "error_message": "None",
        "error_code": "1",
        "error_count": "1",
        "timestamp": "12:00"
    },
    "user": {
        "user_name": "W.Manning",
        "first_name": "William",
        "last_name": "Manning",
        "phone_number": "12345678910",
        "mobile_phone_number": "12345678910",
        "some_other": "Some",
        "unexpected_attr": "Unexpected",
        "user_home": {
            "street": "Some Street",
            "city": "Some City",
            "state": "Some State",
            "postal_code": "Some Postal Code",
            "apartment_no": "Some Apartment No",
            "unexpected_attr": "Unexpected"
        }
    },
    "unexpected_attr": "Unexpected"
}



def create_ms_teams_error_message(request: Optional[RequestSchema]):
    # Can create multiple versions of this function for specific reporting conditions
    channel_message = pymsteams.connectorcard(WEBHOOK_URL)
    message_contents = []
    slack_message_contents = [
        '@Will.M ',
        # '@Laura ',
        # '@Jim McCarthy '
        ]
    if request:
        if request.mention_users:
            print('MENTIONING')
            message_contents.append('<at>WillManning</at>')
            # message_contents.append('<at>Laura Portz</at>')
            # message_contents.append('<at>Jim McCarthy</at>')
        if request.user and request.user.user_name:
            channel_message.title('\nUser: {} Encountered An Error'.format(request.user.user_name))
        else:
            channel_message.title('\nUser: {} Encountered An Error'.format("Unknown User"))
        if request.user and  request.user.phone_number:
            message_contents.append(format_message_text(new_line=True, user_phone_number=request.user.phone_number))
        message_contents.append(format_message_text(new_line=True, time_stamp=request.timestamp))
        message_contents.append(format_message_text(new_line=True, user_request_message=request.user_request_text))
        message_contents.append(format_message_text(new_line=True, session_id=request.session_id))
        message_contents.append(format_message_text(new_line=True, originating_topic=request.topic))
        message_contents.append(format_message_text(new_line=True, originating_subtopic=request.subtopic))
        message_contents.append(format_message_text(new_line=True, system_error_message=request.system_error_message.error_message))
        message_contents.append(format_message_text(new_line=True, request_origin=request.request_origin))
        message_contents.append(format_message_text(new_line=True, time_stamp=request.build_env))
        if request.additional_info:
            for item in request.additional_info: 
                message_contents.append(format_message_text(new_line=True, additional_info=item))
        channel_message.text("\n".join(message_contents))
    print('teams_channel_message: {}'.format(channel_message))
    return channel_message

def format_message_text(new_line: bool = False, *args, **kwargs):
    message_text = ''
    for arg in args:
        message_text += '\n %s' % (arg)
    for key, value in kwargs.items():
        message_text += "\n\t• %s: %s" % (key.capitalize().replace("_", " "), value)
        print(message_text)
    else:
        if new_line:
            message_text += '\n'
        return message_text

def ms_teams_error_messenger(request):    
    # cd GoogleCloudFunctions//ms_teams_messenger /
    # lsof -i tcp:8080
    # kill -9 PID
    # functions-framework-python --target ms_teams_error_messenger
    # http://localhost:8080?seconds=1 
    request_json = request.get_json(silent=True)
    request_args = request.args
    print('show args')
    for arg in request_json:
        try:
            print(arg + ': ' + request_json[arg])
        except:
            pass
            
    request_data: RequestSchema = RequestSchema.from_json(request_json=request_json)
    print(request_data.user_request_text)
    request_data.timestamp = TIMESTAMP
    teams_channel_message = create_ms_teams_error_message(request=request_data)
    print(teams_channel_message)
    if request_data.build_env == 'prod':
        assert teams_channel_message.send()
    else:
        assert teams_channel_message.send()
        
    return "OK"

# def run():
#     print("Sending...")

#     card = pymsteams.connectorcard(WEBHOOK_URL)
#     card.title("Weather Forecast")
#     card.text("\n".join([
#         f"Test Logger",
#         f"- Test Param 1",
#         f"- Test Param 2", 
#         f"- Test Param 3", 
#     ]))
#     assert card.send()
#     print("Sent")
    
# if __name__ == "__main__":
#     run()
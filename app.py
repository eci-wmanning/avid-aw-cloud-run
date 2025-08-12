# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import signal
import sys
from types import FrameType
import google_cloud_functions
from flask import Flask, request
import os
from utils.logging import logger
from dotenv import dotenv_values
from utils import log

app = Flask(__name__)


@app.route("/")
def hello() -> str:
    # Use basic logging with custom fields
    logger.info(logField="custom-entry", arbitraryField="custom-entry")

    # https://cloud.google.com/run/docs/logging#correlate-logs
    logger.info("Child logger with trace Id.")

    return "Hello, World!"


@app.route("/wait_sec")
def wait_sec() -> str:
    logger.info(logField="custom-entry", called_route="wait_sec")
    return google_cloud_functions.copilotWaitSec(request)

@app.route("/set_copilot_postman_monitor_flag")
def set_copilot_postman_monitor_flag() -> str:
    logger.info(logField="custom-entry", called_route="set_copilot_postman_monitor_flag")
    return google_cloud_functions.set_copilot_postman_monitor_flag(request)


@app.route("/get_topic_intents")
def get_topic_intents() -> str:
    logger.info(logField="custom-entry", called_route="get_topic_intents")
    return google_cloud_functions.getIntents(request)


@app.route("/dynamic_qna")
def dynamic_qna() -> str:
    logger.info(logField="custom-entry", called_route="dynamic_qna")
    return google_cloud_functions.dynamic_qna(request)

@app.route("/clarify_issue")
def clarify_issue() -> str:
    logger.info(logField="custom-entry", called_route="clarify_issue")
    return google_cloud_functions.clarify_issue(request)

@app.route("/ms_teams_error_messenger")
def ms_teams_error_messenger() -> str:
    logger.info(logField="custom-entry", called_route="ms_teams_error_messenger")
    return google_cloud_functions.ms_teams_error_messenger(request)


def shutdown_handler(signal_int: int, frame: FrameType) -> None:
    logger.info(f"Caught Signal {signal.strsignal(signal_int)}")

    from utils.logging import flush

    flush()

    # Safely exit program
    sys.exit(0)

if __name__ == "__main__":
    # Running application locally, outside of a Google Cloud Environment
    log(key=dotenv_values(".env")['AZURE_AI_API_KEY'])

    # handles Ctrl-C termination
    signal.signal(signal.SIGINT, shutdown_handler)

    app.run(host="localhost", port=8080, debug=True)
else:
    # handles Cloud Run container termination
    signal.signal(signal.SIGTERM, shutdown_handler)

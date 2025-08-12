import os
import functions_framework
from google.cloud import firestore
from firebase_admin import credentials, initialize_app
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel

try:
    cred = credentials.ApplicationDefault()
    app = initialize_app(credential=cred)
except Exception as err:
    print(err)
    
class WarrantyTopicsModel(BaseModel): 
    chatbot_client_secret: list[Any] = []
    chatbot_schema_name: str
    description: Optional[str] = ''
    enabled: bool
    keywords: Optional[str] = ''
    name: Optional[str] = ''
    postman_monitor_error_flag: bool

class FBTopicList(Enum): 
    APPLIANCES = 'appliances'
    DECKING = "decking"
    DOORS = "doors"
    ELECTRICAL = "electrical"
    EXTERIOR_FINISHES= "exterior_finishes"
    FLOORING = "flooring"
    FOUNDATION = "foundation"
    GARAGE ="garage"
    GENERAL = 'General'
    INTERIOR_CLIMATE_CONTROL = "interior_climate_control"
    INTERIOR_FINISHES = "interior_finishes"
    LANDSCAPE_AND_SITEWORK = "landscape_and_sitework"
    PLUMBING = "plumbing"
    ROOF = "roof"
    STRUCTURAL = "structural"
    WALLS_AND_CEILINGS = "walls_and_ceilings"

class BuildEnv(Enum):
    
    dev = "DEV"
    stage = "STAGE"
    prod = "PROD"
        
    @classmethod
    def _missing_(cls, value):
        return cls.dev
class EnvConfig:
    
    build_env: BuildEnv
    env_prefix: str # DEV_, STAGE_ or PROD_
    firebase_prefix: str # dev_, stage_ or prod_
    project_id: str # homekeep-dev-1614708479592
        
    def __init__(self, env: Optional[str]="dev") -> None:
            
        self.build_env = BuildEnv(env.upper() if env else "DEV")
        # log(assigning_build_env=self.build_env.value)
            
        match self.build_env:
            case BuildEnv.dev:
                self.project_id = os.environ.get('DEV_PROJECT_ID', 'homekeep-dev-1614708479592')
                self.firebase_prefix = BuildEnv.dev.value.lower() + "_"
            case BuildEnv.test:
                self.project_id = os.environ.get('DEV_PROJECT_ID', 'homekeep-dev-1614708479592')
                self.firebase_prefix = BuildEnv.dev.value.lower() + "_"
            case BuildEnv.stage:
                self.project_id = os.environ.get('PROD_PROJECT_ID', 'homekeep-e635a')
                self.firebase_prefix = BuildEnv.prod.value.lower() + "_"
            case BuildEnv.prod:
                self.project_id = os.environ.get('PROD_PROJECT_ID', 'homekeep-e635a')
                self.firebase_prefix = BuildEnv.prod.value.lower() + "_"
            case None:
                self.project_id = os.environ.get('DEV_PROJECT_ID', 'homekeep-dev-1614708479592')
                self.firebase_prefix = BuildEnv.dev.value.lower() + "_"
                    
        self.env_prefix = self.build_env.value + "_"

class FireStoreTopics:
    def __init__(self, topic: str, env: Optional[EnvConfig]=None):
        self.env_config: EnvConfig = env
        self.firestore_topic = FBTopicList(topic)
        self.db = firestore.Client(project=self.env_config.project_id)
        self.topic_model = None
        
    def get_topic_doc(self, env: Optional[str]=None):
        topic_ref = self.db.collection('warranty_topics').document(self.firestore_topic.value)
        topic_snapshot = topic_ref.get()
        self.topic_model = WarrantyTopicsModel.model_validate(topic_snapshot.to_dict())
        return topic_ref
    
    def assign_error_flag(self, error_flagged: bool = False):
        topic_ref = self.get_topic_doc()
        topic_ref.update({"postman_monitor_error_flag": error_flagged})
        print(f'FLAG: {error_flagged}')
        return topic_ref
        
    
def set_copilot_postman_monitor_flag(request):
    """HTTP Cloud Function.
    Args:
        request (flask.Request): The request object.
        <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>
    Returns:
        functions-framework-python --target set_monitor_flag
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """
    request_json = request.get_json(silent=True)
    request_args = request.args

    if request_args and 'error_flagged' in request_args and 'topic' in request_args and 'env' in request_args:
        flagged = bool(int(request_args['error_flagged']))
        print(f'FLAGGED: {flagged}')
        FireStoreTopics(
            topic=request_args['topic'], 
            env=EnvConfig(request_args['env'])).assign_error_flag(flagged)
        return {'status': 200, 'response': f'{request_args['topic']} Flag updated to: {flagged}'}
    elif request_args and 'topic' in request_args and 'env' in request_args:
        FireStoreTopics(
            topic=request_args['topic'], 
            env=EnvConfig(request_args['env'])).assign_error_flag(False)
        return {'status': 200, 'response': f'{request_args['topic']} Flag updated to: False'}
    else:
        return {'error': 'Requires topic, error_flagged, and env', 'response': 404}
    
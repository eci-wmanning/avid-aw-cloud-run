from google.cloud import firestore
from firebase_admin import credentials, initialize_app
import functions_framework
from dataclasses import field
from enum import Enum
from pydantic import BaseModel
from openai import AsyncAzureOpenAI
from typing import Any, List, Optional
import asyncio
import os
from models import FBTopicList

try:
    cred = credentials.ApplicationDefault()
    app = initialize_app(credential=cred)
except Exception as err:
    print(err)


# class FBTopicList(Enum): 
#     APPLIANCES = 'appliances'
#     DECKING = "decking"
#     DOORS = "doors"
#     ELECTRICAL = "electrical"
#     EXTERIOR_FINISHES= "exterior_finishes"
#     FLOORING = "flooring"
#     FOUNDATION = "foundation"
#     GARAGE ="garage"
#     INTERIOR_CLIMATE_CONTROL = "interior_climate_control"
#     INTERIOR_FINISHES = "interior_finishes"
#     LANDSCAPE_AND_SITEWORK = "landscape_and_sitework"
#     PLUMBING = "plumbing"
#     ROOF = "roof"
#     STRUCTURAL = "structural"
#     WALLS_AND_CEILINGS = "walls_and_ceilings"
    
class BuildEnv(Enum):
    
    dev = "DEV"
    stage = "STAGE"
    prod = "PROD"
    
    @classmethod
    def _missing_(cls, value):
        return cls.dev

class FBCollection(Enum):
    azure_data = "azure_data"
    
class EnvConfig:
    
    build_env: BuildEnv
    env_prefix: str # DEV_, STAGE_ or PROD_
    firebase_prefix: str # dev_, stage_ or prod_
    project_id: str # homekeep-dev-1614708479592
    
    def __init__(self, env: Optional[str]="dev") -> None:
        
        self.build_env = BuildEnv(env.upper() if env else "DEV")
        log(assigning_build_env=self.build_env.value)
        
        match self.build_env:
            case BuildEnv.dev:
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
        self.azure_ai_api_key = os.environ.get('AZURE_AI_API_KEY', 'NONE')
        self.azure_ai_endpoint = os.environ.get('AZURE_AI_ENDPOINT', 'https://ai-avidwarrantyhubuswest502033965267.openai.azure.com')
        self.azure_ai_deployment_name = os.environ.get('AZURE_AI_AZURE_AI_DEPLOYMENT_NAME', 'gpt-4o')
        self.azure_ai_model_name = os.environ.get('AZURE_AI_MODEL_NAME', 'gpt-4o')
        self.azure_ai_version = os.environ.get('AZURE_AI_API_VERSION', '2024-10-21')
        # self.firebase_prefix = self.build_env.value.lower() + "_" #Currently there's no 'stage' firestore/firebase
    
    def collection(self, collection_name: FBCollection):
        return self.firebase_prefix + collection_name.value # Ex: dev_azure_data
    
class IssueTrainingModel(BaseModel):
    issue_number: Optional[int] = 0
    observation: Optional[str] = ''
    performance_guideline: Optional[str] = ''
    remodeling_specific_guideline: Optional[str] = ''
    void_warranty_factors: Optional[str] = ''
    corrective_measure: Optional[str] = ''
    discussion: Optional[str] = ''
    matching_issue_certainty: Optional[float] = 0
    associated_copilot_flow: Optional[str] = ''
    chapter: Optional[int] = 0
    subchapter: Optional[int] = 0
    subtopics: list = field(default_factory=list)
    
class TopicTrainingModel(BaseModel): 
    issues: list[Any] = []
    topic_id: str
    topic: Optional[str] = ''
    additional_notes: Optional[str] = ''
    additional_topic_info: Optional[str] = ''
    system_instructions: list[Any]  = []


class FireStoreTopics:
    
    def __init__(self, topic: str, env: Optional[str]=None):
        self.env_config: EnvConfig = EnvConfig(env)
        self.topic = topic.lower()
        self.firestore_topic = FBTopicList(self.topic)
        self.db = firestore.Client(project=self.env_config.project_id)
        self.topic_model = None
        
    def get_topic_doc(self, env: Optional[str]=None):
        azure_data_ref = self.db.collection(self.env_config.collection(FBCollection.azure_data)).document(self.firestore_topic.value).get()
        self.topic_model = TopicTrainingModel.model_validate(azure_data_ref.to_dict())
        self.topic_model.issues = self._get_topic_issues()
        return self.topic_model
    
    def _get_topic_issues(self, env: Optional[str]=None):
        issues: List[IssueTrainingModel] = []
        azure_data_ref = self.db.collection(self.env_config.collection(FBCollection.azure_data)).document(self.firestore_topic.value).collections()    
        for issues_collection in azure_data_ref:
            for issue_doc in issues_collection.stream():
                issues.append(IssueTrainingModel.model_validate(issue_doc.to_dict()))
        log(found_issues=len(issues))
        return issues
    
def log(new_line: bool = False, *args, **kwargs) -> None:
    print_output = ''
    for arg in args:
        print_output += '•\n %s' % (arg)
    for key, value in kwargs.items():
        print_output += "\n• %s: %s" % (key.capitalize().replace("_", " "), value)
    else:
        if new_line:
            print_output += '\n'
    print(print_output)

class ResourceType(Enum):
    clarify_issue="CLARIFY_ISSUE"
    warranty_progressive_stream="WARRANTY_STREAM"
    alternative_topic = "ALTERNATIVE_TOPICS"
    cold_start="COLD_START"
    none=None
    


class CopilotPreviousQuestionsRequest(BaseModel):
    question_text: Optional[str]
    answer_text: Optional[str]


class CopilotRequest(BaseModel):
    user_input: Optional[str] = ''
    copilot: str = ''
    topic: str = ''
    subtopic: str = ''
    env: Optional[str] = ''
    start: Optional[bool]
    redirect_answer: Optional[str] = ''
    previous_questions: List[CopilotPreviousQuestionsRequest] = []


class RequestModel:
    request_model: CopilotRequest
    def __init__(self, request, *args, **kwargs):
        request_json = request.get_json(silent=True)
        self.request_model: CopilotRequest = CopilotRequest.model_validate(request_json)

class AnswerFormatModel(BaseModel):
    answer_text: str
    warrantable_certainty_modifier: Optional[float]
    answer_index: int
    associated_copilot_flow: Optional[str]
    closest_matching_issue_number: Optional[int]
    
class QuestionFormatModel(BaseModel):
    '''
    If used as a Google Cloud Function response, can be used to create a dynamic question-answer response, useable within Copilot.
    In this context, the question-answer set aims to find the closest matching issue withing the NAHB Residential Guidelines, 
    asking a clarifying question (question_text) with the paired relevant answer set (answer_set).
    '''
    question_text: str
    answer_set: List[AnswerFormatModel]
    user_answer: Optional[str]
    closest_matching_issue_number: Optional[int]
    closest_matching_flow: Optional[str]
    reason: str
    
class CopilotAnswerFormat(BaseModel):
    DisplayName: Optional[str]
    ExternalIntentId: Optional[str]
    Score: Optional[int]
    TopicId: Optional[str]
    TriggerId: Optional[str]
    # closest_matching_issue_number: Optional[int]
    

class CopilotQuestionFormat(BaseModel):
    question_text: str
    copilot_answer_set: List[CopilotAnswerFormat]

class AIResponseFormatModel(BaseModel): 
    question_model: Optional[QuestionFormatModel]
    
class CopilotResponse:
    question_text: str
    answer_set: List[str]
    warrantable: bool
    correct_issue: bool
    response: AIResponseFormatModel
    def __init__(self, *args, **kwargs) -> None:
        self.question_text = kwargs['question_text']
        self.answer_set = kwargs['answer_set']
        self.warrantable = kwargs['warrantable']
        self.correct_issue = kwargs['correct_issue']
        self.response = kwargs['response']



class AIResource:
    '''
    https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/structured-outputs?tabs=python
    '''
    connected: bool = False
    
    def __init__(self, env_config: EnvConfig, system_instructions: List[str] | None = None) -> None:
        self.system_instructions: List[str] | None = system_instructions
        self.env_config = env_config
        try:
            self.chat_client = AsyncAzureOpenAI(
                api_key=self.env_config.azure_ai_api_key,  
                api_version=self.env_config.azure_ai_version,
                azure_endpoint=self.env_config.azure_ai_endpoint, 
                max_retries=2
            )
        except:
            self.connected = False
        else:
            self.connected = True
    async def assign_system_instruction_set(self, system_instructions: List[str], topic_instructions: Optional[List[str]] = None):
                
        self.system_instructions = system_instructions
            
        log(processing_system_instructions='...')
        ai_response = self.chat_client.beta.chat.completions.stream(
            model=self.env_config.azure_ai_model_name,
            messages=[
                {"role": "system",
                "content": ' '.join(system_instructions)},
                {"role": "system",
                "content": ' '.join(topic_instructions if topic_instructions else [""])}]
            )
        return

    def assign_system_instructions(self, system_instructions: List[str]):
                
        self.system_instructions = system_instructions
            
        ai_response = self.chat_client.beta.chat.completions.parse(
            model=self.env_config.azure_ai_model_name,
            messages=[
                {"role": "system",
                "content": ' '.join(system_instructions)},]
            )
        return

    async def get_typed_structured_response(self, user_prompt: List[str], system_instructions: List[str] = [], response_format: type = AIResponseFormatModel) -> Any | None:
        """
        Generatively fills request model, requires first providing the model to be filled.

        Args:
            system_prompt (List[str]): The initial instructions if different than the provided instruction used for class instantiation. Joins to one string 
            user_prompt (List[str]): The current input to be processed. Joins to one string
            response_format (type): The object to be generatively filled
            
        Returns:
            AIResponseFormatModel | None: The model format to be returned, wherein some or all is generatively filled
        """
        if self.connected:
            self.assign_system_instructions(system_instructions=system_instructions)
            ai_response = await self.chat_client.beta.chat.completions.parse(
                model=self.env_config.azure_ai_model_name,
                messages=[
                    {"role": "system",
                    "content": ' '.join(system_instructions)},
                    {"role": "user",
                    "content": ' '.join(user_prompt)},],
                response_format=response_format
                )
            return ai_response.choices[0].message.parsed
            # print(ai_response)
        else:
            return None
        
            
    async def get_structured_response(self, user_prompt: List[str], system_instructions: List[str] = [], topic_instructions: List[str] = []) -> AIResponseFormatModel | None:
        """
        Generatively fills request model, requires first providing the model to be filled.

        Args:
            system_prompt (List[str]): The initial instructions if different than the provided instruction used for class instantiation. Joins to one string 
            user_prompt (List[str]): The current input to be processed. Joins to one string

        Returns:
            AIResponseFormatModel | None: The model format to be returned, wherein some or all is generatively filled
        """
        if self.connected:
            self.assign_system_instructions(system_instructions=system_instructions)
            ai_response = await self.chat_client.beta.chat.completions.parse(
                model=self.env_config.azure_ai_model_name,
                messages=[
                    {"role": "system",
                    "content": ' '.join(topic_instructions)},
                    {"role": "system",
                    "content": ' '.join(system_instructions)},
                    {"role": "user",
                    "content": ' '.join(user_prompt)},],
                response_format=AIResponseFormatModel # Describes the object format to be returned form the AI model.
                )
            asyncio.ensure_future(self.chat_client.close())
            return ai_response.choices[0].message.parsed
        else:
            return None
        
    async def get_chat_response(self, system_prompt: List[str], user_prompt: List[str]) -> str:
        """
        Basic question & typed chat completion

        Args:
            system_prompt (List[str]): The initial instructions if different than the provided instruction used for class instantiation. Joins to one string 
            user_prompt (List[str]): The current input to be processed. Joins to one string

        Returns:
            str: Generative response from the Azure AI model given the user input and system instructions
        """
        if self.connected:
            self.assign_system_instructions(system_instructions=system_prompt)
            ai_response = await self.chat_client.chat.completions.create(
                model=self.env_config.azure_ai_model_name,
                messages=[    
                    {"role": "system",
                    "content": ' '.join(system_prompt)},
                    {"role": "user",
                    "content": ' '.join(user_prompt)},]
                )
            response_text = ai_response.choices[0].message.content.__str__()
            return response_text.encode('utf-8').decode('unicode-escape')
        else:
            return 'NA'
    

class SystemInstructionsCreator:
    def __init__(self, copilot: str, subtopic: str, topic_training_data: TopicTrainingModel, limit_request: bool = True):
        try:
            self.copilot: str = copilot # Ex: 'interior_climate_control'
            self.subtopic: str = subtopic # Ex: 'heating_and_cooling_systems'
            self.topic: str = topic_training_data.topic if topic_training_data.topic else "" # Ex: 'Interior Climate Control'
        except Exception:
            pass
        
        self.limit_request = limit_request
        self.topic_training_data = topic_training_data
        self.matching_subtopic_issues = []
        
        for issue in self.topic_training_data.issues:
            if self.subtopic in issue.subtopics and not self.limit_request:
                issue_str = issue.__dict__.__str__() + "\n\n"
                self.matching_subtopic_issues.append(issue_str)
            elif self.subtopic in issue.subtopics:
                if issue and issue.observation and issue.associated_copilot_flow:
                    self.matching_subtopic_issues.append({"associated_copilot_flow": issue.associated_copilot_flow, "observation": issue.observation, "issue_number": issue.issue_number})
            else:
                pass
    
    def base_system_instructions(self):
        
        instructions: List[str] = [
            'Consider this list, which will be referred to as: \'topic_list\', which is a list of issues in which the \'observation\' is a basic description of a homeowners issue: \n{}.'.format(self.matching_subtopic_issues),
            'The user will submit an issue related to their residential home, which the \'topic_list\' will be used to determine if the issue is warrantable',
            'Any system instructions which includes something like: \'some_variable\', is referencing a field that will be assigned.',
            'Assume the user\'s issue relates to their home\'s {0} and all responses should be structured around a residential home\'s {1}.'.format(self.topic, self.subtopic),
            ]
        instructions.append(self.topic_training_data.additional_topic_info if self.topic_training_data.additional_topic_info else '')
        return instructions
    
    def redirect_issue_instructions(self):
        
        instructions: List[str] = [
            "Consider this list of common homeowner issue descriptions: {}.".format(self.matching_subtopic_issues.__str__()),
            "Each \'associated_copilot_flow\' will have a basic general description as the \'observation\' value.",
            "Compare the user's input against: \'observation\' and assign: \'closest_matching_copilot_flow\' as the value: \'associated_copilot_flow\' of the same object, which contains the closes matching description.",
            "Always assign a value.",
            "Assume the user's issue is related to their home's {0}, specifically {1}".format(self.topic, self.subtopic)]
        return instructions

    def alternative_topics_instructions(self):
        
        instructions: List[str] = [
            "Consider this list of common homeowner issue descriptions: {}.".format(self.matching_subtopic_issues.__str__()),
            "Each \'associated_copilot_flow\' will have a basic general description as the \'observation\' value.",
            "Compare the user's input against: \'observation\' and assign: \'closest_matching_copilot_flow\' as the value: \'associated_copilot_flow\' of the same object, which contains the closes matching description.",
            "Always assign a value.",
            "Assume the user's issue is related to their home's {0}, specifically {1}".format(self.topic, self.subtopic)]
        
        return instructions
    
    def clarifyUserIssueInstructions(self) -> List[str]:
        
        instructions: List[str] = [
            'Assign \'question_model\' using a clarifying question as \'question_text\' and the relative multiple choice answers to the question as \'answer_set\'.',
            'The \'question_text\' should be formed to include the issue\'s topic: {0}, and this subtopic: {1} and addressing the user\'s issue.'.format(self.topic, self.subtopic),
            'The goal is to determine which topic most closely matches the user\'s issue.',
            'Never include an answer being some form of the following; \'Other\', \'Not Certain\' or \'None\' as one of the \'answer_set\' answers.',
            'The amount of answers in \'answer_set\' should be between 2 to 5 answers, which prioritize answers clarifying the related topic observation the most. It\'s preferable that there would be more answers, up to 5.',
            'Each \'answer_text\' values should only be a couple words long, maximum 4.',
            'Assign each \'answer_set\' value: \'associated_copilot_flow\' as the closest matching value for the field: \'associated_copilot_flow\' from each object from the \'topic_list\'.',
        ]
        return instructions

class DynamicQnA:
    
    def __init__(self, ai_resource: AIResource, request: Any, limit_request: bool = True) -> None:
        
        self.ai_resource: AIResource = ai_resource
        request_model: CopilotRequest = RequestModel(request=request).request_model
        if request_model.copilot and request_model.subtopic:
            self.copilot: str = request_model.copilot
            self.topic: str = request_model.topic
            self.subtopic: str = request_model.subtopic
            self.env: str | None = request_model.env
            self.user_input: str | None = request_model.user_input
        else:
            raise Exception("Request body missing topic or subtopic.")
        self.firestore_app = FireStoreTopics(env=self.env, topic=self.topic)
        self.topic_training_data: TopicTrainingModel = self.firestore_app.get_topic_doc()
        self.limit_request: bool = limit_request
        self.instructions_model = SystemInstructionsCreator(copilot=self.copilot, subtopic=self.subtopic, topic_training_data=self.topic_training_data)
        
    async def _cold_start_instructions(self, system_instructions: List[str] = [], topic_instructions: List[str] = []):
        
        if not system_instructions:
            system_instructions = self.instructions_model.base_system_instructions()
            
        asyncio.ensure_future(self.ai_resource.assign_system_instruction_set(system_instructions=system_instructions))
        return
    
    def _start_conversation(self, topic_instructions: List[str]):
        
        if self.user_input:
            response = self._get_structured_response(system_instructions=self.instructions_model.base_system_instructions(), topic_instructions=topic_instructions)
            return response
        
        else:
            self._cold_start_instructions
            
    def _get_structured_response(self, topic_instructions: List[str], system_instructions: Optional[List[str]]) -> AIResponseFormatModel | None:
        
        if not system_instructions:
            system_instructions = self.instructions_model.base_system_instructions()
        if self.user_input:
            ai_response: AIResponseFormatModel | None = asyncio.run(
                self.ai_resource.get_structured_response(
                    system_instructions=system_instructions, 
                    user_prompt=[self.user_input], 
                    topic_instructions=topic_instructions)
                )
        return ai_response
    
    
class ClarifyIssueCreator(DynamicQnA):
    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        self.topic_instructions = self.instructions_model.clarifyUserIssueInstructions()
        _pass = self._cold_start_instructions()
    
    def start_conversation(self):
        
        response = self._start_conversation(topic_instructions=self.instructions_model.clarifyUserIssueInstructions())
        format_copilot_response: CopilotQuestionFormat = self.assign_copilot_question(ai_response=response)
        
        return format_copilot_response
    
    def _check_answer_index(self, question_model: QuestionFormatModel):
        
        index = 0
        
        if question_model.answer_set[0].answer_index == 1:
            
            for idx in question_model.answer_set:
                
                idx.answer_index = index
                index += 1
                
        return question_model
    
    def assign_copilot_question(self, ai_response: Optional[AIResponseFormatModel]) -> CopilotQuestionFormat:
        
        copilot_answers: List[CopilotAnswerFormat] = []
        
        if ai_response and ai_response.question_model:
            
            ai_response.question_model = self._check_answer_index(ai_response.question_model)
            
            for item in ai_response.question_model.answer_set:
                
                if item.associated_copilot_flow and self.topic_training_data.topic_id:
                    
                    new_answer_set: CopilotAnswerFormat = CopilotAnswerFormat(
                        DisplayName=item.answer_text, 
                        ExternalIntentId=item.associated_copilot_flow, 
                        Score=50, 
                        TopicId=self.topic_training_data.topic_id + ".topic." + item.associated_copilot_flow, 
                        TriggerId=item.associated_copilot_flow)
                    copilot_answers.append(new_answer_set)
                    
            not_listed_answer_set = CopilotAnswerFormat(
                DisplayName='Not listed', 
                ExternalIntentId="None", 
                Score=0, 
                TopicId=self.topic_training_data.topic_id + ".topic." + "None", 
                TriggerId="None")
            copilot_answers.append(not_listed_answer_set)
            
            copilot_response_model: CopilotQuestionFormat = CopilotQuestionFormat(question_text=ai_response.question_model.question_text, copilot_answer_set=copilot_answers)
            
        return copilot_response_model
    
    
@functions_framework.http
def clarify_issue(request):
    """
    * Running locally
        * cd ~/Development/avid-warranty-cloud/GoogleCloudFunctions/clarify-issue
        * functions-framework-python --target clarify_issue
        * note: If a local process is still running on 8080
            * kill -9 $(lsof -i:8080 -t)
    """
    if request.method == "OPTIONS":
        headers = {
            # "Access-Control-Allow-Origin": "http://localhost:3050",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Origin, Content-Type, Accept",
            "Access-Control-Max-Age": "3600",
        }
        request.mode = 'no-cors'
        return ("OK", 204, headers)
    else:
        headers = {"Access-Control-Allow-Origin": "*"}
    
    try:
        resource_type = ResourceType(request.args.get("resource"))
    except Exception as err:
        log(error_encountered=err.add_note("Unexpected request body."))
        return ({"response": "Query sent using invalid 'resource' value. Expected: {}".format([e.value for e in ResourceType])}, 500, headers)
    
    app = AIResource(env_config=EnvConfig())
    log(processing_request=resource_type.value)
    
    match resource_type:
        case ResourceType.clarify_issue as clarify:
                
                clarify_issue_model: CopilotRequest = RequestModel(request=request).request_model
                log(env=clarify_issue_model.env, topic=clarify_issue_model.copilot)
                
                if clarify_issue_model and clarify_issue_model.copilot and clarify_issue_model.subtopic and clarify_issue_model.user_input:
                    clarify_issue_resource = ClarifyIssueCreator(ai_resource=app, request=request)
                    clarify_response = clarify_issue_resource.start_conversation()
                    
                    if clarify_response:
                        return (clarify_response.model_dump(), 200, headers)
                    else:
                        _cold_start = clarify_issue_resource._cold_start_instructions()
                        return ({"response": "OK"}, 200, headers)
        case ResourceType.none | ResourceType.cold_start:
            
            request_model: CopilotRequest = RequestModel(request=request).request_model
            if request_model and request_model.copilot and request_model.subtopic:
                question_creator_resource = DynamicQnA(ai_resource=app, request=request)
                _cold_start = question_creator_resource._cold_start_instructions()
                return ({"response": "OK"}, 200, headers)
            
        case _:
            
            return ({"response": "OK"}, 200, headers) 
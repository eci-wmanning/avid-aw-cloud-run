from enum import Enum
from typing import List, Optional, Any
from dataclasses import dataclass, field
from pydantic import BaseModel
import json
# from ...training_data import training_data 


class ResourceType(Enum):
    clarify_issue="CLARIFY_ISSUE"
    clarify = "CLARIFY_NEW"
    warranty_progressive_stream="WARRANTY_STREAM"
    cold_start="COLD_START"
    none=None
    

@dataclass
class GuidelinesFileModel: 
    '''
    The topic specific json object, represented as a model
    Better option would be to set up a blob storage resource, so the OpenAI model is trained on the data prior to deploy
    '''
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


@dataclass
class TopicTrainingModel: 
    issues = []
    topic_id: str = ''
    topic: Optional[str] = ''
    additional_notes: Optional[str] = ''
    additional_topic_info: Optional[str] = ''
    system_instructions = []
    
    def __init__(self, copilot: str, subtopic: str):
        self.copilot = copilot.lower()
        self.subtopic = subtopic
        # file_path = 'training_data/{}.json'.format(self.copilot.lower())
        file_path = 'combined_training_data.json'
        json_file = json.load(open(file_path, 'r'))
        self.topic = json_file[self.copilot]['topic']
        self.topic_id = json_file[self.copilot]['topic_id']
        self.additional_notes = json_file[self.copilot]['additional_notes']
        self.additional_topic_info = json_file[self.copilot]['additional_topic_info']
        self.issues.extend(GuidelinesFileModel(**items) for items in json_file[self.copilot]['issues'] if self.subtopic in items['subtopics'])
    
    def get_issues(self) -> list[GuidelinesFileModel]:
        file_path = 'combined_training_data.json'
        json_file = json.load(open(file_path, 'r'))
        self.topic = json_file[self.copilot]['topic']
        self.additional_notes = json_file[self.copilot]['additional_notes']
        self.additional_topic_info = json_file[self.copilot]['additional_topic_info']
        self.issues.extend(GuidelinesFileModel(**items) for items in json_file[self.copilot]['issues'])
        return self.issues


class LimitedIssueModel(BaseModel):
    observation: Optional[str] = ''
    associated_copilot_flow: Optional[str] = ''

class LimitedTopicModel(BaseModel):
    issues: List[LimitedIssueModel] = []


class CopilotPreviousQuestionsRequest(BaseModel):
    question_text: Optional[str]
    answer_text: Optional[str]


class CopilotRequest(BaseModel):
    user_input: Optional[str] = ''
    copilot: Optional[str] = ''
    subtopic: Optional[str] = ''
    start: Optional[bool]
    redirect_answer: Optional[str] = ''
    previous_questions: List[CopilotPreviousQuestionsRequest] = []


class RequestModel:
    request_model: CopilotRequest
    def __init__(self, request, *args, **kwargs):
        request_json = request.get_json(silent=True)
        self.request_model: CopilotRequest = CopilotRequest.model_validate(request_json)

class ObservationsAddressingIssue(BaseModel):
    description: List[str]
    associated_issue_numbers: List[int]
    
class MatchingIssueCertainty(Enum):
    high = 100
    medium = 50
    low = 25
    none = 0
    
class WarrantableIssueCertainty(Enum):
    high = 100
    medium = 50
    low = 25
    none = 0
    
class TopicObservationModel(BaseModel):
    observation: str | None
    issue_no:  int | None
    matching_certainty_score: MatchingIssueCertainty
    
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
    closest_matching_issue_number: Optional[int]
    

class CopilotQuestionFormat(BaseModel):
    question_text: str
    copilot_answer_set: List[CopilotAnswerFormat]

class StructuredVariableModel(BaseModel):
    variable_type: Any
    variable_description: str
    def __class__(self):
        return self.variable_type

class AIResponseFormatModel(BaseModel): 
    issue_number: Optional[int]
    # observation: Optional[str]
    # performance_guideline: Optional[str]
    # remodeling_specific_guideline: Optional[str]
    # void_warranty_factors: Optional[str]
    # corrective_measure: Optional[str]
    # discussion: Optional[str]
    builder_responsible: Optional[bool]
    question_model: Optional[QuestionFormatModel]
    correct_issue_certainty_score: int
    issue_warrantable_certainty_score: WarrantableIssueCertainty

class CopilotResponseFormatModel(BaseModel):
    ai_response: AIResponseFormatModel
    copilot_answer_set: List[CopilotQuestionFormat]
    copilot_question_text: Optional[str]
    
    
class DialogHistoryModel:
    issue_warrantable: bool = False
    warrantable_certainty_score: WarrantableIssueCertainty = WarrantableIssueCertainty.none
    previous_dialog: List[Optional[QuestionFormatModel]] = []
    
    def __init__(self) -> None:
        pass
    
    def add_dialog(self, response_model: AIResponseFormatModel):
        self.previous_dialog.append(response_model.question_model)
        
    def update_dialog(self, response_model: Optional[AIResponseFormatModel], warrantable: bool, certainty: WarrantableIssueCertainty):
        if response_model:
            self.previous_dialog.append(response_model.question_model)
        self.issue_warrantable = warrantable
        self.warrantable_certainty_score = certainty

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

class RedirectResponse(BaseModel):
    closest_matching_copilot_flow: Optional[str]

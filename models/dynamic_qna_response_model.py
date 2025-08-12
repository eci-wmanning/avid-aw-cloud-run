from pydantic import BaseModel
from typing import Optional, List
from enum import Enum

class WarrantableIssueCertainty(Enum):
    high = 100
    medium = 50
    low = 25
    none = 0
    
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
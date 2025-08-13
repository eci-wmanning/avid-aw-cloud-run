from enum import Enum
from pydantic import BaseModel
from openai import AzureOpenAI, AsyncAzureOpenAI
from typing import Any, List, Optional
import asyncio
from resources import AIResource
from .models import *
from .instructions import SystemInstructionsCreator
from .question_creator import QuestionCreator
from utils import log
from flask import Flask, request

class FBCollection(Enum):
    azure_data = "azure_data"
    
class Wrapper:
    def __init__(self, f):
        self.f = f
    def __call__(self, *args, **kwargs):
        return self.f(*args, **kwargs)


class DynamicQnA:
    def __init__(
        self, 
        ai_resource: AIResource,
        request: Any,
        limit_request: bool = True) -> None:
        
        request_model: CopilotRequest = RequestModel(request=request).request_model
        self.ai_resource = ai_resource
        if request_model.copilot and request_model.subtopic:
            self.copilot: str = request_model.copilot
            self.subtopic: str = request_model.subtopic
        else:
            raise Exception("Request body missing topic or subtopic.")
        self.user_input = request_model.user_input
        self.topic_training_data = TopicTrainingModel(copilot=self.copilot, subtopic=self.subtopic,)
        self.ai_resource: AIResource = ai_resource
        self.limit_request = limit_request
        self.instructions_model = SystemInstructionsCreator(copilot=self.copilot, subtopic=self.subtopic, topic_training_data=self.topic_training_data)
        
    async def _cold_start_instructions(self, system_instructions: List[str] = [], topic_instructions: List[str] = []):
        
        if not system_instructions:
            system_instructions = self.instructions_model.base_system_instructions()
            
        asyncio.ensure_future(self.ai_resource.assign_system_instruction_set(system_prompt=system_instructions))
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
                    system_prompt=system_instructions, 
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
    
    def check_answer_index(self, question_model: QuestionFormatModel):
        
        index = 0
        
        if question_model.answer_set[0].answer_index == 1:
            
            for idx in question_model.answer_set:
                
                idx.answer_index = index
                index += 1
                
        return question_model
    
    def assign_copilot_question(self, ai_response: Optional[AIResponseFormatModel]) -> CopilotQuestionFormat:
        
        copilot_answers: List[CopilotAnswerFormat] = []
        
        if ai_response and ai_response.question_model:
            
            ai_response.question_model = self.check_answer_index(ai_response.question_model)
            
            for item in ai_response.question_model.answer_set:
                
                if item.associated_copilot_flow and self.topic_training_data.topic_id:
                    
                    new_answer_set: CopilotAnswerFormat = CopilotAnswerFormat(
                        DisplayName=item.answer_text, 
                        ExternalIntentId=item.associated_copilot_flow, 
                        Score=50, 
                        TopicId=self.topic_training_data.topic_id + ".topic." + item.associated_copilot_flow, 
                        TriggerId=item.associated_copilot_flow, 
                        closest_matching_issue_number=item.closest_matching_issue_number)
                    copilot_answers.append(new_answer_set)
                    
            not_listed_answer_set = CopilotAnswerFormat(
                DisplayName='Not listed', 
                ExternalIntentId="None", 
                Score=0, 
                TopicId=self.topic_training_data.topic_id + ".topic." + "None", 
                TriggerId="None", closest_matching_issue_number=0)
            copilot_answers.append(not_listed_answer_set)
            
            copilot_response_model: CopilotQuestionFormat = CopilotQuestionFormat(question_text=ai_response.question_model.question_text, copilot_answer_set=copilot_answers)
            
        return copilot_response_model
    
    
class ClarifyIssue:
    def __init__(
        self, 
        ai_resource: AIResource,
        copilot: str = '',
        subtopic: str = '',
        limit_request: bool = True) -> None:
        
        self.ai_resource = ai_resource
        self.copilot: Optional[str] = copilot
        self.subtopic: str = subtopic
        self.topic_training_data = TopicTrainingModel(copilot=self.copilot, subtopic=self.subtopic,)
        self.ai_resource: AIResource = ai_resource
        self.limit_request = limit_request
        self.instructions_model = SystemInstructionsCreator(copilot=copilot, subtopic=subtopic, topic_training_data=self.topic_training_data)

    async def cold_start_instructions(self):
        
        instructions = self.instructions_model.base_system_instructions()
        asyncio.ensure_future(self.ai_resource.assign_system_instruction_set(system_prompt=instructions))
        
        return
    
    def start_conversation(self, user_input: Optional[str], redirect_answer: Optional[str]):
        
        if user_input:
            response = self.get_issue_clarification_ai_response(user_prompt=[user_input])
            # return response
            new_response = self.assign_copilot_question(ai_response=response)
            return new_response
        else:
            self.cold_start_instructions

    def check_answer_index(self, question_model: QuestionFormatModel):
        
        index = 0
        if question_model.answer_set[0].answer_index == 1:
            for idx in question_model.answer_set:
                idx.answer_index = index
                index += 1
        return question_model

    def assign_copilot_question(self, ai_response: Optional[AIResponseFormatModel]) -> CopilotQuestionFormat:
        
        copilot_answers: List[CopilotAnswerFormat] = []
        
        if ai_response and ai_response.question_model:
            
            for item in ai_response.question_model.answer_set:
                
                if item.associated_copilot_flow and self.topic_training_data.topic_id:
                    
                    new_answer_set: CopilotAnswerFormat = CopilotAnswerFormat(
                        DisplayName=item.answer_text, 
                        ExternalIntentId=item.associated_copilot_flow, 
                        Score=50, 
                        TopicId=self.topic_training_data.topic_id + ".topic." + item.associated_copilot_flow, 
                        TriggerId=item.associated_copilot_flow, 
                        closest_matching_issue_number=item.closest_matching_issue_number)
                    copilot_answers.append(new_answer_set)
                    
            not_listed_answer_set = CopilotAnswerFormat(DisplayName='Not listed', ExternalIntentId="None", Score=0, TopicId=self.topic_training_data.topic_id + ".topic." + "None", TriggerId="None", closest_matching_issue_number=0)
            copilot_answers.append(not_listed_answer_set)
            
            copilot_response_model: CopilotQuestionFormat = CopilotQuestionFormat(question_text=ai_response.question_model.question_text, copilot_answer_set=copilot_answers)
        
        return copilot_response_model
    
    def get_issue_clarification_ai_response(self, user_prompt: List[str]) -> AIResponseFormatModel | None:
        
        ai_response: AIResponseFormatModel | None = asyncio.run(
            self.ai_resource.get_structured_response(
                system_prompt=self.instructions_model.base_system_instructions(), 
                user_prompt=user_prompt, 
                topic_instructions=self.instructions_model.clarifyUserIssueInstructions())
            )
        
        if ai_response:
            if ai_response.question_model != None:
                
                ai_response.question_model = self.check_answer_index(ai_response.question_model)
            
            if ai_response.issue_number != None or ai_response.issue_number != 'None':
                self.issue_no = ai_response.issue_number
            
            if ai_response.question_model:
                if ai_response.question_model.closest_matching_issue_number:
                    closest_issues: List[GuidelinesFileModel] = self.topic_training_data.issues
                    
                    for issue in closest_issues:
                        if issue.associated_copilot_flow == ai_response.question_model.closest_matching_issue_number:
                            ai_response.question_model.closest_matching_flow = issue.associated_copilot_flow
                return ai_response
            else:
                return ai_response

def dynamic_qna(request):
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
    
    log(processing_request=ResourceType.clarify_issue.value)
                
    model: CopilotRequest = RequestModel(request=request).request_model

    ai_resource = AIResource()
    
    if model and model.copilot and model.subtopic:
        clarify_issue_resource = ClarifyIssue(copilot=model.copilot, subtopic=model.subtopic, ai_resource=ai_resource)
        if model.copilot and model.subtopic and model.user_input:
            clarify_response = clarify_issue_resource.start_conversation(user_input=model.user_input, redirect_answer=None)
            log(clarify_response=clarify_response)
            if clarify_response:
                return (clarify_response.model_dump(), 200, headers)
        else:
            cold_start = clarify_issue_resource.cold_start_instructions()
            return ({"response": "OK"}, 200, headers)
        
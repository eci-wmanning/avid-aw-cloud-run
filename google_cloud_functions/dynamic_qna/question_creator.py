from typing import List, Optional
from pydantic import BaseModel
import asyncio
from .models import *
from .instructions import SystemInstructionsCreator
from utils import log
from resources import AIResource

class QuestionCreator:
    '''
    https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/structured-outputs?tabs=python
    '''
    CORRECT_ISSUE_UPPER_CERTAINTY=80
    UPPER_CERTAINTY = 90
    LOWER_CERTAINTY = 35

    def __init__(
        self, 
        ai_resource: AIResource,
        copilot: str = '',
        subtopic: str = '',
        # system_instructions: str | None = None,
        limit_request: bool = True) -> None:
        self.copilot: Optional[str] = copilot
        self.subtopic: str = subtopic
        self.topic_training_data = TopicTrainingModel(copilot=self.copilot, subtopic=self.subtopic,)
        self.ai_resource: bool = ai_resource
        _start_response = self.createBaseInstructions()
        self.limit_request = limit_request
        self.dialog: Optional[CopilotRequest] = None
        if self.topic_training_data.issues:
            self.observation_model: List[TopicObservationModel] = [TopicObservationModel(observation=topic.observation if topic else None, issue_no=topic.issue_number if topic else None, matching_certainty_score=MatchingIssueCertainty.none) for topic in self.topic_training_data.issues]
        self.dialog_history = DialogHistoryModel()
        self.limited_training_model: List[LimitedIssueModel] = []
        self.issue_no = None
        self.calculated_certainty = 0
            
        
    def start_conversation(self, user_input: Optional[str], redirect_answer: Optional[str], dialog: Optional[CopilotRequest] = None):
        # log(processing='...')
        self.dialog = dialog
        if user_input:
            base_response = self.createBaseInstructions()
            if self.limit_request: 
                system_instructions = self.limited_redirect_issue_instructions()
            else:
                system_instructions = self.redirect_issue_instructions()
            response = self.get_issue_clarification_ai_response(system_prompt=system_instructions, user_prompt=[user_input])
            new_response = self.assign_copilot_question(ai_response=response)
            return new_response
        else:
            base_response = self.createBaseInstructions()
    def get_redirect_value(self, user_input: Optional[str], redirect_answer: Optional[str]) -> CopilotAnswerFormat | None:
        # log(processing='...')
        if redirect_answer:
            if self.limit_request: 
                system_instructions = self.limited_redirect_issue_instructions()
            else:
                system_instructions = self.redirect_issue_instructions()
            response: RedirectResponse | None = self.get_redirect_ai_response(system_prompt=system_instructions, user_prompt=[redirect_answer])
            if response:
                redirect_model = CopilotAnswerFormat(DisplayName=response.closest_matching_copilot_flow, ExternalIntentId=response.closest_matching_copilot_flow, TopicId=response.closest_matching_copilot_flow, TriggerId=response.closest_matching_copilot_flow, closest_matching_issue_number=1, Score=100)
                return redirect_model
                
    def format_topic_list_instructions(self):
        issues = []
        for issue in self.topic_training_data.issues:
            if self.subtopic in issue.subtopics:
                issue_str = issue.__dict__.__str__() + "\n\n"
                issues.append(issue_str)
                # self.limited_training_model.append(LimitedIssueModel(observation=issue.observation, associated_copilot_flow=issue.associated_copilot_flow))
        # issues = []
        # for issue in self.limited_training_model:
        #     issue_str = issue.__dict__.__str__() + "\n\n"
        #     issues.append(issue_str)
        log(issues=issues)
        return issues
        
        
    async def cold_start_instructions(self):
        instructions = self.createBaseInstructions()
        asyncio.ensure_future(self.ai_resource.assign_system_instruction_set(system_prompt=instructions))
        return
        
    def createBaseInstructions(self):
        # log(assigning='Base System Instructions...')
        instructions: List[str] = [
            'Consider this list, which will be referred to as: \'topic_list\', which is a list of issues in which the \'observation\' is a basic description of a homeowners issue: \n{}.'.format(self.format_topic_list_instructions()),
            'The user will submit an issue related to their residential home, which the list of topics will be used to determine if the issue is warrantable',
            'Any system instructions which includes something like: \'some_variable\', is referencing a field that will be assigned.',
            'Assume the user\'s issue relates to their home\'s {0} and all responses should be structured around a residential home\'s {1}.'.format(self.copilot, self.subtopic),
            ]
        instructions.append(self.topic_training_data.additional_topic_info if self.topic_training_data.additional_topic_info else '')
        return instructions
        
    def related_issue_instructions(self):
        combined = []
        for guideline in self.format_topic_list_instructions():
            if guideline and guideline.observation and guideline.issue_no:
                combined.append("{0}: {1}".format(guideline.issue_no, guideline.observation))
        instructions: List[str] = [
            "Each descriptions will start with a number followed by a colon and then the description text, for example; \'3: Some description text\'.",
            "Assign the field called \'description\' as a list of issues from the list of descriptions that is most related to the user's issue."]
        return instructions
        
    def redirect_issue_instructions(self):
        combined = []
        for guideline in self.topic_training_data.issues:
            if guideline and guideline.observation and guideline.associated_copilot_flow:
                combined.append({"associated_copilot_flow": guideline.associated_copilot_flow, "observation": guideline.observation})
        instructions: List[str] = [
            "Consider this list of descriptions that a homeowners issue: {}.".format(combined.__str__()),
            "Each \'associated_copilot_flow\' will have a basic general description as the \'observation\' value.",
            "Compare the user's input against: \'observation\' and assign: \'closest_matching_copilot_flow\' as the value: \'associated_copilot_flow\' of the same object, which contains the closes matching description.",
            "Always assign a value.",
            "Assume the user's issue is related to their home's {0}, specifically {1}".format(self.copilot, self.subtopic)]
        return instructions
        
    def limited_redirect_issue_instructions(self):
        combined = []
        for guideline in self.topic_training_data.issues:
            if guideline and guideline.observation and guideline.associated_copilot_flow:
                combined.append({"associated_copilot_flow": guideline.associated_copilot_flow, "observation": guideline.observation})
        instructions: List[str] = [
            "Consider this list of descriptions that a homeowners issue: {}.".format(combined.__str__()),
            "Each \'associated_copilot_flow\' will have a basic general description as the \'observation\' value.",
            "Compare the user's input against: \'observation\' and assign: \'closest_matching_copilot_flow\' as the value: \'associated_copilot_flow\' of the same object, which contains the closes matching description.",
            "Always assign a value.",
            "Assume the user's issue is related to their home's {0}, specifically {1}".format(self.copilot, self.subtopic)]
        return instructions
        
    def clarifyUserIssueInstructions(self) -> List[str]:
        # log(assigning='Specific Task Instructions...')
        # instructions = self.createBaseInstructions()
        instructions = []
            
        # instructions = []
        instructions.extend([
            'Assign \'question_model\' using a clarifying question as \'question_text\' and the relative multiple choice answers to the question as \'answer_set\'.',
            'The \'question_text\' should be formed to include the issue\'s topic: {0}, and this subtopic: {1} and addressing the user\'s issue.'.format(self.copilot, self.subtopic),
            'The goal is to determine which topic most closely matches the user\'s issue.',
            'Never include an answer being some form of the following; \'Other\', \'Not Certain\' or \'None\' as one of the \'answer_set\' answers.',
            # 'The \'answer_index\' starts at 0.',
            'The amount of answers in \'answer_set\' should be between 2 to 5 answers, which prioritize answers clarifying the related topic observation the most.',
            'Answer text should only be a couple words long, maximum 4.',
            'Assign each \'answer_set\' value: \'associated_copilot_flow\' as the closest matching value for the field: \'associated_copilot_flow\' from each object from the \'topic_list\'.',
        ])
        if self.dialog:
            if self.dialog.previous_questions:
                json_questions = []
                for item in self.dialog.previous_questions:
                    json_questions.append(item.model_dump_json())
                # print("FOUND PREVIOUS QUESTIONS: {}".format(json_questions))
                instructions.extend([
                    'Take into account the user\' previous questions and their selected answers as: {}'.format(json_questions)
                ])
        return instructions

    def structuredSystemStartingInstructions(self) -> List[str]:
        '''Created as an array for easy adding/removing instruction sets. Combines to one string @call to AI model'''
        instructions: List[str] = [
            'Extract the closest matching object from: {}.'.format(self.topic_training_data.issues.__str__()),
            'If the \'corrective_measure\' signifies that the builder or contractor must correct the users issue, assign \'builder_responsible\' to True',
            'Consider the previous questions and answers: {}.'.format(self.dialog_history.previous_dialog),
            'Assign \'issue_warrantable_certainty_score\' a score of 1 to 100, with 100 being the overall certainty of the issue being warrantable.']
        return instructions
        
    def structuredSystemInstructions(self, response: AIResponseFormatModel | None) -> List[str]:
        '''Created as an array for easy adding/removing instruction sets. Combines to one string @call to AI model'''
        instructions: List[str] = [
            'If the \'corrective_measure\' signifies that the builder or contractor must correct the users issue, assign \'builder_responsible\' to True',
            'Consider the previous questions and answers: {}.'.format(self.dialog_history.previous_dialog),
            'Create a question, as: \'question_text\' and a multiple choice answer_set as an array containing objects each containing an \'answer_text\' value and a \'warrantable_certainty_modifier\' value which can be anywhere between 0 to 100, where 0 signifies a less likelihood that the issue is warrantable.',
            'Consider the previous question and answers and assign \'issue_warrantable_certainty_score\' a score of 1 to 100, with 100 being completely certain the issue is warrantable.']
        return instructions
    def check_answer_index(self, question_model: QuestionFormatModel):
        new_model = question_model
        index = 0
        if question_model.answer_set[0].answer_index == 1:
            for idx in question_model.answer_set:
                idx.answer_index = index
                index += 1
        return question_model
        
    def assign_copilot_question(self, ai_response: Optional[AIResponseFormatModel]) -> CopilotQuestionFormat:
        copilot_answers = []
        if ai_response and ai_response.question_model:
            for item in ai_response.question_model.answer_set:
                if item.associated_copilot_flow and self.topic_training_data.topic_id:
                    new_answer_set = CopilotAnswerFormat(DisplayName=item.answer_text, ExternalIntentId=item.associated_copilot_flow, Score=50, TopicId=self.topic_training_data.topic_id + ".topic." + item.associated_copilot_flow, TriggerId=item.associated_copilot_flow, closest_matching_issue_number=item.closest_matching_issue_number)
                    copilot_answers.append(new_answer_set)
            
            copilot_response_model: CopilotQuestionFormat = CopilotQuestionFormat(question_text=ai_response.question_model.question_text, copilot_answer_set=copilot_answers)
        return copilot_response_model
            
    def get_redirect_ai_response(self, system_prompt: List[str], user_prompt: List[str]) -> RedirectResponse | None:
        ai_response: RedirectResponse | None = asyncio.run(self.ai_resource.get_typed_structured_response(system_prompt=system_prompt, user_prompt=user_prompt, response_format=RedirectResponse))
        if ai_response:
            return ai_response
        else:
            return ai_response
                
    def get_issue_clarification_ai_response(self, system_prompt: List[str], user_prompt: List[str]) -> AIResponseFormatModel | None:
            
        ai_response: AIResponseFormatModel | None = asyncio.run(
            self.ai_resource.get_structured_response(
                system_prompt=self.createBaseInstructions(), 
                user_prompt=user_prompt, 
                topic_instructions=system_prompt)
            )
            
        if ai_response:
            if ai_response.question_model != None:
                ai_response.question_model = self.check_answer_index(ai_response.question_model)
                ai_response.question_model.answer_set.append(AnswerFormatModel(answer_text='Not listed', answer_index=len(ai_response.question_model.answer_set), warrantable_certainty_modifier=0, associated_copilot_flow="None", closest_matching_issue_number=0))
                
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
            
    def get_structured_ai_response(self, system_prompt: List[str], user_prompt: List[str]) -> AIResponseFormatModel | None:
        if system_prompt != self.system_instructions:
            self.system_instructions = system_prompt
            ai_response: AIResponseFormatModel | None = asyncio.run(self.ai_resource.get_structured_response(system_prompt=system_prompt, user_prompt=user_prompt))
        else:
            ai_response: AIResponseFormatModel | None = asyncio.run(self.ai_resource.get_structured_response(user_prompt=user_prompt))
                
        if ai_response:
                
            if ai_response.issue_number != None or ai_response.issue_number != 'None':
                self.issue_no = ai_response.issue_number
                
            if ai_response.question_model:
                selected_user_input = input("Type 0, 1, 2... etc to select answer. SELECTION: ")
                # ai_response.question_model.user_answer = ai_response.question_model.answer_set[AnswerFormatModel(answer_text=selected_user_input, warrantable_certainty_modifier=)] if ai_response.question_model.answer_set is not [] else 'None', 
                ai_response.question_model.user_answer = ai_response.question_model.answer_set[int(selected_user_input)].answer_text if ai_response.question_model.answer_set is not [] else 'None'
                # log(selected=ai_response.question_model.user_answer)
                    
            self.dialog_history.update_dialog(response_model=ai_response, warrantable=True, certainty=ai_response.issue_warrantable_certainty_score)
                
            if ai_response.issue_warrantable_certainty_score.value >= self.UPPER_CERTAINTY:
                # log(ending_session='Issue found to be warrantable')
                return ai_response
            elif ai_response.issue_warrantable_certainty_score.value <= self.LOWER_CERTAINTY and ai_response.issue_warrantable_certainty_score != 0:
                # log(ending_session='Issue found to NOT be warrantable')
                return ai_response
            else:
                new_system_prompt = self.structuredSystemInstructions(response=ai_response)
                if ai_response.question_model:
                    self.get_structured_ai_response(
                        system_prompt=new_system_prompt, 
                        user_prompt=[ai_response.question_model.user_answer if ai_response.question_model.user_answer else 'None'])
            return ai_response
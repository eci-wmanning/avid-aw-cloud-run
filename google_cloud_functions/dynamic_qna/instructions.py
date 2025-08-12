from typing import List
from .models import TopicTrainingModel

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
        
    def clarifyUserIssueInstructions(self) -> List[str]:
        instructions = []
            
        instructions.extend([
            'Assign \'question_model\' using a clarifying question as \'question_text\' and the relative multiple choice answers to the question as \'answer_set\'.',
            'The \'question_text\' should be formed to include the issue\'s topic: {0}, and this subtopic: {1} and addressing the user\'s issue.'.format(self.topic, self.subtopic),
            'The goal is to determine which topic most closely matches the user\'s issue.',
            'Never include an answer being some form of the following; \'Other\', \'Not Certain\' or \'None\' as one of the \'answer_set\' answers.',
            'The amount of answers in \'answer_set\' should be between 2 to 5 answers, which prioritize answers clarifying the related topic observation the most. It\'s preferable that there would be more answers, up to 5.',
            'Each \'answer_text\' values should only be a couple words long, maximum 4.',
            'Assign each \'answer_set\' value: \'associated_copilot_flow\' as the closest matching value for the field: \'associated_copilot_flow\' from each object from the \'topic_list\'.',
        ])
        return instructions
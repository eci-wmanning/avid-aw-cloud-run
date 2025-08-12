from utils import log, EnvConfig, BuildEnv
from typing import List, Optional, Any
from openai import AsyncAzureOpenAI
import asyncio
from models import AIResponseFormatModel


class AIResource:
    '''
    https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/structured-outputs?tabs=python
    '''
    connected: bool = False
        
    def __init__(self, system_instructions: List[str] | None = None,) -> None:
        self.system_instructions: List[str] | None = system_instructions
        self.system_instruction_set: List[dict]
        self.env_config = EnvConfig(env=BuildEnv.dev.value)
        try:
            self.chat_client = AsyncAzureOpenAI(
                api_key=self.env_config.azure_ai_api_key,  
                api_version=self.env_config.azure_ai_version,
                azure_endpoint=self.env_config.azure_ai_endpoint, max_retries=2
            )
        except:
            self.connected = False
        else:
            self.connected = True
    async def assign_system_instruction_set(self, system_prompt: List[str], topic_instructions: Optional[List[str]] = None):
                    
        self.system_instructions = system_prompt
                
        log(processing_system_instructions='...')
        ai_response = self.chat_client.beta.chat.completions.stream(
            model=self.env_config.azure_ai_deployment_name,
            messages=[
                {"role": "system",
                "content": ' '.join(system_prompt)},
                {"role": "system",
                "content": ' '.join(topic_instructions if topic_instructions else [""])}]
            )
        return

    def assign_system_instructions(self, system_prompt: List[str]):
                    
        self.system_instructions = system_prompt
                
        ai_response = self.chat_client.beta.chat.completions.parse(
            model=self.env_config.azure_ai_deployment_name,
            messages=[
                {"role": "system",
                "content": ' '.join(system_prompt)},]
            )
        return

    async def get_typed_structured_response(self, user_prompt: List[str], system_prompt: List[str] = [], response_format: type = AIResponseFormatModel) -> Any | None:
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
            self.assign_system_instructions(system_prompt=system_prompt)
            ai_response = await self.chat_client.beta.chat.completions.parse(
                model=self.env_config.azure_ai_deployment_name,
                messages=[
                    {"role": "system",
                    "content": ' '.join(system_prompt)},
                    {"role": "user",
                    "content": ' '.join(user_prompt)},],
                response_format=response_format
                )
            return ai_response.choices[0].message.parsed
            # print(ai_response)
        else:
            return None
            
                
    async def get_structured_response(self, user_prompt: List[str], system_prompt: List[str] = [], topic_instructions: List[str] = []) -> AIResponseFormatModel | None:
        """
        Generatively fills request model, requires first providing the model to be filled.

        Args:
            system_prompt (List[str]): The initial instructions if different than the provided instruction used for class instantiation. Joins to one string 
            user_prompt (List[str]): The current input to be processed. Joins to one string

        Returns:
            AIResponseFormatModel | None: The model format to be returned, wherein some or all is generatively filled
        """
        if self.connected:
            self.assign_system_instructions(system_prompt=system_prompt)
            ai_response = await self.chat_client.beta.chat.completions.parse(
                model=self.env_config.azure_ai_deployment_name,
                messages=[
                    {"role": "system",
                    "content": ' '.join(topic_instructions)},
                    {"role": "system",
                    "content": ' '.join(system_prompt)},
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
            self.assign_system_instructions(system_prompt=system_prompt)
            ai_response = await self.chat_client.chat.completions.create(
                model=self.env_config.azure_ai_deployment_name,
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
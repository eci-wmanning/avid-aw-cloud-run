from enum import Enum
from utils import log
import os
from typing import Optional
from dotenv import dotenv_values


class BuildEnv(Enum):
    
    dev = "DEV"
    stage = "STAGE"
    prod = "PROD"
    test = "TEST"
            
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
        self.env_config = dotenv_values(".env")
        log(assigning_build_env=self.build_env.value)
            
        match self.build_env:
            case BuildEnv.dev:
                self.project_id = self.env_config['DEV_PROJECT_ID']
            case BuildEnv.stage:
                self.project_id = self.env_config['PROD_PROJECT_ID']
            case BuildEnv.prod:
                self.project_id = self.env_config['PROD_PROJECT_ID']
            case None:
                self.project_id = self.env_config['DEV_PROJECT_ID']
                    
        self.env_prefix = self.build_env.value + "_"
        # self.azure_ai_api_key = dotenv_values('AZURE_AI_API_KEY')
        # self.azure_ai_endpoint = dotenv_values('AZURE_AI_ENDPOINT', 'https://ai-avidwarrantyhubuswest502033965267.openai.azure.com')
        # self.azure_ai_deployment_name = dotenv_values('AZURE_AI_AZURE_AI_DEPLOYMENT_NAME', 'gpt-4o')
        # self.azure_ai_model_name = dotenv_values('AZURE_AI_MODEL_NAME', 'gpt-4o')
        # self.azure_ai_version = dotenv_values('AZURE_AI_API_VERSION', '2024-10-21')
        self.azure_ai_api_key = self.env_config['AZURE_AI_API_KEY']
        self.azure_ai_endpoint = self.env_config['AZURE_AI_ENDPOINT']
        self.azure_ai_deployment_name = self.env_config['AZURE_AI_AZURE_AI_DEPLOYMENT_NAME']
        self.azure_ai_model_name =  self.env_config['AZURE_AI_MODEL_NAME']
        self.azure_ai_version =  self.env_config['AZURE_AI_API_VERSION']
        self.firebase_prefix = self.build_env.value.lower() + "_"
        log(azure_ai_api_key=self.azure_ai_api_key)
        
    def env_collection(self, collection_name: str):
        return self.firebase_prefix + collection_name # Ex: dev_azure_data
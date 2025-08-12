from _collections_abc import dict_keys
from dataclasses import dataclass
from typing import Any, Optional, Self

@dataclass
class SchemaModel(object):
    @classmethod
    def from_json(cls, request_json: Any) -> Self:
        # keys = [f.name for f in dataclasses.fields(cls)]
        # json_keys = request_json.keys()
        unexpected_values = []
        expected_keys: dict_keys[str, Any] = cls.__dataclass_fields__.keys()
        tmp = {}
        
        
        for key in expected_keys:
            try:
                # There's probably a better way to do this programmatically
                if key == 'user':
                    tmp[key] = UserSchema.from_json(request_json=request_json[key])
                elif key == 'user_home':
                    tmp[key] = HomeSchema.from_json(request_json=request_json[key])
                elif key == 'system_error_message':
                    tmp[key] = SystemErrorSchema.from_json(request_json=request_json[key])
                elif key =='additional_info':
                    tmp[key] = request_json[key]
                else:
                    tmp[key] = request_json[key]
            except KeyError:
                tmp[key] = None
            except AttributeError:
                pass
        
        cls_data: Self = cls(**tmp)
        
        return cls_data

@dataclass
class HomeSchema(SchemaModel): 
    street: Optional[str]  = "Unknown"
    city: Optional[str] = "Unknown"
    state: Optional[str] = "Unknown"
    postal_code: Optional[str] = "Unknown"
    apartment_no: Optional[str] = "Unknown"
    
@dataclass
class UserSchema(SchemaModel):
    user_home: HomeSchema
    user_name: Optional[str] = "Unknown"
    first_name: Optional[str] = "Unknown"
    last_name: Optional[str] = "Unknown"
    phone_number: Optional[str] = "Unknown"
    mobile_phone_number: Optional[str] = "Unknown"

@dataclass
class SystemErrorSchema(SchemaModel):
    error_message: Optional[str]
    error_code: Optional[str]
    error_count: Optional[str]
    timestamp: Optional[str]
    
    
@dataclass
class RequestSchema(SchemaModel):
    user_request_text: Optional[str]
    mention_users: Optional[bool]
    topic: Optional[str]
    subtopic: Optional[str]
    session_id: Optional[str]
    system_error_message: SystemErrorSchema
    build_env: Optional[str]
    timestamp: Optional[str]
    additional_text: Optional[str]
    request_origin: Optional[str]
    verbose: Optional[bool]
    user: UserSchema
    additional_info: list[Any]
"""
Install the Google AI Python SDK

$ pip install google-generativeai

See the getting started guide for more information:
https://ai.google.dev/gemini-api/docs/get-started/python
"""

import os
import json
import google.generativeai as genai

from typing import Any, List, Optional, Type, TypeVar
from pydantic import BaseModel, Field, field_validator, validator
from bot.features.LLM.config import auto_find_command_prompt_gemini

class moderation_schema(BaseModel):
    abuse_probability: int = Field(0, ge=0, le=10, description="The probability of the user abusing the command")
    spam_probability: int = Field(0, ge=0, le=10, description="The probability of the user spamming the command")
    useless_probability: int = Field(0, ge=0, le=10, description="The probability of the user wasting time")
    ban_probability: int = Field(0, ge=0, le=10, description="The probability that the user should be banned")

    class Config:
        extra = "allow"

class get_command_schema(BaseModel):
    thinking: str = Field("", description="What is your thought process behind the user input? What is the user trying to convey?")
    moderation: moderation_schema = Field(moderation_schema(), description="Moderation probabilities")
    matched_command: str = Field("", description="What command did you find the most suitable?")
    matched_subcommand: Optional[str] = Field(None, description="Was there any subcommand that matched the user input?")
    match_probability: int = Field(0, ge=0, le=10, description="The probability of the command matching the user input")
    matched_command_parameters: List[str] = Field([], description="What are the parameters of the matched command?")
    reasoning: str = Field("", description="What is your reasoning behind the match probability and response?")

    class Config:
        extra = "allow"

    @field_validator('thinking', 'matched_command', 'matched_subcommand', 'reasoning', mode="before")
    def validate_string_fields(cls, v):
        return str(v) if v is not None else ""

    @field_validator('match_probability', mode="before")
    def validate_match_probability(cls, v):
        try:
            v = int(v)
            return max(0, min(v, 10))
        except (ValueError, TypeError):
            return 0

    @field_validator('matched_command_parameters', mode="before")
    def validate_matched_command_parameters(cls, v):
        if isinstance(v, list):
            return [str(item) for item in v if item is not None]
        return []

    @field_validator('moderation', mode="before")
    def validate_moderation(cls, v):
        if isinstance(v, dict):
            try:
                return moderation_schema(**v)
            except:
                pass
        return moderation_schema()

    @classmethod
    def validate_and_parse(cls, data: dict) -> 'get_command_schema':
        parsed_data = {}
        for field, field_info in cls.__fields__.items():
            if field in data:
                try:
                    parsed_data[field] = field_info.type_(data[field])
                except:
                    parsed_data[field] = field_info.default
            else:
                parsed_data[field] = field_info.default
        return cls(**parsed_data)

T = TypeVar('T', bound=BaseModel)
genai.configure(api_key=os.environ["GEMINI_API_KEY"])

class GeminiConfig(BaseModel):
    temperature: float = 0.7
    top_p: float = 0.95
    top_k: int = 64
    max_output_tokens: int = 8192
    response_mime_type: str = "application/json"

class GeminiLLM:
    def __init__(self, config: GeminiConfig = GeminiConfig()):
        self.model: genai.GenerativeModel = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            generation_config=config.model_dump()
        )

    async def generate_json(self, user_input: str, prompt: str) -> Any:
        chat = self.model.start_chat(
            history=[
                {
                    "role": "user",
                    "parts": [
                        prompt,
                    ],
                }
            ]
        )
        response = await chat.send_message_async(user_input)
        return response

async def get_closest_command(user_input: str, user_role: str, user_id: int, commands: dict, llm=GeminiLLM()):
    prompt = auto_find_command_prompt_gemini(user_input, user_role, user_id, commands)
    response = await llm.generate_json(user_input, prompt)
    response = json.loads(response.text, strict=False)
    try:
        response = get_command_schema(**response)
    except Exception as e:
        print(e)
    return response
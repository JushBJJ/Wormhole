
import os
import instructor

from typing import Any, Optional, Type, TypeVar
from openai import AsyncOpenAI as OpenAI
from pydantic import BaseModel, Field
from bot.features.LLM.config import auto_find_command_prompt

T = TypeVar('T', bound=BaseModel)


class OllamaConfig(BaseModel):
    base_url: str = "http://localhost:11434/v1"
    api_key: str = "yo mama so fat she can't even fit in the API key field"
    mode: instructor.Mode = instructor.Mode.JSON_SCHEMA
    default_model: str = "llama3:8b"
    

class TogetherAIConfig(BaseModel):
    base_url: str = "https://api.together.xyz/v1"
    api_key: str = os.getenv("TOGETHER_API_KEY")
    mode: instructor.Mode = instructor.Mode.JSON_SCHEMA
    default_model: str = "mistralai/Mixtral-8x7B-Instruct-v0.1"


class OllamaLLM:
    def __init__(self, config: OllamaConfig = OllamaConfig()):
        self.config = config
        self.client = instructor.from_openai(
            OpenAI(
                base_url=self.config.base_url,
                api_key=self.config.api_key
            ),
            mode=self.config.mode
        )

    async def generate_json(self, prompt: str, model: Optional[str] = None, response_schema: Optional[Type[T]] = None,  **kwargs) -> Any:
        messages = [{"role": "user", "content": prompt}]
        response = await self.client.chat.completions.create(
            model=model or self.config.default_model,
            messages=messages,
            response_model=response_schema,
            **kwargs
        )
        return response


class get_command_schema(BaseModel):
    closest_command: str = Field(..., description="The closest command to the user input")
    command_parameters: dict = Field({}, description="The parameters of the command in kwargs")
    command_is_valid: bool = Field(True, description="Whether the command is valid or not.")
    command_exists: bool = Field(True, description="Whether the command exists or not.")
    reasoning: str = Field("", description="The reasoning behind your decision.")
    response_to_user: str = Field("", description="The response to the user.")
    auto_execute_command: bool = Field(False, description="Whether the command should be executed automatically.")
    reasoning_to_execute: str = Field("", description="The reasoning behind executing the command.")

async def get_closest_command(user_input: str, user_role: str, user_id: int, commands: dict, config=OllamaConfig()) -> get_command_schema:
    ollama = OllamaLLM(config)
    prompt = auto_find_command_prompt(user_input, user_role, user_id, commands)
    response = await ollama.generate_json(prompt, response_schema=get_command_schema)
    return response
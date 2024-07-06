
import os
from enum import Enum
import instructor

from typing import Any, Dict, List, Optional, Type, TypeVar
from openai import AsyncOpenAI as OpenAI
from pydantic import BaseModel, Field
from bot.features.LLM.config import auto_find_command_prompt
from bot.commands import admin, general, wormhole
from discord.ext.commands import Command

T = TypeVar('T', bound=BaseModel)


class OllamaConfig(BaseModel):
    base_url: str = "http://localhost:11434/v1"
    api_key: str = "yo mama so fat she can't even fit in the API key field"
    mode: instructor.Mode = instructor.Mode.JSON_SCHEMA
    default_model: str = "llama3:8b-instruct-q6_K"
    

class AnyscaleConfig(BaseModel):
    base_url: str = "https://api.endpoints.anyscale.com/v1"
    api_key: str = os.getenv("ANYSCALE_API_KEY")
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
        messages = [m for m in kwargs.get("messages", [])]
        messages.append({"role": "user", "content": prompt})
        response = await self.client.chat.completions.create(
            model=model or self.config.default_model,
            messages=messages,
            response_model=response_schema
        )
        print(response)
        return response
    
class moderation_schema(BaseModel):
    abuse_probability: int = Field(0, ge=0, le=10, description="The probability of the user abusing the command")
    spam_probability: int = Field(0, ge=0, le=10, description="The probability of the user spamming the command")
    useless_probability: int = Field(0, ge=0, le=10, description="The probability of the user wasting time")
    ban_probability: int = Field(0, ge=0, le=10, description="The probability that the user should be banned")

def generate_command_enum():
    commands = {}
    for module in [general.GeneralCommands, admin.AdminCommands, wormhole.WormholeCommands]:
        for name, member in module.__dict__.items():
            if isinstance(member, Command):
                commands[name] = name
    return Enum('CommandName', commands)


def create_get_command_schema(CommandName):
    class get_command_schema(BaseModel):
        moderation: moderation_schema = Field(..., description="Moderation probabilities")
        matched_command: CommandName = Field(..., description="The command that was matched")
        match_probability: int = Field(0, ge=0, le=10, description="The probability of the command matching the user input")
        matched_command_parameters: List[str] = Field([], description="Command parameters based off user input")
        response_to_user: str = Field("", description="The response to the user")
    
    return get_command_schema

async def get_closest_command(user_input: str, user_role: str, user_id: int, commands: dict, config=OllamaConfig(), **kwargs):
    CommandName = generate_command_enum()
    get_command_schema = create_get_command_schema(CommandName)

    ollama = OllamaLLM(config)
    prompt = auto_find_command_prompt(user_input, user_role, user_id, commands)
    response = await ollama.generate_json(prompt, response_schema=get_command_schema)
    return response
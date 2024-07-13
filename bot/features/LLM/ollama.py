import asyncio
import hashlib
import os
import discord
import instructor
import ollama
from ollama import AsyncClient

from typing import Any, Dict, List, Optional, Set, Tuple, Type, TypeVar
from openai import AsyncOpenAI as OpenAI
from pydantic import BaseModel, Field
from bot.features.LLM.config import auto_find_command_prompt
from bot.features.LLM.moderation.prompt import eval_prompt
from bot.commands import admin, general, wormhole
from discord.ext.commands import Command, Group
from discord.ui import Button, View, Modal, TextInput
from enum import Enum

from services.discord import DiscordBot

T = TypeVar('T', bound=BaseModel)


class OllamaConfig(BaseModel):
    base_url: str = os.getenv("OLLAMA_BASE_URL", "")
    api_key: str = "yo mama so fat she can't even fit in the API key field"
    mode: instructor.Mode = instructor.Mode.JSON_SCHEMA
    default_model: str = "mistral:7b-instruct-v0.3-q6_K"
    

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

    async def generate_json(self, user_input: str, model: Optional[str] = None, response_schema: Optional[Type[T]] = None,  **kwargs) -> Any:
        messages = [m for m in kwargs.get("messages", [])]
        messages.append({"role": "user", "content": user_input})
        client = self.client.client
        response = await client.chat.completions.create(
            model=model or self.config.default_model,
            messages=messages
        )
        return response
    
class moderation_schema(BaseModel):
    abuse_probability: int = Field(..., ge=0, le=10, description="The probability of the user abusing the command")
    spam_probability: int = Field(..., ge=0, le=10, description="The probability of the user spamming the command")
    useless_probability: int = Field(..., ge=0, le=10, description="The probability of the user wasting time")
    ban_probability: int = Field(..., ge=0, le=10, description="The probability that the user should be banned")

class CorrectionModal(Modal):
    def __init__(self, bot, hash_id):
        super().__init__(title="Provide Correct Response")
        self.bot = bot
        self.hash_id = hash_id
        self.correct_response = TextInput(label="Correct Response", style=discord.TextStyle.paragraph)
        self.add_item(self.correct_response)

    async def on_submit(self, interaction: discord.Interaction):
        self.bot.evaluations[self.hash_id]["correct_response"] = self.correct_response.value
        hash_id, predicted, actual = _process_evaluation(self.hash_id, self.bot.evaluations[self.hash_id])
        await self.bot.config.add_data(hash_id, predicted, actual)
        await interaction.response.send_message("Correct response recorded. Thank you!", ephemeral=True)

def generate_command_enum():
    commands = {}
    sub_commands = {}

    def add_command(name, command):
        if isinstance(command, Group):
            commands[name] = name
            for subcmd in command.commands:
                full_name = f"{name} {subcmd.name}"
                sub_commands[full_name] = full_name
        elif isinstance(command, Command):
            commands[name] = name

    for module in [general.GeneralCommands, admin.AdminCommands, wormhole.WormholeCommands]:
        for name, member in module.__dict__.items():
            if isinstance(member, (Command, Group)):
                add_command(name, member)

    return Enum('CommandName', commands), Enum('CommandName', sub_commands)

def create_get_command_schema(CommandName, SubCommandName):
    class get_command_schema(BaseModel):
        thinking: str = Field(..., description="What is your thought process behind the user input? What is the user trying to convey?")
        moderation: moderation_schema = Field(..., description="Moderation probabilities")
        matched_command: str = Field(..., description="What command did you find the most suitable?")
        matched_subcommand: Optional[str] = Field(..., description="Was there any subcommand that matched the user input?")
        match_probability: int = Field(..., ge=0, le=10, description="The probability of the command matching the user input")
        matched_command_parameters: List[str] = Field(..., description="What are the parameters of the matched command?")
        reasoning: str = Field(..., description="What is your reasoning behind the match probability and response?")
    
    return get_command_schema

async def get_closest_command(user_input: str, user_role: str, user_id: int, commands: dict, config=OllamaConfig(), **kwargs):
    CommandName, SubCommandName = generate_command_enum()
    get_command_schema = create_get_command_schema(CommandName, SubCommandName)

    ollama = OllamaLLM(config)
    prompt = auto_find_command_prompt(user_input, user_role, user_id, commands)
    response = await ollama.generate_json(prompt, response_schema=get_command_schema)
    return response

def _format_message(msgs: List[str]) -> str:
    return "\n".join(
        f"{k}: {v}" for m in msgs
        for k, v in {
            "Time since last message": m[2],
            m[1]: m[0]
        }.items()
    )

def _process_evaluation(hash_id: int, evaluation: dict) -> Tuple[str, str, str]:
    if evaluation["result"] == "Yes":
        actual = [{"role": "user", "content": evaluation["prompt"]}, {"role": "assistant", "content": evaluation["response"]}]
        predicted = actual
    elif evaluation["result"] == "No":
        actual = [{"role": "user", "content": evaluation["prompt"]}, {"role": "assistant", "content": evaluation["correct_response"]}]
        predicted = [{"role": "user", "content": evaluation["prompt"]}, {"role": "assistant", "content": evaluation["response"]}]
    return str(hash_id), str(predicted), str(actual)

async def moderate_channel(bot: DiscordBot, message: discord.Message, messages: Dict[str, Set[str]], config=OllamaConfig()):
    tasks = set()
    prompts = set()
    msgs_list = set()
    new_messages = messages.copy()
    for channel, msgs in messages.items():
        bot.logger.info(f"{channel}: {len(msgs)}")
        if len(msgs) >= 5:
            prompt = eval_prompt(channel, msgs)
            msgs_list.add(_format_message(msgs))
            msg = [{"role": "user", "content": prompt}]
            prompts.add(msg[0]["content"])
            tasks.add(AsyncClient(host="http://ollama:11434").chat(model="mistral:7b-instruct-v0.3-q6_K", messages=msg, format="json"))
            new_messages[channel] = set()
    responses = await asyncio.gather(*tasks)
    messages.clear()
    messages.update(new_messages)
    bot.logger.info(responses)

    user = await bot.fetch_user(os.getenv("OWNER_ID", 0))
    eval_tasks = set()
    
    for r, prompt, msg in zip(responses, prompts, msgs_list):
        view = View()
        view.add_item(Button(style=discord.ButtonStyle.success, label="Yes", custom_id="Yes"))
        view.add_item(Button(style=discord.ButtonStyle.danger, label="No", custom_id="No"))
        view.add_item(Button(style=discord.ButtonStyle.secondary, label="Skip", custom_id="Skip"))
        
        response = r["message"]["content"]
        content = f"# Messages\n```{msg[:1800]}```\n# Response:\n```{response}```"
        content = content[:2000]
        hashed_content = hash(content)
        bot.evaluations[hashed_content] = {
            "content": content,
            "prompt": prompt,
            "response": response
        }
        eval_tasks.add(user.send(content=content, view=view))
    
    await asyncio.gather(*eval_tasks)

    @bot.event
    async def on_interaction(interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data["custom_id"]
            message_content = interaction.message.content
            hash_id = hash(message_content)
            
            if hash_id in bot.evaluations:
                evaluation = bot.evaluations[hash_id]
                new_view = View()
                for button in interaction.message.components[0].children:
                    new_button = Button(
                        style=button.style,
                        label=button.label,
                        custom_id=button.custom_id,
                        disabled=True
                    )
                    new_view.add_item(new_button)
                
                if custom_id == "Yes":
                    evaluation["result"] = "Yes"
                    hash_id, predicted, actual = _process_evaluation(hash_id, evaluation)
                    await bot.config.add_data(hash_id, predicted, actual)
                    await interaction.response.send_message("Evaluation recorded: Yes", ephemeral=True)
                elif custom_id == "No":
                    evaluation["result"] = "No"
                    await interaction.response.send_modal(CorrectionModal(bot, hash_id))
                elif custom_id == "Skip":
                    evaluation["result"] = "Skip"
                    await interaction.response.send_message("Evaluation skipped", ephemeral=True)
                await interaction.message.edit(view=new_view)
from typing import Any, Dict
import outlines

@outlines.prompt
def auto_find_command_prompt(user_input: str, user_role: str, user_id: int, commands: Dict[str, Any]):
    """
    These are the commands you personally serve:
    ```
    {% for name, command in commands.items() %}
    {{ name }}:
        Description: {{ command.help if command.help else "No description available" }}
        Parameters:
            {% if command.clean_params %}
                {% for param in command.clean_params.values() %}
            - `{{ param.name }}`{% if param.default != param.empty %} (Optional){% else %} (Required){% endif %}
                {% endfor %}
            {% else %}
            None
            {% endif %}
    {% endfor %}
    ```

    Think of their natural language as an easier way for users to execute commands.
    Just be smart overall on your judgements.
    
    If they are asking you what is your info, you obviously do the `info` command.
    If they are asking you what is your commands, you obviously do the `help` command.
    
    Do not ban/unban anyone if the user role is not Admin.
    Do not admin/unadmin anyone if the user role is not Admin.

    What constitutes as abuse:
    - The user sends commands that could overwhelm the bot's processing capacity (e.g., very long or complex prompts)
    - The user attempts to make the bot perform harmful or unethical actions
    - The user uses offensive language or personal attacks in their commands
    - The user tries to extract sensitive information about the bot or its creators

    What constitutes as spam:
    - The user sends the exact same command or message multiple times in quick succession
    - The user sends a large number of slightly varied but essentially identical commands
    - The user floods the channel with messages that don't contain valid commands
    - The user sends messages with excessive use of mentions, emojis, or formatting to draw attention

    What constitutes as useless:
    - The user sends commands that are clearly nonsensical or gibberish
    - The user sends messages that don't contain any recognizable commands or queries
    - The user repeatedly sends "test" messages or similar content with no apparent purpose
    - The user sends messages that are entirely off-topic for the bot's intended use

    What constitutes as a ban:
    - The user accumulates a certain number of abuse, spam, or useless infractions within a set timeframe
    - The user persists in any of the above behaviors after receiving warnings
    - The user attempts to circumvent moderation by creating alternate accounts
    - The user deliberately tries to crash or break the bot's functionality
    
    Don't match a command that doesn't exist, or else the bot will throw an error.

    This is what the user said: \"{{ user_input[1:] }}\"
    This is the user's role: \"{{ user_role }}\"
    This is the user's ID: \"{{ user_id }}\"
    """
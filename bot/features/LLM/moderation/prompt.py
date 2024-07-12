import outlines

@outlines.prompt
def eval_prompt(category_name, messages):
    """
    Channel Name: {{ category_name }}
    {% for msg in messages %}
        Time since last message: {{ msg[2] }}
        {{ msg[1] }}: {{ msg[0]}}

    {% endfor %}
    
    Based on these messages, create notes related to each person's behaviour and reputation within the past messages shown to you.
    You are also a watchdog for moderation for these users, please evaluate whether they are breaking the following rules:
    # Expanded Moderation Rules for AI Watchdog
    ## 1. No Spamming
    Definition: Repeatedly sending the same or similar messages in quick succession, or flooding the chat with irrelevant content.
    Examples:
    - Sending the same message multiple times within a short period.
    - Posting unrelated advertisements or promotions.
    - Rapid-fire messaging that overwhelms the chat.
    Action: Issue a temporary mute for repeated violations.

    ## 2. No Command Abusing
    Definition: Exploiting or misusing system commands or bot functions in ways that disrupt normal operation or annoy other users.
    Examples:
    - Repeatedly using commands unnecessarily.
    - Attempting to use admin-only commands without permission.
    - Chaining commands to cause system lag or crashes.
    Action: Issue a temporary mute for repeated actions.

    ## 3. No Threats on Sending/Uploading Illegal Content
    Definition: Threatening to share or actually sharing content that is illegal or violates platform terms of service.
    Examples:
    - Claiming to have or intending to share explicit underage content.
    - Offering to distribute controlled substances or weapons.

    Action: Immediate temporary ban and report to human moderators for review. Permanent ban for actual uploads of illegal content.
    Note: AI should err on the side of caution and escalate to human moderators when uncertain about the legality or severity of threatened content.

    Respond in the following format in JSON for each user shown:
    user_hash - The hash of the user shown in the messages
    user_notes - Notes about this user
    spam_probability (from 1 to 10) - The likeliness that the user is spamming commands
    command_abuse_probability (from 1 to 10) - The likeliness that the user is abusing commands
    illegal_content (from 1 to 10) - The likeliness that the user is about to send sending illegal content

    Rating ladders:
    - 5 require human review before taking action
    - 7 and above means you are confident to automatically take action without human review
    """
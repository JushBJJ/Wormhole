import discord
from bot.config import WormholeConfig
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

class PrettyMessage:
    def __init__(self, config: WormholeConfig):
        self.config = config
    
    async def to_embed( self, 
                        user_id: int, 
                        display_name: str,
                        avatar: str,
                        message: str
        ) -> discord.Embed:

        user_id = str(user_id)
        user_color = await self.config.get_user_color(user_id)
        user_hash = await self.config.get_user_hash(user_id)
        embed = discord.Embed(
            description = message,
            color = user_color
        )
        embed.set_author(name=display_name, icon_url=avatar)
        embed.set_footer(text=f"{user_hash}")
        return embed
    
    def to_attachments_message(self, attachments: list) -> str:
        if not attachments:
            return ""
        
        attachment_urls = [attachment.url for attachment in attachments]
        return "\n".join(attachment_urls)
    
    def embeds_to_links(self, embeds: list) -> str:
        if not embeds:
            return ""

        embed_urls = [embed.url or "" for embed in embeds]
        return "\n".join(embed_urls)

    async def handle_stickers(self, message: discord.Message) -> tuple:
        stickers_to_send = []
        content_addition = ""
        
        for sticker in message.stickers:
            try:
                if sticker.format.name=="lottie":
                    stickers_to_send.append(sticker)
                else:
                    content_addition+=sticker.url
            except discord.NotFound:
                content_addition += f"\n[Unknown sticker: {sticker.name}]"
            except discord.Forbidden:
                content_addition += f"\n[No permission to use sticker: {sticker.name}]"
            except Exception as e:
                content_addition += f"\n[Error with sticker {sticker.name}: {str(e)}]"
        
        return stickers_to_send, content_addition
    
    def create_rich_message_box(self, author, content, attachments, user_id, console_width=None):
        min_width = len(user_id)

        if console_width and console_width < min_width:
            width = console_width
        else:
            width = max(min_width, console_width or 0)
        
        console = Console(width=width)
        table = Table(show_header=False, show_edge=False, pad_edge=True, box=None)
        table.add_column("Content", style="cyan", no_wrap=True, min_width=width, max_width=width+len(content))
        table.add_row(content)
        if attachments:
            table.add_row("")
            table.add_row("[bold]Attachments:[/bold]")
            for attachment in attachments:
                table.add_row(attachment)

        message_panel = Panel(
            table,
            title=f"[bold yellow]{author}[/bold yellow]",
            subtitle=f"[dim]{user_id}[/dim]",
            expand=False,
            border_style="blue"
        )
        console.print(message_panel)
        console.print()
    
    def format_mentions(self, mentions: list) -> str:
        if not mentions:
            return ""
        
        mention_strings = [f"<@{mention}>" for mention in mentions]
        return " ".join(mention_strings)
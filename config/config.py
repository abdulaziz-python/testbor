import os
from dataclasses import dataclass
from typing import List, Optional
from dotenv import load_dotenv

class ConfigError(Exception):
    pass

@dataclass
class Config:
    bot_token: Optional[str]
    llama_api_token: Optional[str]
    admin_ids: List[int]
    required_channels: List[dict]

def load_config() -> Config:
    load_dotenv()

    bot_token = os.getenv('BOT_TOKEN')
    llama_api_token = os.getenv('LLAMA_API_TOKEN')

    admin_ids_str = os.getenv('ADMIN_IDS', '')
    admin_ids = []
    if admin_ids_str:
        try:
            admin_ids = [int(admin_id.strip()) for admin_id in admin_ids_str.split(',') if admin_id.strip()]
        except ValueError:
            raise ConfigError("ADMIN_IDS vergul bilan ajratilgan butun sonlar bo'lishi kerak")

    required_channels = []
    channels_str = os.getenv('REQUIRED_CHANNELS', '@pythonnews_uzbekistan:Python News Uzbekistan,@testbor_c:Testbor Channel')

    for channel_info in channels_str.split(','):
        if ':' in channel_info:
            channel_id, channel_title = channel_info.split(':', 1)
            required_channels.append({"id": channel_id.strip(), "title": channel_title.strip()})

    if not required_channels:
        required_channels = [
            {"id": "@pythonnews_uzbekistan", "title": "Python News Uzbekistan"},
            {"id": "@testbor_c", "title": "Testbor Channel"}
        ]

    return Config(
        bot_token=bot_token,
        llama_api_token=llama_api_token,
        admin_ids=admin_ids,
        required_channels=required_channels
    )

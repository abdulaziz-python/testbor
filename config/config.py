import os
from dataclasses import dataclass, field
from bot.utils.logger import get_logger
from typing import List, Dict

logger = get_logger(__name__)

@dataclass
class Config:
    bot_token: str = "8075757982:AAGJBRILTv4mApRXeBDuBtpJdHoS4aLg0C4"
    admin_ids: List[int] = field(default_factory=lambda: [6236467772, 7795537801, 7632092580])
    crypto_pay_token: str = "366714:AA1CdLN8HkGbSLXyHLQEKUzt7yYpGXDLqZw"
    payment_token: str = "398062629:TEST:999999999_F91D8F69C042267444B74CC0B3C747757EB0E065"
    webhook_url: str = "https://testbor.alwaysdata.net"
    required_channels: List[Dict[str, str]] = field(default_factory=lambda: [
        {"id": "@pythonnews_uzbekistan", "title": "Python Kanali"},
        {"id": "@testbor_c", "title": "TestBor News"}
    ])

def load_config():
    try:
        return Config()
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        raise
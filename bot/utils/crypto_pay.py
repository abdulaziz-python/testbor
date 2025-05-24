import aiohttp
import asyncio
import hmac
import hashlib
from bot.utils.logger import get_logger
from config.config import load_config

logger = get_logger(__name__)
config = load_config()

class CryptoPayAPI:
    def __init__(self):
        self.api_token = config.crypto_pay_token
        self.base_url = "https://pay.send.tg/api/v1"

    async def _make_request(self, method, endpoint, data=None, retries=3):
        headers = {
            "Crypto-Pay-API-Token": self.api_token,
            "Content-Type": "application/json"
        }
        for attempt in range(retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.request(
                        method,
                        f"{self.base_url}{endpoint}",
                        json=data,
                        headers=headers
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"API error: {response.status} - {error_text}")
                            return {"error": error_text}
                        return await response.json()
            except Exception as e:
                logger.error(f"Request error (attempt {attempt + 1}): {e}", exc_info=True)
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    return {"error": str(e)}
        return {"error": "Max retries reached"}

    async def create_invoice(self, **kwargs):
        return await self._make_request("POST", "/invoices", data=kwargs)

    async def get_invoice(self, invoice_id):
        return await self._make_request("GET", f"/invoices/{invoice_id}")

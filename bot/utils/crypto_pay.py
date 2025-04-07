import aiohttp
import logging
import json
from config.config import load_config
from bot.utils.logger import get_logger

logger = get_logger(__name__)

class CryptoPayAPI:
    def __init__(self):
        config = load_config()
        self.api_token = config.crypto_pay_token
        self.base_url = "https://pay.crypt.bot/api"
        self.headers = {
            "Crypto-Pay-API-Token": self.api_token,
            "Content-Type": "application/json"
        }
    
    async def _make_request(self, method, endpoint, params=None):
        url = f"{self.base_url}/{endpoint}"
        logger.info(f"Making {method} request to {endpoint} with params: {params}")
        try:
            async with aiohttp.ClientSession() as session:
                if method == "GET":
                    async with session.get(url, headers=self.headers, params=params) as response:
                        response_text = await response.text()
                        logger.debug(f"Response status: {response.status}, body: {response_text}")
                        
                        if response.status != 200:
                            logger.error(f"HTTP error: {response.status} {response.reason} - {response_text}")
                            return {"error": f"Xatolik: HTTP {response.status} {response.reason} - {response_text[:100]}"}
                        
                        try:
                            result = json.loads(response_text)
                            if not result.get("ok", False):
                                error_msg = result.get("error", {}).get("message", "Noma'lum xatolik")
                                logger.error(f"API error: {error_msg}")
                                return {"error": f"API xatolik: {error_msg}"}
                                
                            logger.info(f"Successful response from {endpoint}")
                            return result.get("result", {})
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON decode error: {e} - Response: {response_text[:100]}")
                            return {"error": f"JSON xatolik: {e}"}
                            
                elif method == "POST":
                    async with session.post(url, headers=self.headers, json=params) as response:
                        response_text = await response.text()
                        logger.debug(f"Response status: {response.status}, body: {response_text}")
                        
                        if response.status != 200:
                            logger.error(f"HTTP error: {response.status} {response.reason} - {response_text}")
                            return {"error": f"Xatolik: HTTP {response.status} {response.reason} - {response_text[:100]}"}
                        
                        try:
                            result = json.loads(response_text)
                            if not result.get("ok", False):
                                error_msg = result.get("error", {}).get("message", "Noma'lum xatolik")
                                error_code = result.get("error", {}).get("code", "unknown")
                                logger.error(f"API error: Code {error_code} - {error_msg}")
                                return {"error": f"API xatolik: {error_msg} (kod: {error_code})"}
                                
                            logger.info(f"Successful response from {endpoint}")
                            return result.get("result", {})
                        except json.JSONDecodeError as e:
                            logger.error(f"JSON decode error: {e} - Response: {response_text[:100]}")
                            return {"error": f"JSON xatolik: {e}"}
                else:
                    logger.error(f"Unsupported HTTP method: {method}")
                    return {"error": "Qo'llanilmaydigan HTTP metodi"}
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error: {e}")
            return {"error": f"Ulanish xatoligi: {e}"}
        except Exception as e:
            logger.error(f"Unexpected error in _make_request: {e}")
            return {"error": f"Umumiy xatolik: {e}"}
    
    async def get_me(self):
        """Bot haqida ma'lumotni olish"""
        try:
            logger.info("Requesting bot info (getMe)")
            return await self._make_request("GET", "getMe")
        except Exception as e:
            logger.error(f"Error in get_me: {e}")
            return {"error": f"getMe xatoligi: {e}"}
    
    async def create_invoice(self, asset, amount, description=None, hidden_message=None, 
                            paid_btn_name=None, paid_btn_url=None, payload=None, 
                            allow_comments=None, allow_anonymous=None, expires_in=None):
        """To'lov yaratish"""
        try:
            params = {
                "asset": asset,
                "amount": amount
            }
            
            if description:
                params["description"] = description
            if hidden_message:
                params["hidden_message"] = hidden_message
            if paid_btn_name:
                params["paid_btn_name"] = paid_btn_name
            if paid_btn_url:
                params["paid_btn_url"] = paid_btn_url
            if payload:
                params["payload"] = payload
            if allow_comments is not None:
                params["allow_comments"] = allow_comments
            if allow_anonymous is not None:
                params["allow_anonymous"] = allow_anonymous
            if expires_in:
                params["expires_in"] = expires_in
            
            logger.info(f"Creating invoice: asset={asset}, amount={amount}, payload={payload}")
            result = await self._make_request("POST", "createInvoice", params)
            
            if "error" in result:
                logger.error(f"Error creating invoice: {result['error']}")
                return result
            
            logger.info(f"Invoice created successfully: {result.get('invoice_id', 'unknown')}")
            return result
        except Exception as e:
            logger.error(f"Error in create_invoice: {e}")
            return {"error": f"Invoice yaratish xatoligi: {e}"}
    
    async def get_invoices(self, asset=None, invoice_ids=None, status=None, offset=None, count=None):
        """Invoice'larni olish"""
        try:
            params = {}
            if asset:
                params["asset"] = asset
            if invoice_ids:
                params["invoice_ids"] = invoice_ids
            if status:
                params["status"] = status
            if offset:
                params["offset"] = offset
            if count:
                params["count"] = count
            
            logger.info(f"Getting invoices with params: {params}")
            return await self._make_request("GET", "getInvoices", params)
        except Exception as e:
            logger.error(f"Error in get_invoices: {e}")
            return {"error": f"Invoicelar olish xatoligi: {e}"}
    
    async def get_balance(self):
        """Balansni tekshirish"""
        try:
            logger.info("Requesting balance")
            return await self._make_request("GET", "getBalance")
        except Exception as e:
            logger.error(f"Error in get_balance: {e}")
            return {"error": f"Balans tekshirish xatoligi: {e}"}
    
    async def transfer(self, user_id, asset, amount, spend_id=None, comment=None, disable_send_notification=None):
        """Pul o'tkazish"""
        try:
            params = {
                "user_id": user_id,
                "asset": asset,
                "amount": amount
            }
            
            if spend_id:
                params["spend_id"] = spend_id
            if comment:
                params["comment"] = comment
            if disable_send_notification is not None:
                params["disable_send_notification"] = disable_send_notification
            
            logger.info(f"Transferring {amount} {asset} to user {user_id}")
            return await self._make_request("POST", "transfer", params)
        except Exception as e:
            logger.error(f"Error in transfer: {e}")
            return {"error": f"Transfer xatoligi: {e}"}
    
    async def set_webhook(self, url):
        """Webhook o'rnatish"""
        try:
            logger.info(f"Setting webhook to: {url}")
            params = {"url": url}
            result = await self._make_request("POST", "setWebhook", params)
            if "error" in result:
                logger.error(f"Error setting webhook: {result['error']}")
                return False, result['error']
            logger.info("Webhook set successfully")
            return True, result
        except Exception as e:
            logger.error(f"Error in set_webhook: {e}")
            return False, str(e)
    
    async def delete_webhook(self):
        """Webhookni o'chirish"""
        try:
            logger.info("Deleting webhook")
            result = await self._make_request("POST", "deleteWebhook", {})
            if "error" in result:
                logger.error(f"Error deleting webhook: {result['error']}")
                return False, result['error']
            logger.info("Webhook deleted successfully")
            return True, result
        except Exception as e:
            logger.error(f"Error in delete_webhook: {e}")
            return False, str(e)
    
    async def get_webhook_info(self):
        """Webhook ma'lumotlarini olish"""
        try:
            logger.info("Getting webhook info")
            return await self._make_request("GET", "getWebhookInfo")
        except Exception as e:
            logger.error(f"Error in get_webhook_info: {e}")
            return {"error": f"Webhook ma'lumotlarini olish xatoligi: {e}"}
    
    # Xavfsizlik
    def verify_webhook(self, init_data):
        """Webhook ma'lumotlarini tekshirish"""
        # Bu funksiya webhook hodisalari authenticate qilish uchun
        # Hozircha boshlang'ich versiya
        return True

# Qisqa test uchun funksiya
async def test_crypto_pay():
    """CryptoPay API ishlashini tekshirish"""
    try:
        logger.info("Testing CryptoPay API")
        api = CryptoPayAPI()
        me_result = await api.get_me()
        
        if "error" in me_result:
            logger.error(f"CryptoPay API test failed: {me_result['error']}")
            return False, me_result['error']
        
        balance_result = await api.get_balance()
        if "error" in balance_result:
            logger.error(f"CryptoPay balance test failed: {balance_result['error']}")
            return False, balance_result['error']
        
        logger.info(f"CryptoPay API test successful: {me_result}")
        return True, me_result
    except Exception as e:
        logger.error(f"CryptoPay API test exception: {e}")
        return False, str(e) 
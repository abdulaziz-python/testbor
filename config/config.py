import os
from dotenv import load_dotenv

def load_config():
    load_dotenv()
    return {
        "bot_token": os.getenv("BOT_TOKEN"),
        "payment_token": os.getenv("PAYMENT_TOKEN"),
        "crypto_pay_token": os.getenv("CRYPTO_PAY_TOKEN", "366714:AAUG4V33VbFnikaLHQLGkHi0mGaN5likipo "),
        "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", "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"),
        "db_host": os.getenv("DB_HOST", "localhost"),
        "db_port": int(os.getenv("DB_PORT", 5432)),
        "db_name": os.getenv("DB_NAME", "testbor"),
        "db_user": os.getenv("DB_USER", "postgres"),
        "db_password": os.getenv("DB_PASSWORD", ""),
        "admin_ids": [int(x) for x in os.getenv("ADMIN_IDS").split(",") if x],
        "required_channels": [
            {"name": channel_name, "id": int(channel_id), "url": channel_url}
            for channel_name, channel_id, channel_url in [
                x.split(":") for x in os.getenv("REQUIRED_CHANNELS").split(";") if x
            ]
        ],
        "webhook_domain": os.getenv("WEBHOOK_DOMAIN"),
        "webhook_path": os.getenv("WEBHOOK_PATH", "/webhook"),
        "webserver_host": os.getenv("WEBSERVER_HOST", "0.0.0.0"),
        "webserver_port": int(os.getenv("WEBSERVER_PORT", 8443)),
        "ssl_cert": os.getenv("SSL_CERT", ""),
        "ssl_key": os.getenv("SSL_KEY", "")
    }

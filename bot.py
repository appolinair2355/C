"""
Telegram Bot implementation with advanced features and deployment capabilities
"""
import os
import logging
import requests
import json
from typing import Dict, Any
from handlers import TelegramHandlers
from card_predictor import card_predictor

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.deployment_file_path = "deployment_package_complete.zip"
        # Initialize advanced handlers
        self.handlers = TelegramHandlers(token)

    def handle_update(self, update: Dict[str, Any]) -> None:
        """Handle incoming Telegram update with advanced features for webhook mode"""
        try:
            # Log avec type de message
            if 'message' in update:
                logger.info(f"🔄 Bot traite message normal via webhook")
            elif 'edited_message' in update:
                logger.info(f"🔄 Bot traite message édité via webhook")
            
            logger.info(f"Received update: {json.dumps(update, indent=2)}")

            # Use the advanced handlers for processing (they handle card predictions too)
            self.handlers.handle_update(update)
            
            # Log succès du traitement
            logger.info(f"✅ Update traité avec succès via webhook")

        except Exception as e:
            logger.error(f"❌ Error handling update via webhook: {e}")

    def send_message(self, chat_id: int, text: str) -> bool:
        """Send text message to user"""
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'HTML'
            }

            response = requests.post(url, json=data, timeout=10)
            result = response.json()

            if result.get('ok'):
                logger.info(f"Message sent successfully to chat {chat_id}")
                return True
            else:
                logger.error(f"Failed to send message: {result}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error sending message: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    def send_document(self, chat_id: int, file_path: str) -> bool:
        """Send document file to user"""
        try:
            url = f"{self.base_url}/sendDocument"

            with open(file_path, 'rb') as file:
                files = {
                    'document': (os.path.basename(file_path), file, 'application/zip')
                }
                data = {
                    'chat_id': chat_id,
                    'caption': '📦 Deployment Package for render.com'
                }

                response = requests.post(url, data=data, files=files, timeout=60)
                result = response.json()

                if result.get('ok'):
                    logger.info(f"Document sent successfully to chat {chat_id}")
                    return True
                else:
                    logger.error(f"Failed to send document: {result}")
                    return False

        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error sending document: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending document: {e}")
            return False

    def set_webhook(self, webhook_url: str) -> bool:
        """Set webhook URL for the bot"""
        try:
            url = f"{self.base_url}/setWebhook"
            data = {
                'url': webhook_url,
                'allowed_updates': ['message', 'edited_message']
            }

            response = requests.post(url, json=data, timeout=10)
            result = response.json()

            if result.get('ok'):
                logger.info(f"Webhook set successfully: {webhook_url}")
                return True
            else:
                logger.error(f"Failed to set webhook: {result}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error setting webhook: {e}")
            return False
        except Exception as e:
            logger.error(f"Error setting webhook: {e}")
            return False

    def get_bot_info(self) -> Dict[str, Any]:
        """Get bot information"""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=30)
            result = response.json()

            if result.get('ok'):
                return result.get('result', {})
            else:
                logger.error(f"Failed to get bot info: {result}")
                return {}

        except Exception as e:
            logger.error(f"Error getting bot info: {e}")
            return {}

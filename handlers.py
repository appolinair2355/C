import logging
import re
import time
import json
from datetime import datetime
from telegram import Update, Message, Chat, User
from telegram.ext import CallbackContext

from card_predictor import CardPredictor

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class TelegramHandlers:
    """Gestionnaire principal des événements Telegram."""

    def __init__(self, bot):
        self.bot = bot

        # Initialisation du prédicteur
        try:
            self.card_predictor = CardPredictor()
            logger.info("✅ CardPredictor initialisé avec succès")
        except Exception as e:
            logger.error(f"❌ Impossible d’importer ou initialiser CardPredictor: {e}")
            self.card_predictor = None

        # Cooldown et états
        self.last_message_time = {}
        self.COOLDOWN = 10  # secondes

    # -------------------------------------------------
    # Vérification cooldown
    # -------------------------------------------------
    def is_in_cooldown(self, chat_id: int) -> bool:
        now = time.time()
        last = self.last_message_time.get(chat_id, 0)
        if now - last < self.COOLDOWN:
            logger.debug(f"⏳ Cooldown actif pour {chat_id}")
            return True
        self.last_message_time[chat_id] = now
        return False

    # -------------------------------------------------
    # Handlers principaux
    # -------------------------------------------------
    def handle_message(self, update: Update, context: CallbackContext):
        """Handler principal pour chaque message reçu"""
        try:
            message: Message = update.message
            if not message or not message.text:
                return

            chat: Chat = message.chat
            user: User = message.from_user
            text: str = message.text.strip()

            logger.info(f"📩 Message reçu dans {chat.id} par {user.username}: {text}")

            # Cooldown
            if self.is_in_cooldown(chat.id):
                return

            # Gestion prédiction
            if self.card_predictor:
                self._process_prediction_logic(message, text)

            # TODO: ajouter d’autres traitements ici (commandes, etc.)

        except Exception as e:
            logger.exception(f"⚠️ Erreur dans handle_message: {e}")

    # -------------------------------------------------
    # Prédictions
    # -------------------------------------------------
    def _process_prediction_logic(self, message: Message, text: str):
        """Logique complète de traitement prédictions"""
        try:
            should_predict, game_number, mirror_prediction = self.card_predictor.should_predict(text)

            if should_predict and game_number and mirror_prediction:
                logger.info(f"🎯 Nouvelle prédiction détectée (Game {game_number+2} : {mirror_prediction})")

                prediction_text = self.card_predictor.make_prediction(game_number, mirror_prediction)
                chat_id = self.card_predictor.get_redirect_channel(message.chat.id)

                sent_message = self.bot.send_message(chat_id=chat_id, text=prediction_text)
                if sent_message:
                    self.card_predictor.predictions[game_number+2]['message_id'] = sent_message.message_id
                    self.card_predictor.predictions[game_number+2]['chat_id'] = chat_id
                    logger.info(f"📤 Prédiction envoyée dans {chat_id}")

            # Vérification si un message final confirme ou infirme la prédiction
            verification_result = self.card_predictor.verify_prediction(text, bot=self.bot)
            if verification_result:
                logger.info(f"🔍 Prédiction vérifiée: {verification_result}")

        except Exception as e:
            logger.exception(f"⚠️ Erreur dans _process_prediction_logic: {e}")

    # -------------------------------------------------
    # Commandes
    # -------------------------------------------------
    def handle_command(self, update: Update, context: CallbackContext):
        """Gestion des commandes /start, /help, etc."""
        try:
            message: Message = update.message
            if not message or not message.text:
                return

            chat: Chat = message.chat
            user: User = message.from_user
            command = message.text.strip().split()[0].lower()

            logger.info(f"⚡ Commande reçue {command} dans {chat.id} par {user.username}")

            if command == "/start":
                self.bot.send_message(chat.id, "🤖 Bot démarré avec succès !")
            elif command == "/help":
                self.bot.send_message(chat.id, "📖 Commandes disponibles:\n/start - démarrer\n/help - aide")
            elif command == "/reset":
                if self.card_predictor:
                    self.card_predictor.reset_all_predictions()
                    self.bot.send_message(chat.id, "♻️ Prédictions réinitialisées")
            else:
                self.bot.send_message(chat.id, f"❓ Commande inconnue: {command}")

        except Exception as e:
            logger.exception(f"⚠️ Erreur dans handle_command: {e}")

    # -------------------------------------------------
    # Callback Query
    # -------------------------------------------------
    def handle_callback(self, update: Update, context: CallbackContext):
        """Gestion des interactions boutons inline"""
        try:
            query = update.callback_query
            if not query:
                return

            data = query.data
            user = query.from_user
            chat_id = query.message.chat_id

            logger.info(f"🔘 Callback reçu de {user.username} ({chat_id}) : {data}")

            if data == "reset_predictions":
                if self.card_predictor:
                    self.card_predictor.reset_all_predictions()
                    self.bot.send_message(chat_id, "♻️ Prédictions réinitialisées via bouton")

            query.answer()

        except Exception as e:
            logger.exception(f"⚠️ Erreur dans handle_callback: {e}")

    # -------------------------------------------------
    # Messages d’édition
    # -------------------------------------------------
    def handle_edited_message(self, update: Update, context: CallbackContext):
        """Traite l’édition de messages"""
        try:
            message: Message = update.edited_message
            if not message or not message.text:
                return

            text: str = message.text.strip()
            logger.info(f"✏️ Message édité détecté: {text}")

            if self.card_predictor:
                self._process_prediction_logic(message, text)

        except Exception as e:
            logger.exception(f"⚠️ Erreur dans handle_edited_message: {e}")

    # -------------------------------------------------
    # Utils
    # -------------------------------------------------
    def handle_error(self, update: object, context: CallbackContext):
        """Gestion centralisée des erreurs"""
        logger.error(f"⚠️ Update {update} a causé une erreur: {context.error}")

"""
Card prediction logic for Joker's Telegram Bot - webhook deployment
Modifications:
- 🔰 considered as ✅ (final)
- Predictions created for N+2
- Store message_id when sending predictions and edit that message when status changes:
    - Found at N+2 -> ✅0️⃣
    - Not found at N+2 but found at N+3 -> ✅1️⃣
    - Not found at N+2 nor N+3 -> ⭕
- Functions added: get_prediction_text, send_prediction_via_bot, edit_prediction_message, process_incoming_telegram_message
- Keeps cooldown persistence in .last_prediction_time
"""

import re
import logging
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import time
import os
import json
import hashlib

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Configuration constants
VALID_CARD_COMBINATIONS = [
    "♠️♥️♦️", "♠️♥️♣️", "♠️♦️♣️", "♥️♦️♣️"
]

CARD_SYMBOLS = ["♠️", "♥️", "♦️", "♣️"]  # ❤️ est normalisé en ♥️

# Channel IDs (example provided)
TARGET_CHANNEL_ID = -1002682552255
PREDICTION_CHANNEL_ID = -1002646551216

# Persistence filename
LAST_PREDICTION_FILENAME = ".last_prediction_time"


def normalize_emoji(text: str) -> str:
    """Normalize emoji variants (e.g. ❤️ -> ♥️)."""
    return text.replace("❤️", "♥️")


def extract_parentheses_sections(text: str) -> List[str]:
    """Return list of contents inside parentheses, in order."""
    pattern = r'\(([^)]+)\)'
    return re.findall(pattern, text)


class CardPredictor:
    """Handles card prediction logic for webhook deployment"""

    def __init__(self):
        self.predictions: Dict[int, Dict] = {}  # keyed by target_game (int)
        self.processed_messages = set()  # Avoid duplicate processing
        self.sent_predictions = {}
        self.temporary_messages = {}
        self.pending_edits = {}
        self.position_preference = 1
        self.redirect_channels = {}
        self.last_prediction_time = self._load_last_prediction_time()
        self.prediction_cooldown = 30

    # -------------------------
    # Persistence (cooldown)
    # -------------------------
    def _load_last_prediction_time(self) -> float:
        """Load last prediction timestamp from file"""
        try:
            if os.path.exists(LAST_PREDICTION_FILENAME):
                with open(LAST_PREDICTION_FILENAME, 'r') as f:
                    timestamp = float(f.read().strip())
                    logger.info(f"⏰ Dernière prédiction chargée: {time.time() - timestamp:.1f}s écoulées")
                    return timestamp
        except Exception as e:
            logger.warning(f"⚠️ Impossible de charger le timestamp: {e}")
        return 0.0

    def _save_last_prediction_time(self):
        """Save last prediction timestamp to file"""
        try:
            with open(LAST_PREDICTION_FILENAME, 'w') as f:
                f.write(str(self.last_prediction_time))
        except Exception as e:
            logger.warning(f"⚠️ Impossible de sauvegarder le timestamp: {e}")

    # -------------------------
    # Config / utils
    # -------------------------
    def reset_predictions(self):
        self.predictions.clear()
        self.processed_messages.clear()
        self.sent_predictions.clear()
        self.temporary_messages.clear()
        self.pending_edits.clear()
        self.last_prediction_time = 0.0
        self._save_last_prediction_time()
        logger.info("🔄 Prédictions réinitialisées")

    def set_position_preference(self, position: int):
        if position in [1, 2]:
            self.position_preference = position
            logger.info(f"🎯 Position mise à jour : {position}")
        else:
            logger.warning(f"⚠️ Position invalide {position}, utilisation de 1")

    def set_redirect_channel(self, source_chat_id: int, target_chat_id: int):
        self.redirect_channels[source_chat_id] = target_chat_id
        logger.info(f"📤 Redirection configurée : {source_chat_id} → {target_chat_id}")

    def get_redirect_channel(self, source_chat_id: int) -> int:
        return self.redirect_channels.get(source_chat_id, PREDICTION_CHANNEL_ID)

    def reset_all_predictions(self):
        self.predictions.clear()
        self.processed_messages.clear()
        self.sent_predictions.clear()
        self.temporary_messages.clear()
        self.pending_edits.clear()
        self.redirect_channels.clear()
        self.last_prediction_time = 0.0
        self._save_last_prediction_time()
        logger.info("🔄 Toutes les prédictions et redirections supprimées")

    # -------------------------
    # Extraction helpers
    # -------------------------
    def extract_game_number(self, message: str) -> Optional[int]:
        pattern = r'#[nN]?(\d+)'
        match = re.search(pattern, message)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None

    def has_pending_indicators(self, text: str) -> bool:
        indicators = ['⏰', '▶', '🕐', '➡️']
        return any(indicator in text for indicator in indicators)

    def has_completion_indicators(self, text: str) -> bool:
        completion_indicators = ['✅', '🔰']
        return any(indicator in text for indicator in completion_indicators)

    def should_wait_for_edit(self, text: str, message_id: int) -> bool:
        if self.has_pending_indicators(text):
            self.pending_edits[message_id] = {
                'original_text': text,
                'timestamp': datetime.now()
            }
            return True
        return False

    def extract_card_symbols_from_parentheses(self, text: str) -> List[List[str]]:
        matches = re.findall(r'\(([^)]+)\)', text)
        all_sections = []
        for match in matches:
            normalized_content = normalize_emoji(match)
            unique_symbols = [s for s in ["♠️", "♥️", "♦️", "♣️"] if s in normalized_content]
            all_sections.append(unique_symbols)
        return all_sections

    # -------------------------
    # Mirror rule
    # -------------------------
    def check_mirror_rule(self, message: str) -> Optional[str]:
        normalized_message = normalize_emoji(message)
        color_counts = {
            "♥️": normalized_message.count("♥️"),
            "♠️": normalized_message.count("♠️"),
            "♦️": normalized_message.count("♦️"),
            "♣️": normalized_message.count("♣️")
        }
        candidates = [c for c, cnt in color_counts.items() if cnt >= 3]
        if len(candidates) != 1:
            return None
        mirror_map = {"♥️": "♣️", "♠️": "♦️", "♦️": "♠️", "♣️": "♥️"}
        return mirror_map.get(candidates[0])

    # -------------------------
    # Cooldown
    # -------------------------
    def can_make_prediction(self) -> bool:
        current_time = time.time()
        if self.last_prediction_time == 0:
            return True
        return (current_time - self.last_prediction_time) >= self.prediction_cooldown

    # -------------------------
    # Decision to predict
    # -------------------------
    def should_predict(self, message: str) -> Tuple[bool, Optional[int], Optional[str]]:
        game_number = self.extract_game_number(message)
        if not game_number:
            return False, None, None

        if '#R' in message or '#X' in message:
            return False, None, None

        if self.has_pending_indicators(message) and not self.has_completion_indicators(message):
            self.temporary_messages[game_number] = message
            return False, None, None

        target_game = game_number + 2
        if target_game in self.predictions and self.predictions[target_game].get('status') in ('pending', '⏳', 'waiting_next'):
            return False, None, None

        if self.has_completion_indicators(message):
            self.temporary_messages.pop(game_number, None)

        if not self.can_make_prediction():
            return False, None, None

        mirror_prediction = self.check_mirror_rule(message)
        if not mirror_prediction:
            return False, None, None

        message_hash = hashlib.sha1(message.encode()).hexdigest()
        if message_hash in self.processed_messages:
            return False, None, None

        self.processed_messages.add(message_hash)
        return True, game_number, mirror_prediction

    # -------------------------
    # Make & send prediction
    # -------------------------
    def make_prediction(self, game_number: int, predicted_costume: str,
                        sent_message_id: Optional[int] = None, sent_chat_id: Optional[int] = None) -> str:
        target_game = game_number + 2
        prediction_text = f"🔵{target_game}🔵:{predicted_costume} statut :⏳"

        self.predictions[target_game] = {
            'predicted_costume': predicted_costume,
            'status': '⏳',
            'predicted_from': game_number,
            'verification_count': 0,
            'message_text': prediction_text,
            'message_id': sent_message_id,
            'chat_id': sent_chat_id,
            'timestamp': time.time(),
            'verified': False
        }
        self.last_prediction_time = time.time()
        self._save_last_prediction_time()
        return prediction_text

    def get_prediction_text(self, target_game: int) -> str:
        rec = self.predictions.get(target_game)
        if not rec:
            return ""
        return f"🔵{target_game}🔵:{rec['predicted_costume']} statut :{rec.get('status', '⏳')}"

    def send_prediction_via_bot(self, bot, chat_id: int, target_game: int) -> Optional[int]:
        rec = self.predictions.get(target_game)
        if not rec:
            return None
        text = rec.get('message_text') or self.get_prediction_text(target_game)
        try:
            sent = bot.send_message(chat_id=chat_id, text=text)
            message_id = getattr(sent, 'message_id', None)
            rec['message_id'] = message_id
            rec['chat_id'] = chat_id
            rec['message_text'] = text
            return message_id
        except Exception as e:
            logger.exception(f"⚠️ Send failed: {e}")
            return None

    def edit_prediction_message(self, bot, target_game: int) -> bool:
        rec = self.predictions.get(target_game)
        if not rec:
            return False
        message_id = rec.get('message_id')
        chat_id = rec.get('chat_id', PREDICTION_CHANNEL_ID)
        if not message_id:
            return False
        new_text = self.get_prediction_text(target_game)
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=new_text)
            rec['message_text'] = new_text
            return True
        except Exception as e:
            logger.exception(f"⚠️ Edit failed: {e}")
            return False

    # -------------------------
    # Verification logic
    # -------------------------
    def check_costume_in_first_parentheses(self, message: str, predicted_costume: str) -> bool:
        normalized = normalize_emoji(message)
        matches = extract_parentheses_sections(normalized)
        if not matches:
            return False
        first_content = matches[0]
        symbols = re.findall(r'(?:♠️|♥️|♦️|♣️)', first_content)
        return predicted_costume in symbols

    def verify_prediction(self, message: str, bot=None) -> Optional[Dict]:
        if not self.has_completion_indicators(message):
            logger.debug("verify_prediction called on non-final message; skipping.")
            return None

        game_number = self.extract_game_number(message)
        if not game_number:
            return None

        # Recherche de la prédiction associée à N ou N-1
        for offset in [0, -1]:
            target_game = game_number + offset
            rec = self.predictions.get(target_game)
            if not rec:
                continue

            predicted = rec['predicted_costume']
            if self.check_costume_in_first_parentheses(message, predicted):
                rec['status'] = "✅0️⃣" if offset == 0 else "✅1️⃣"
            else:
                if rec['status'] == '⏳' and offset == -1:
                    rec['status'] = "⭕"

            if bot:
                self.edit_prediction_message(bot, target_game)

            rec['verified'] = True
            return rec

        return None

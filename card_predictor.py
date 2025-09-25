"""
Card prediction logic for Joker's Telegram Bot - simplified for webhook deployment
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
import time
import os
import json

logger = logging.getLogger(__name__)

# Configuration constants
VALID_CARD_COMBINATIONS = [
    "♠️♥️♦️", "♠️♥️♣️", "♠️♦️♣️", "♥️♦️♣️"
]

CARD_SYMBOLS = ["♠️", "♥️", "♦️", "♣️", "❤️"]  # Include both ♥️ and ❤️ variants

# Target channel ID for Baccarat Kouamé
TARGET_CHANNEL_ID = -1002682552255

# Target channel ID for predictions and updates
PREDICTION_CHANNEL_ID = -1002646551216

class CardPredictor:
    """Handles card prediction logic for webhook deployment"""

    def __init__(self):
        self.predictions = {}  # Store predictions for verification
        self.processed_messages = set()  # Avoid duplicate processing
        self.sent_predictions = {}  # Store sent prediction messages for editing
        self.temporary_messages = {}  # Store temporary messages waiting for final edit
        self.pending_edits = {}  # Store messages waiting for edit with indicators
        self.position_preference = 1  # Default position preference (1 = first card, 2 = second card)
        self.redirect_channels = {}  # Store redirection channels for different chats
        self.last_prediction_time = self._load_last_prediction_time()  # Load persisted timestamp
        self.prediction_cooldown = 30   # Cooldown period in seconds between predictions

    def _load_last_prediction_time(self) -> float:
        """Load last prediction timestamp from file"""
        try:
            if os.path.exists('.last_prediction_time'):
                with open('.last_prediction_time', 'r') as f:
                    timestamp = float(f.read().strip())
                    logger.info(f"⏰ PERSISTANCE - Dernière prédiction chargée: {time.time() - timestamp:.1f}s écoulées")
                    return timestamp
        except Exception as e:
            logger.warning(f"⚠️ Impossible de charger le timestamp: {e}")
        return 0

    def _save_last_prediction_time(self):
        """Save last prediction timestamp to file"""
        try:
            with open('.last_prediction_time', 'w') as f:
                f.write(str(self.last_prediction_time))
        except Exception as e:
            logger.warning(f"⚠️ Impossible de sauvegarder le timestamp: {e}")

    def reset_predictions(self):
        """Reset all prediction states - useful for recalibration"""
        self.predictions.clear()
        self.processed_messages.clear()
        self.sent_predictions.clear()
        self.temporary_messages.clear()
        self.pending_edits.clear()
        self.last_prediction_time = 0
        self._save_last_prediction_time()
        logger.info("🔄 Système de prédictions réinitialisé")

    def set_position_preference(self, position: int):
        """Set the position preference for card selection (1 or 2)"""
        if position in [1, 2]:
            self.position_preference = position
            logger.info(f"🎯 Position de carte mise à jour : {position}")
        else:
            logger.warning(f"⚠️ Position invalide : {position}. Utilisation de la position par défaut (1).")

    def set_redirect_channel(self, source_chat_id: int, target_chat_id: int):
        """Set redirection channel for predictions from a source chat"""
        self.redirect_channels[source_chat_id] = target_chat_id
        logger.info(f"📤 Redirection configurée : {source_chat_id} → {target_chat_id}")

    def get_redirect_channel(self, source_chat_id: int) -> int:
        """Get redirect channel for a source chat, fallback to PREDICTION_CHANNEL_ID"""
        return self.redirect_channels.get(source_chat_id, PREDICTION_CHANNEL_ID)

    def reset_all_predictions(self):
        """Reset all predictions and redirect channels"""
        self.predictions.clear()
        self.processed_messages.clear()
        self.sent_predictions.clear()
        self.temporary_messages.clear()
        self.pending_edits.clear()
        self.redirect_channels.clear()
        self.last_prediction_time = 0
        self._save_last_prediction_time()
        logger.info("🔄 Toutes les prédictions et redirections ont été supprimées")

    def extract_game_number(self, message: str) -> Optional[int]:
        """Extract game number from message like #n744 or #N744"""
        pattern = r'#[nN](\d+)'
        match = re.search(pattern, message)
        if match:
            return int(match.group(1))
        return None

    def has_pending_indicators(self, text: str) -> bool:
        """Check if message contains indicators suggesting it will be edited"""
        indicators = ['⏰', '▶', '🕐', '➡️']
        return any(indicator in text for indicator in indicators)

    def has_completion_indicators(self, text: str) -> bool:
        """Check if message contains completion indicators after edit"""
        completion_indicators = ['✅', '🔰']
        has_indicator = any(indicator in text for indicator in completion_indicators)
        if has_indicator:
            logger.info(f"🔍 FINALISATION DÉTECTÉE - Indicateurs trouvés dans: {text[:100]}...")
        return has_indicator

    def should_wait_for_edit(self, text: str, message_id: int) -> bool:
        """Determine if we should wait for this message to be edited"""
        if self.has_pending_indicators(text):
            # Store this message as pending edit
            self.pending_edits[message_id] = {
                'original_text': text,
                'timestamp': datetime.now()
            }
            return True
        return False

    def extract_card_symbols_from_parentheses(self, text: str) -> List[List[str]]:
        """Extract unique card symbols from each parentheses section"""
        # Find all parentheses content
        pattern = r'\(([^)]+)\)'
        matches = re.findall(pattern, text)

        all_sections = []
        for match in matches:
            # Normalize ❤️ to ♥️ for consistency
            normalized_content = match.replace("❤️", "♥️")

            # Extract only unique card symbols (costumes) from this section
            unique_symbols = set()
            for symbol in ["♠️", "♥️", "♦️", "♣️"]:
                if symbol in normalized_content:
                    unique_symbols.add(symbol)

            all_sections.append(list(unique_symbols))

        return all_sections

    def check_mirror_rule(self, message: str) -> Optional[str]:
        """
        NOUVELLE RÈGLE DU MIROIR:
        Si on trouve 3 couleurs identiques ou plus dans tout le message (joueur + banquier),
        on donne le miroir de cette couleur:
        - ♥️ (❤️) → ♣️
        - ♠️ → ♦️
        - ♦️ → ♠️
        - ♣️ → ♥️
        """
        normalized_message = message.replace("❤️", "♥️")
        color_counts = {
            "♥️": normalized_message.count("♥️"),
            "♠️": normalized_message.count("♠️"),
            "♦️": normalized_message.count("♦️"),
            "♣️": normalized_message.count("♣️")
        }
        logger.info(f"🔮 MIROIR - Comptage couleurs: {color_counts}")
        for color, count in color_counts.items():
            if count >= 3:
                mirror = {"♥️":"♣️","♠️":"♦️","♦️":"♠️","♣️":"♥️"}[color]
                logger.info(f"🔮 MIROIR DÉTECTÉ - {count}x{color} → Prédire {mirror}")
                return mirror
        return None

    def can_make_prediction(self) -> bool:
        current_time = time.time()
        if self.last_prediction_time == 0:
            return True
        return current_time - self.last_prediction_time >= self.prediction_cooldown

    def should_predict(self, message: str) -> Tuple[bool, Optional[int], Optional[str]]:
        """Analyse le message pour savoir si une prédiction peut être faite"""
        game_number = self.extract_game_number(message)
        if not game_number:
            return False, None, None
        if '🔰' in message or '#R' in message or '#X' in message:
            return False, None, None
        if self.has_pending_indicators(message) and not self.has_completion_indicators(message):
            self.temporary_messages[game_number] = message
            return False, None, None
        target_game = game_number + 1
        if target_game in self.predictions and self.predictions[target_game].get('status') == 'pending':
            return False, None, None
        if not self.can_make_prediction():
            return False, None, None
        mirror_prediction = self.check_mirror_rule(message)
        if not mirror_prediction:
            return False, None, None
        message_hash = hash(message)
        if message_hash in self.processed_messages:
            return False, None, None
        self.processed_messages.add(message_hash)
        self.last_prediction_time = time.time()
        self._save_last_prediction_time()
        return True, game_number, mirror_prediction

    def make_prediction(self, game_number: int, predicted_costume: str) -> str:
        target_game = game_number + 1
        prediction_text = f"🔵{target_game}🔵:{predicted_costume}statut :⏳"
        self.predictions[target_game] = {
            'predicted_costume': predicted_costume,
            'status': 'pending',
            'predicted_from': game_number,
            'verification_count': 0,
            'message_text': prediction_text
        }
        return prediction_text

    def check_costume_in_first_parentheses(self, message: str, predicted_costume: str) -> bool:
        normalized_message = message.replace("❤️", "♥️")
        normalized_costume = predicted_costume.replace("❤️", "♥️")
        matches = re.findall(r'\(([^)]+)\)', normalized_message)
        if not matches:
            return False
        return normalized_costume in matches[0]

    def verify_prediction(self, message: str) -> Optional[Dict]:
        """Système qui met à jour uniquement le message de prédiction existant"""
        has_success_symbol = ('✅' in message) or ('🔰' in message)
        if not has_success_symbol:
            logger.info("🔍 ⏸️ Pas de vérification - Aucun symbole de succès (✅ ou 🔰) trouvé")
            return None
        game_number = self.extract_game_number(message)
        if not game_number:
            return None
        if not self.predictions:
            return None
        for predicted_game in sorted(self.predictions.keys()):
            prediction = self.predictions[predicted_game]
            if prediction.get('status') != 'pending':
                continue
            verification_offset = game_number - predicted_game
            predicted_costume = prediction.get('predicted_costume')
            if verification_offset in [0, 1]:
                if self.check_costume_in_first_parentheses(message, predicted_costume):
                    status_symbol = f"✅{verification_offset}️⃣"
                    original_message = prediction['message_text']
                    updated_message = f"🔵{predicted_game}🔵:{predicted_costume}statut :{status_symbol}"
                    prediction['status'] = 'correct'
                    prediction['verification_count'] = verification_offset
                    prediction['final_message'] = updated_message
                    return {
                        'type': 'edit_message',
                        'predicted_game': predicted_game,
                        'new_message': updated_message,
                        'original_message': original_message
                    }
            elif verification_offset >= 2:
                original_message = prediction['message_text']
                updated_message = f"🔵{predicted_game}🔵:{predicted_costume}statut :⭕"
                prediction['status'] = 'failed'
                prediction['final_message'] = updated_message
                return {
                    'type': 'edit_message',
                    'predicted_game': predicted_game,
                    'new_message': updated_message,
                    'original_message': original_message
                }
        return None

# Global instance
card_predictor = CardPredictor()

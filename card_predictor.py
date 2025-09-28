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

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Configuration constants
VALID_CARD_COMBINATIONS = [
    "♠️♥️♦️", "♠️♥️♣️", "♠️♦️♣️", "♥️♦️♣️"
]

CARD_SYMBOLS = ["♠️", "♥️", "♦️", "♣️", "❤️"]  # Include both ♥️ and ❤️ variants

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
        self.sent_predictions = {}  # store message metadata if needed
        self.temporary_messages = {}  # Store temporary messages waiting for final edit
        self.pending_edits = {}  # Store messages waiting for edit with indicators
        self.position_preference = 1  # Default position preference (1 = first card, 2 = second card)
        self.redirect_channels = {}  # Store redirection channels for different chats
        self.last_prediction_time = self._load_last_prediction_time()  # Load persisted timestamp
        self.prediction_cooldown = 30   # Cooldown period in seconds between predictions

    # -------------------------
    # Persistence (cooldown)
    # -------------------------
    def _load_last_prediction_time(self) -> float:
        """Load last prediction timestamp from file"""
        try:
            if os.path.exists(LAST_PREDICTION_FILENAME):
                with open(LAST_PREDICTION_FILENAME, 'r') as f:
                    timestamp = float(f.read().strip())
                    logger.info(f"⏰ PERSISTANCE - Dernière prédiction chargée: {time.time() - timestamp:.1f}s écoulées")
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
    # Configuration / utility
    # -------------------------
    def reset_predictions(self):
        """Reset all prediction states - useful for recalibration"""
        self.predictions.clear()
        self.processed_messages.clear()
        self.sent_predictions.clear()
        self.temporary_messages.clear()
        self.pending_edits.clear()
        self.last_prediction_time = 0.0
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
        self.last_prediction_time = 0.0
        self._save_last_prediction_time()
        logger.info("🔄 Toutes les prédictions et redirections ont été supprimées")

    # -------------------------
    # Extraction helpers
    # -------------------------
    def extract_game_number(self, message: str) -> Optional[int]:
        """Extract game number from message like #n744 or #N744 or #744"""
        pattern = r'#[nN]?(\d+)'
        match = re.search(pattern, message)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None

    def has_pending_indicators(self, text: str) -> bool:
        """Check if message contains indicators suggesting it will be edited"""
        indicators = ['⏰', '▶', '🕐', '➡️']
        return any(indicator in text for indicator in indicators)

    def has_completion_indicators(self, text: str) -> bool:
        """Check if message contains completion indicators after edit (✅ or 🔰 treated as final)"""
        completion_indicators = ['✅', '🔰']  # 🔰 is treated as final
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
            unique_symbols = []
            for symbol in ["♠️", "♥️", "♦️", "♣️"]:
                if symbol in normalized_content:
                    unique_symbols.append(symbol)

            all_sections.append(unique_symbols)

        return all_sections

    def has_three_different_cards(self, cards: List[str]) -> bool:
        """Check if there are exactly 3 different card symbols"""
        unique_cards = list(set(cards))
        logger.info(f"Checking cards: {cards}, unique: {unique_cards}, count: {len(unique_cards)}")
        return len(unique_cards) == 3

    def is_temporary_message(self, message: str) -> bool:
        """Check if message contains temporary progress emojis"""
        temporary_emojis = ['⏰', '▶', '🕐', '➡️']
        return any(emoji in message for emoji in temporary_emojis)

    def is_final_message(self, message: str) -> bool:
        """Check if message contains final completion emojis (✅ or 🔰)"""
        final_emojis = ['✅', '🔰']
        is_final = any(emoji in message for emoji in final_emojis)
        if is_final:
            logger.info(f"🔍 MESSAGE FINAL DÉTECTÉ - Emoji final trouvé dans: {message[:100]}...")
        return is_final

    # -------------------------
    # Mirror rule
    # -------------------------
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
        normalized_message = normalize_emoji(message)

        # Compter toutes les occurrences de chaque couleur dans le message entier
        color_counts = {
            "♥️": normalized_message.count("♥️"),
            "♠️": normalized_message.count("♠️"),
            "♦️": normalized_message.count("♦️"),
            "♣️": normalized_message.count("♣️")
        }

        logger.info(f"🔮 MIROIR - Comptage couleurs: {color_counts}")

        # Trouver les couleurs qui ont 3 occurrences ou plus
        candidates = [c for c, cnt in color_counts.items() if cnt >= 3]
        if len(candidates) != 1:
            logger.info(f"🔮 MIROIR - Pas de majorité unique (candidates={candidates})")
            return None

        color = candidates[0]
        mirror_map = {
            "♥️": "♣️",
            "♠️": "♦️",
            "♦️": "♠️",
            "♣️": "♥️"
        }
        mirror = mirror_map.get(color)
        logger.info(f"🔮 MIROIR DÉTECTÉ - {color} ({color_counts[color]}x) → Prédire {mirror}")
        return mirror

    # -------------------------
    # Cooldown
    # -------------------------
    def can_make_prediction(self) -> bool:
        """Check if enough time has passed since last prediction"""
        current_time = time.time()

        if self.last_prediction_time == 0:
            logger.info(f"⏰ PREMIÈRE PRÉDICTION: Aucune prédiction précédente, autorisation accordée")
            return True

        time_since_last = current_time - self.last_prediction_time

        if time_since_last >= self.prediction_cooldown:
            logger.info(f"⏰ COOLDOWN OK: {time_since_last:.1f}s écoulées depuis dernière prédiction (≥{self.prediction_cooldown}s)")
            return True
        else:
            remaining = self.prediction_cooldown - time_since_last
            logger.info(f"⏰ COOLDOWN ACTIF: Encore {remaining:.1f}s à attendre avant prochaine prédiction")
            return False

    # -------------------------
    # Decision to predict
    # -------------------------
    def should_predict(self, message: str) -> Tuple[bool, Optional[int], Optional[str]]:
        """
        Determine whether to create a prediction.
        - Only finalized messages (✅ or 🔰) are considered here.
        - #R and #X remain exclusions (you can remove them if you want).
        Returns: (should_predict, game_number, predicted_costume)
        """
        game_number = self.extract_game_number(message)
        if not game_number:
            return False, None, None

        logger.debug(f"🔮 PRÉDICTION - Analyse du jeu {game_number}")

        # Remove '🔰' exclusion: treat it as final (handled by has_completion_indicators)
        # EXCLUSIONS: keep #R and #X if present (they block predictions)
        if '#R' in message:
            logger.info(f"🔮 EXCLUSION - Jeu {game_number}: Contient #R, pas de prédiction")
            return False, None, None

        if '#X' in message:
            logger.info(f"🔮 EXCLUSION - Jeu {game_number}: Contient #X (match nul), pas de prédiction")
            return False, None, None

        # If message is temporary and not yet final, wait
        if self.has_pending_indicators(message) and not self.has_completion_indicators(message):
            logger.info(f"🔮 Jeu {game_number}: Message temporaire (⏰▶🕐➡️), attente finalisation")
            self.temporary_messages[game_number] = message
            return False, None, None

        # Target game (prediction is stored and sent for base_game + 2)
        target_game = game_number + 2
        if target_game in self.predictions and self.predictions[target_game].get('status') in ('pending', '⏳', 'waiting_next'):
            logger.info(f"🔮 Jeu {game_number}: Prédiction N{target_game} déjà existante, éviter doublon")
            return False, None, None

        # If message is final, remove from temporary messages (if was stored)
        if self.has_completion_indicators(message):
            if game_number in self.temporary_messages:
                del self.temporary_messages[game_number]
                logger.info(f"🔮 Jeu {game_number}: Retiré des messages temporaires")

        # Check cooldown
        if not self.can_make_prediction():
            logger.info(f"🔮 COOLDOWN - Jeu {game_number}: Attente cooldown, prédiction différée")
            return False, None, None

        # Apply mirror rule
        mirror_prediction = self.check_mirror_rule(message)
        if not mirror_prediction:
            logger.info(f"🔮 RÈGLE MIROIR - Jeu {game_number}: Pas assez de couleurs identiques (besoin de 3+ ou majorité unique)")
            return False, None, None

        # Check duplicates by message hash
        message_hash = hash(message)
        if message_hash in self.processed_messages:
            logger.info(f"🔮 PRÉDICTION - Jeu {game_number}: Message déjà traité (hash)")
            return False, None, None

        # Mark processed and prepare prediction
        self.processed_messages.add(message_hash)
        # update last prediction time (will be saved on actual make_prediction)
        logger.info(f"🔮 PRÉDICTION - Jeu {game_number}: Préparée pour prédiction N{target_game} avec {mirror_prediction}")
        return True, game_number, mirror_prediction

    # -------------------------
    # Make & send prediction (store message_id)
    # -------------------------
    def make_prediction(self, game_number: int, predicted_costume: str, sent_message_id: Optional[int] = None, sent_chat_id: Optional[int] = None) -> str:
        """
        Create a prediction record for target_game = game_number + 2.
        If you already sent the message to Telegram, pass sent_message_id so we can edit later.
        """
        target_game = game_number + 2  # IMPORTANT: +2 per your requirement

        prediction_text = f"🔵{target_game}🔵:{predicted_costume} statut :⏳"

        self.predictions[target_game] = {
            'predicted_costume': predicted_costume,
            'status': '⏳',  # initial pending status
            'predicted_from': game_number,
            'verification_count': 0,
            'message_text': prediction_text,
            'message_id': sent_message_id,
            'chat_id': sent_chat_id,
            'timestamp': time.time(),
            'verified': False
        }

        # Update cooldown timestamp and persist
        self.last_prediction_time = time.time()
        self._save_last_prediction_time()

        logger.info(f"Made prediction for game {target_game} based on costume {predicted_costume} (from {game_number})")
        return prediction_text

    def get_prediction_text(self, target_game: int) -> str:
        """Rebuild prediction text according to current status."""
        rec = self.predictions.get(target_game)
        if not rec:
            return ""
        costume = rec['predicted_costume']
        status = rec.get('status', '⏳')
        # map to visible representation
        visible = status
        # ensure formatting is consistent (status already in desired emoji form)
        return f"🔵{target_game}🔵:{costume} statut :{visible}"

    # -------------------------
    # Telegram integration helpers (python-telegram-bot)
    # -------------------------
    def send_prediction_via_bot(self, bot, chat_id: int, target_game: int) -> Optional[int]:
        """
        Send prediction text to channel and store message_id for later edits.
        bot: instance of telegram.Bot (python-telegram-bot v20.x)
        chat_id: ID of chat/channel to send to
        target_game: integer key of self.predictions
        Returns message_id if sent, else None
        """
        rec = self.predictions.get(target_game)
        if not rec:
            logger.error(f"send_prediction_via_bot: no prediction record for {target_game}")
            return None
        text = rec.get('message_text') or self.get_prediction_text(target_game)
        try:
            sent = bot.send_message(chat_id=chat_id, text=text)
            message_id = getattr(sent, 'message_id', None)
            rec['message_id'] = message_id
            rec['chat_id'] = chat_id
            # save potentially updated message_text (in case of formatting)
            rec['message_text'] = text
            logger.info(f"✉️ Prediction sent to chat {chat_id} as message_id={message_id}")
            return message_id
        except Exception as e:
            logger.exception(f"⚠️ Failed to send prediction to chat {chat_id}: {e}")
            return None

    def edit_prediction_message(self, bot, target_game: int) -> bool:
        """
        Edit the previously sent prediction message (replace status).
        Returns True on success.
        """
        rec = self.predictions.get(target_game)
        if not rec:
            logger.error(f"edit_prediction_message: no prediction record for {target_game}")
            return False
        message_id = rec.get('message_id')
        chat_id = rec.get('chat_id', PREDICTION_CHANNEL_ID)
        new_text = self.get_prediction_text(target_game)
        if not message_id:
            logger.warning(f"No message_id stored for prediction {target_game}; cannot edit")
            return False
        try:
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=new_text)
            # update stored message_text
            rec['message_text'] = new_text
            logger.info(f"✏️ Edited prediction message {message_id} in chat {chat_id} for target {target_game}")
            return True
        except Exception as e:
            logger.exception(f"⚠️ Failed to edit prediction message {message_id} for target {target_game}: {e}")
            return False

    # -------------------------
    # Verification logic & status updates
    # -------------------------
    def check_costume_in_first_parentheses(self, message: str, predicted_costume: str) -> bool:
        """Return True if the predicted costume exists in the FIRST parentheses group of the message."""
        normalized = normalize_emoji(message)
        matches = extract_parentheses_sections(normalized)
        if not matches:
            return False
        first_content = matches[0]
        # find suits in first_content
        found = predicted_costume in re.findall(r'(?:♠️|♥️|♦️|♣️)', first_content)
        logger.debug(f"Checking predicted '{predicted_costume}' in first parentheses '{first_content}' -> {found}")
        return found

    def verify_prediction(self, message: str, bot=None) -> Optional[Dict]:
        """
        Verify incoming finalized message and update prediction statuses.
        - message: full text of the incoming (finalized) Telegram message
        - bot: optional telegram.Bot instance to perform edit_message_text calls
        Returns the updated prediction record or None.
        """
        if not self.has_completion_indicators(message):
            # We only verify on finalized messages (✅ or 🔰)
        logger.debug("verify_prediction called on non-final message; skipping.")
            return None

        game_number = self.extract_game_number(message)
        if game_number is None:
            logger.debug("verify_prediction: no game number found")
            return None

        # 1) If this game_number matches a stored prediction target (N+2)
        if game_number in self.predictions:
            rec = self.predictions[game_number]
            predicted = rec['predicted_costume']
            if self.check_costume_in_first_parentheses(message, predicted):
                rec['status'] = "✅0️⃣"
                rec['verified'] = True
                rec['verification_game'] = game_number
                rec['verified_at'] = time.time()
                logger.info(f"Prediction target {game_number} -> ✅0️⃣")
                # edit message in channel if we have bot & message_id
                if bot:
                    try:
                        self.edit_prediction_message(bot, game_number)
                    except Exception:
                        pass
            else:
                # mark waiting for N+3
                rec['status'] = "waiting_next"
                logger.info(f"Prediction target {game_number} -> not found in N+2, status=waiting_next")
            return rec

        # 2) Otherwise, check if this message is N+3 for any prediction that was waiting
        for target_game, rec in list(self.predictions.items()):
            if rec.get('status') == "waiting_next" and (target_game + 1) == game_number:
                predicted = rec['predicted_costume']
                if self.check_costume_in_first_parentheses(message, predicted):
                    rec['status'] = "✅1️⃣"
                    rec['verified'] = True
                    rec['verification_game'] = game_number
                    rec['verified_at'] = time.time()
                    logger.info(f"Prediction target {target_game} -> ✅1️⃣ (found in N+3={game_number})")
                else:
                    rec['status'] = "⭕"
                    rec['verified'] = True
                    rec['verification_game'] = game_number
                    rec['verified_at'] = time.time()
                    logger.info(f"Prediction target {target_game} -> ⭕ (not found in N+3={game_number})")
                # edit message if possible
                if bot:
                    try:
                        self.edit_prediction_message(bot, target_game)
                    except Exception:
                        pass
                return rec

        # No prediction updated
        logger.debug("verify_prediction: no prediction matched/updated for incoming final message.")
        return None

    # -------------------------
    # Convenience: process incoming telegram message (combined)
    # -------------------------
    def process_incoming_telegram_message(self, bot, chat_id: int, message_text: str) -> Dict:
        """
        Called by your webhook handler when a message arrives.
        - bot: telegram.Bot instance (python-telegram-bot v20.x)
        - chat_id: id of the chat where message arrived
        - message_text: content of the message

        Flow:
        1) Attempt to create a prediction if message is final and mirror rule matches.
           If a prediction is created, we call send_prediction_via_bot(...) to send to channel and
           store message_id for later edits.
        2) Attempt to verify/update any existing predictions using this finalized message.
        Returns: dict { 'made_prediction': info or None, 'verified': record or None }
        """
        result = {'made_prediction': None, 'verified': None}

        try:
            # 1) Should we prepare a prediction?
            should, base_game, predicted_costume = self.should_predict(message_text)
            if should and base_game and predicted_costume:
                # create record (without message_id yet)
                text = self.make_prediction(base_game, predicted_costume, sent_message_id=None, sent_chat_id=PREDICTION_CHANNEL_ID)
                # send to channel and store message_id
                # note: make_prediction returns the textual message; the stored record has target_game key
                target_game = base_game + 2
                try:
                    sent_message = bot.send_message(chat_id=PREDICTION_CHANNEL_ID, text=self.get_prediction_text(target_game))
                    message_id = getattr(sent_message, 'message_id', None)
                    # save message_id and chat_id
                    if target_game in self.predictions:
                        self.predictions[target_game]['message_id'] = message_id
                        self.predictions[target_game]['chat_id'] = PREDICTION_CHANNEL_ID
                    logger.info(f"Sent prediction message for target {target_game} message_id={message_id}")
                    result['made_prediction'] = {'target_game': target_game, 'message_id': message_id, 'text': self.get_prediction_text(target_game)}
                except Exception as e:
                    logger.exception(f"Failed to send prediction message to channel {PREDICTION_CHANNEL_ID}: {e}")
                    # leave record without message_id; still stored

            # 2) Verification step (only finalized messages are considered inside verify_prediction)
            verified_rec = self.verify_prediction(message_text, bot=bot)
            if verified_rec:
                result['verified'] = verified_rec

        except Exception as e:
            logger.exception(f"Error processing incoming message: {e}")

        return result

    # -------------------------
    # Debug / show
    # -------------------------
    def show_predictions(self) -> str:
        if not self.predictions:
            return "No predictions."
        lines = []
        for tg in sorted(self.predictions.keys()):
            rec = self.predictions[tg]
            lines.append(f"Game {tg}: costume={rec.get('predicted_costume')} status={rec.get('status')} message_id={rec.get('message_id')} from={rec.get('predicted_from')}")
        return "\n".join(lines)


# -------------------------
# Example usage (for local testing only)
# -------------------------
if __name__ == "__main__":
    # This block is only for local/manual testing and should be removed or guarded in actual webhook use.
    from telegram import Bot
    # set token from env for local test (not required for deployment)
    TOKEN = os.environ.get("TG_TOKEN", "")
    if not TOKEN:
        print("Set TG_TOKEN env var to run local test.")
    else:
        bot = Bot(TOKEN)
        cp = CardPredictor()
        # Example final message to create prediction:
        m1 = "#N861. 0(4♥️Q♥️6♠️) - ✅3(2♣️A♣️Q♣️) #T3"
        print("Processing incoming:", m1)
        out = cp.process_incoming_telegram_message(bot, TARGET_CHANNEL_ID, m1)
        print("Result:", out)
        print("Current predictions:\n", cp.show_predictions())

        # Example of N+2 arriving
        m2 = "#N863 (7♥️5♣️3♠️) - ✅"
        print("Processing incoming:", m2)
        out2 = cp.process_incoming_telegram_message(bot, TARGET_CHANNEL_ID, m2)
        print("Result:", out2)
        print("Current predictions:\n", cp.show_predictions())
  

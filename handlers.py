"""
Event handlers for Telegram bot - optimized for render.com webhook deployment
Enhanced with message verification and status update system
"""

import logging
import os
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Rate limiting storage
user_message_counts = defaultdict(list)

# ID de l'utilisateur autorisé (Sossou Kouamé)
AUTHORIZED_USER_ID = 1190237801

# Target channel ID for Baccarat Kouamé
TARGET_CHANNEL_ID = -1002682552255

# Target channel ID for predictions and updates
PREDICTION_CHANNEL_ID = -1002887687164

# Configuration constants
GREETING_MESSAGE = """
🎭 Salut ! Je suis le bot DEPLOY299999 optimisé pour render.com !
Ajoutez-moi à votre canal pour des prédictions automatiques ! 🎯

🔮 Fonctionnalités avancées :
• Prédictions automatiques avec cooldown
• Vérification et mise à jour des statuts
• Édition des messages de prédiction
• Système de redirection multi-canaux

Utilisez /help pour voir toutes mes commandes.
"""

WELCOME_MESSAGE = """
🎭 **BIENVENUE DANS DEPLOY299999 - RENDER.COM !** 🔮

🎯 **COMMANDES DISPONIBLES:**
• `/start` - Accueil
• `/help` - Aide détaillée complète
• `/about` - À propos du bot DEPLOY299999
• `/dev` - Informations développeur
• `/deploy` - Package de déploiement render.com

🔧 **CONFIGURATION AVANCÉE:**
• `/cos [1|2]` - Position de carte
• `/cooldown [secondes]` - Délai entre prédictions  
• `/redirect` - Redirection des prédictions
• `/announce [message]` - Annonce officielle
• `/reset` - Réinitialiser le système

🔮 **FONCTIONNALITÉS DEPLOY299999:**
✓ Prédictions automatiques avec règle du miroir
✓ Vérification sur messages édités ET normaux
✓ Édition automatique des statuts de prédiction
✓ Système de cooldown configurable (30s par défaut)
✓ Support render.com avec port 10000
✓ Redirection multi-canaux flexible

🎯 **Version DEPLOY299999 - Port 10000 - render.com**
"""

HELP_MESSAGE = """
🎯 **GUIDE D'UTILISATION BOT DEPLOY299999** 🔮

📝 **COMMANDES DE BASE:**
• `/start` - Message d'accueil
• `/help` - Afficher cette aide
• `/about` - Informations sur DEPLOY299999
• `/dev` - Contact développeur
• `/deploy` - Package render.com complet

🔧 **COMMANDES DE CONFIGURATION:**
• `/cos [1|2]` - Position de carte pour prédictions
• `/cooldown [secondes]` - Modifier le délai entre prédictions
• `/redirect [source] [target]` - Redirection avancée
• `/redi` - Redirection rapide vers le chat actuel
• `/announce [message]` - Envoyer une annonce officielle
• `/reset` - Réinitialiser toutes les prédictions

🔮 **SYSTÈME DE PRÉDICTION DEPLOY299999:**
- Analyse automatique des messages avec finalisation ✅ 🔰
- Règle du miroir pour couleurs identiques (3+ occurrences)
- Vérification sur messages édités ET normaux
- Édition automatique des statuts :
  ⏳ → ✅0️⃣ (succès immédiat)
  ⏳ → ✅1️⃣ (succès +1 jeu)
  ⏳ → ⭕ (échec après +2)

🎴 **Format des cartes :** ♠️ ♥️ ♦️ ♣️

🌐 **Optimisé pour render.com - Port 10000**
"""

ABOUT_MESSAGE = """
🎭 Bot DEPLOY299999 - Prédicteur de Cartes Avancé

🤖 Version : 2.0 DEPLOY299999
🛠️ Développé pour render.com avec Flask + Webhook
🔮 Spécialisé dans l'analyse de combinaisons avec vérification

✨ Fonctionnalités DEPLOY299999 :
- Prédictions automatiques avec règle du miroir
- Vérification et édition de messages en temps réel
- Support messages édités ET normaux avec ✅ 🔰
- Système de cooldown configurable
- Redirection multi-canaux
- Interface intuitive

🌐 Optimisé pour déploiement render.com
🚀 Port 10000 - Production ready

🌟 Créé pour améliorer votre expérience de prédiction !
"""

DEV_MESSAGE = """
👨‍💻 Informations Développeur DEPLOY299999 :

🔧 Technologies utilisées :
- Python 3.11+ avec Flask
- API Telegram Bot avec webhooks
- Système de vérification et édition avancé
- Déployé sur render.com avec port 10000

📊 Fonctionnalités techniques :
- Webhook en temps réel pour réactivité maximale
- Édition automatique des messages de prédiction
- Vérification sur messages édités ET normaux
- Système de cooldown persistent avec fichier
- Redirection multi-canaux configurables

📧 Contact : 
Pour le support technique ou les suggestions d'amélioration, 
contactez l'administrateur du bot DEPLOY299999.

🚀 Le bot est optimisé pour render.com et 100% opérationnel !
"""

MAX_MESSAGES_PER_MINUTE = 30
RATE_LIMIT_WINDOW = 60

def is_rate_limited(user_id: int) -> bool:
    """Check if user is rate limited"""
    now = datetime.now()
    user_messages = user_message_counts[user_id]

    # Remove old messages outside the window
    user_messages[:] = [msg_time for msg_time in user_messages 
                       if now - msg_time < timedelta(seconds=RATE_LIMIT_WINDOW)]

    # Check if user exceeded limit
    if len(user_messages) >= MAX_MESSAGES_PER_MINUTE:
        return True

    # Add current message time
    user_messages.append(now)
    return False

class TelegramHandlers:
    """Handlers for Telegram bot using render.com webhook approach"""

    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.deployment_file_path = "deployment_render_complete_deploy299999.zip"

        # Import card_predictor locally to avoid circular imports
        try:
            from card_predictor import card_predictor
            self.card_predictor = card_predictor
            logger.info("✅ Card predictor initialisé pour DEPLOY299999")
        except ImportError:
            logger.error("❌ Failed to import card_predictor")
            self.card_predictor = None

        # Store redirected channels for each source chat
        self.redirected_channels = {} # {source_chat_id: target_chat_id}

    def handle_update(self, update: Dict[str, Any]) -> None:
        """Handle incoming Telegram update with enhanced webhook support"""
        try:
            if 'message' in update:
                message = update['message']
                logger.info(f"🔄 DEPLOY299999 - Traitement message normal")
                self._handle_message(message)
            elif 'edited_message' in update:
                message = update['edited_message']
                logger.info(f"🔄 DEPLOY299999 - Traitement message édité pour prédictions/vérifications")
                self._handle_edited_message(message)
            else:
                logger.info(f"⚠️ Type d'update non géré: {list(update.keys())}")

        except Exception as e:
            logger.error(f"❌ Error handling update: {e}")

    def _handle_message(self, message: Dict[str, Any]) -> None:
        """Handle regular messages with verification support"""
        try:
            chat_id = message['chat']['id']
            user_id = message.get('from', {}).get('id')
            sender_chat = message.get('sender_chat', {})
            sender_chat_id = sender_chat.get('id', chat_id)

            # Rate limiting check (skip for channels/groups)
            chat_type = message['chat'].get('type', 'private')
            if user_id and chat_type == 'private' and is_rate_limited(user_id):
                self.send_message(chat_id, "⏰ Veuillez patienter avant d'envoyer une autre commande.")
                return

            # Handle commands
            if 'text' in message:
                text = message['text'].strip()

                if text == '/start':
                    self._handle_start_command(chat_id, user_id)
                elif text == '/help':
                    self._handle_help_command(chat_id, user_id)
                elif text == '/about':
                    self._handle_about_command(chat_id, user_id)
                elif text == '/dev':
                    self._handle_dev_command(chat_id, user_id)
                elif text == '/deploy':
                    self._handle_deploy_command(chat_id, user_id)
                elif text.startswith('/cos'):
                    self._handle_cos_command(chat_id, text, user_id)
                elif text == '/redi':
                    self._handle_redi_command(chat_id, sender_chat_id, user_id)
                elif text == '/reset':
                    self._handle_reset_command(sender_chat_id, user_id)
                elif text.startswith('/cooldown'):
                    self._handle_cooldown_command(chat_id, text, user_id)
                elif text.startswith('/redirect'):
                    self._handle_redirect_command(chat_id, text, user_id)
                elif text.startswith('/announce'):
                    self._handle_announce_command(chat_id, text, user_id)
                else:
                    # Handle regular messages
                    self._handle_regular_message(message)

                    # Process for card prediction in channels/groups
                    if chat_type in ['group', 'supergroup', 'channel'] and self.card_predictor:
                        self._process_card_message(message)
                        # VÉRIFICATION sur messages normaux avec ✅ ou 🔰
                        self._process_verification_on_normal_message(message)

            # Handle new chat members
            if 'new_chat_members' in message:
                self._handle_new_chat_members(message)

        except Exception as e:
            logger.error(f"❌ Error handling message: {e}")

    def _handle_edited_message(self, message: Dict[str, Any]) -> None:
        """Handle edited messages with enhanced prediction and verification"""
        try:
            chat_id = message['chat']['id']
            chat_type = message['chat'].get('type', 'private')
            user_id = message.get('from', {}).get('id')
            message_id = message.get('message_id')
            sender_chat = message.get('sender_chat', {})
            sender_chat_id = sender_chat.get('id', chat_id)

            logger.info(f"✏️ DEPLOY299999 - Message édité ID:{message_id} | Chat:{chat_id} | Sender:{sender_chat_id}")

            # Rate limiting check (skip for channels/groups)
            if user_id and chat_type == 'private' and is_rate_limited(user_id):
                return

            if 'text' in message:
                text = message['text']
                logger.info(f"✏️ DEPLOY299999 - Contenu édité analysé")

                # Skip if card_predictor not available
                if not self.card_predictor:
                    logger.warning("❌ Card predictor not available")
                    return

                # Vérifier canal autorisé
                if sender_chat_id != TARGET_CHANNEL_ID:
                    logger.info(f"🚫 Message édité ignoré - Canal non autorisé: {sender_chat_id}")
                    return

                logger.info(f"✅ DEPLOY299999 - Message édité du canal autorisé")

                # Vérifier finalisation
                has_completion = self.card_predictor.has_completion_indicators(text)

                if has_completion:
                    logger.info(f"🎯 DEPLOY299999 - ÉDITION FINALISÉE - Traitement complet")

                    # SYSTÈME 1: PRÉDICTION AUTOMATIQUE (messages édités avec finalisation)
                    should_predict, game_number, combination = self.card_predictor.should_predict(text)

                    if should_predict and game_number is not None and combination is not None:
                        prediction = self.card_predictor.make_prediction(game_number, combination)
                        logger.info(f"🔮 PRÉDICTION DEPLOY299999: {prediction}")

                        # Envoyer et stocker la prédiction
                        target_channel = self.get_redirect_channel(sender_chat_id)
                        sent_message_info = self.send_message(target_channel, prediction)
                        if sent_message_info and isinstance(sent_message_info, dict) and 'message_id' in sent_message_info:
                            target_game = game_number + 1
                            self.card_predictor.sent_predictions[target_game] = {
                                'chat_id': target_channel,
                                'message_id': sent_message_info['message_id']
                            }
                            logger.info(f"📝 PRÉDICTION STOCKÉE pour jeu {target_game}")

                    # SYSTÈME 2: VÉRIFICATION ET ÉDITION DE MESSAGES
                    verification_result = self.card_predictor._verify_prediction_common(text, is_edited=True)
                    if verification_result:
                        logger.info(f"🔍 ✅ VÉRIFICATION DEPLOY299999: {verification_result}")

                        if verification_result.get('type') == 'edit_message':
                            predicted_game = verification_result.get('predicted_game')
                            new_message = verification_result.get('new_message')

                            # Éditer le message de prédiction existant
                            if predicted_game in self.card_predictor.sent_predictions:
                                message_info = self.card_predictor.sent_predictions[predicted_game]
                                edit_success = self.edit_message(
                                    message_info['chat_id'],
                                    message_info['message_id'],
                                    new_message
                                )

                                if edit_success:
                                    logger.info(f"🔍 ✅ MESSAGE ÉDITÉ avec succès - Prédiction {predicted_game}")
                                else:
                                    logger.error(f"🔍 ❌ ÉCHEC ÉDITION - Prédiction {predicted_game}")
                            else:
                                logger.warning(f"🔍 ⚠️ AUCUN MESSAGE STOCKÉ pour {predicted_game}")
                    else:
                        logger.info(f"🔍 ⭕ AUCUNE VÉRIFICATION trouvée")

        except Exception as e:
            logger.error(f"❌ Error handling edited message: {e}")

    def _process_card_message(self, message: Dict[str, Any]) -> None:
        """Process message for card prediction"""
        try:
            chat_id = message['chat']['id']
            text = message.get('text', '')
            sender_chat = message.get('sender_chat', {})
            sender_chat_id = sender_chat.get('id', chat_id)

            # Only process from authorized channel
            if sender_chat_id != TARGET_CHANNEL_ID:
                return

            if not text or not self.card_predictor:
                return

            logger.info(f"🎯 DEPLOY299999 - Traitement message canal autorisé")

            # Store temporary messages with pending indicators
            if self.card_predictor.has_pending_indicators(text):
                message_id = message.get('message_id')
                if message_id:
                    self.card_predictor.temporary_messages[message_id] = text
                    logger.info(f"⏰ Message temporaire stocké: {message_id}")

        except Exception as e:
            logger.error(f"❌ Error processing card message: {e}")

    def _process_verification_on_normal_message(self, message: Dict[str, Any]) -> None:
        """Process verification on normal messages with completion indicators"""
        try:
            text = message.get('text', '')
            sender_chat = message.get('sender_chat', {})
            sender_chat_id = sender_chat.get('id', message['chat']['id'])

            # Only process from authorized channel
            if sender_chat_id != TARGET_CHANNEL_ID:
                return

            if not text or not self.card_predictor:
                return

            # Vérifier finalisation
            has_completion = self.card_predictor.has_completion_indicators(text)

            if has_completion:
                logger.info(f"🎯 DEPLOY299999 - MESSAGE NORMAL finalisé - Vérification")

                # Vérification unifiée
                verification_result = self.card_predictor._verify_prediction_common(text, is_edited=False)
                if verification_result:
                    logger.info(f"🔍 ✅ VÉRIFICATION depuis MESSAGE NORMAL")

                    if verification_result['type'] == 'edit_message':
                        predicted_game = verification_result['predicted_game']

                        # Éditer le message de prédiction
                        if predicted_game in self.card_predictor.sent_predictions:
                            message_info = self.card_predictor.sent_predictions[predicted_game]
                            edit_success = self.edit_message(
                                message_info['chat_id'],
                                message_info['message_id'],
                                verification_result['new_message']
                            )

                            if edit_success:
                                logger.info(f"✅ MESSAGE ÉDITÉ depuis message normal - Prédiction {predicted_game}")
                            else:
                                logger.error(f"❌ ÉCHEC ÉDITION depuis message normal")
                        else:
                            logger.warning(f"⚠️ AUCUN MESSAGE STOCKÉ pour {predicted_game}")

        except Exception as e:
            logger.error(f"❌ Error processing verification on normal message: {e}")

    def _is_authorized_user(self, user_id: int) -> bool:
        """Check if user is authorized"""
        return user_id == AUTHORIZED_USER_ID

    def _handle_start_command(self, chat_id: int, user_id: int = None) -> None:
        """Handle /start command"""
        try:
            if user_id and not self._is_authorized_user(user_id):
                self.send_message(chat_id, "🚫 Vous n'êtes pas autorisé à utiliser ce bot.")
                return
            self.send_message(chat_id, WELCOME_MESSAGE)
        except Exception as e:
            logger.error(f"Error in start command: {e}")

    def _handle_help_command(self, chat_id: int, user_id: int = None) -> None:
        """Handle /help command"""
        try:
            if user_id and not self._is_authorized_user(user_id):
                self.send_message(chat_id, "🚫 Vous n'êtes pas autorisé à utiliser ce bot.")
                return
            self.send_message(chat_id, HELP_MESSAGE)
        except Exception as e:
            logger.error(f"Error in help command: {e}")

    def _handle_about_command(self, chat_id: int, user_id: int = None) -> None:
        """Handle /about command"""
        try:
            if user_id and not self._is_authorized_user(user_id):
                self.send_message(chat_id, "🚫 Vous n'êtes pas autorisé à utiliser ce bot.")
                return
            self.send_message(chat_id, ABOUT_MESSAGE)
        except Exception as e:
            logger.error(f"Error in about command: {e}")

    def _handle_dev_command(self, chat_id: int, user_id: int = None) -> None:
        """Handle /dev command"""
        try:
            if user_id and not self._is_authorized_user(user_id):
                self.send_message(chat_id, "🚫 Vous n'êtes pas autorisé à utiliser ce bot.")
                return
            self.send_message(chat_id, DEV_MESSAGE)
        except Exception as e:
            logger.error(f"Error in dev command: {e}")

    def _handle_deploy_command(self, chat_id: int, user_id: int = None) -> None:
        """Handle /deploy command - send DEPLOY299999 render.com package"""
        try:
            if user_id and not self._is_authorized_user(user_id):
                self.send_message(chat_id, "🚫 Vous n'êtes pas autorisé à utiliser ce bot.")
                return

            # Send initial message
            self.send_message(
                chat_id, 
                "🚀 Préparation du package DEPLOY299999 pour render.com... Veuillez patienter."
            )

            # Check if deployment file exists
            if not os.path.exists(self.deployment_file_path):
                self.send_message(
                    chat_id,
                    "❌ Package DEPLOY299999 non trouvé. Contactez l'administrateur."
                )
                logger.error(f"Deployment file {self.deployment_file_path} not found")
                return

            # Send the file
            success = self.send_document(chat_id, self.deployment_file_path)

            if success:
                self.send_message(
                    chat_id,
                    f"✅ **PACKAGE DEPLOY299999 RENDER.COM ENVOYÉ !**\n\n"
                    f"📦 **Fichier :** {self.deployment_file_path}\n\n"
                    "📋 **Contenu du package DEPLOY299999 :**\n"
                    "• main.py - Serveur webhook optimisé port 10000\n"
                    "• bot.py - Gestionnaire principal avec vérification\n"
                    "• handlers.py - Commandes et édition de messages\n"
                    "• card_predictor.py - Système complet avec règle miroir\n"
                    "• config.py - Configuration render.com\n"
                    "• render.yaml - Configuration déploiement\n"
                    "• requirements.txt - Dépendances Python\n"
                    "• Procfile - Script de démarrage\n\n"
                    "🎯 **DEPLOY299999 - FONCTIONNALITÉS :**\n"
                    "• 🔮 Prédictions automatiques avec cooldown\n"
                    "• ✅ Vérifications sur messages édités ET normaux\n"
                    "• 📝 Édition automatique des statuts de prédiction\n"
                    "• 🌐 Optimisé render.com port 10000\n"
                    "• 🚀 Production ready avec webhook\n\n"
                    "🌐 **Instructions déploiement render.com :**\n"
                    "1. Créez un service Web sur render.com\n"
                    "2. Uploadez le package DEPLOY299999\n"
                    "3. Variables d'environnement :\n"
                    "   - BOT_TOKEN : 7644537698:AAFjBt4dBfCB5YH4hxaPXV1bIXlNyIAQwjc\n"
                    "   - WEBHOOK_URL : https://votre-app.onrender.com\n"
                    "   - PORT : 10000\n\n"
                    "🚀 **DEPLOY299999 sera 100% opérationnel sur render.com !**"
                )
            else:
                self.send_message(
                    chat_id,
                    "❌ Échec de l'envoi du package. Réessayez plus tard."
                )

        except Exception as e:
            logger.error(f"Error handling deploy command: {e}")

    def _handle_cos_command(self, chat_id: int, text: str, user_id: int = None) -> None:
        """Handle /cos command"""
        try:
            if user_id and not self._is_authorized_user(user_id):
                self.send_message(chat_id, "🚫 Vous n'êtes pas autorisé à utiliser ce bot.")
                return

            parts = text.strip().split()
            if len(parts) != 2:
                self.send_message(chat_id, "❌ Format incorrect ! Utilisez : /cos [1|2]")
                return

            try:
                position = int(parts[1])
                if position not in [1, 2]:
                    self.send_message(chat_id, "❌ Position invalide ! Utilisez 1 ou 2.")
                    return
            except ValueError:
                self.send_message(chat_id, "❌ Position invalide ! Utilisez 1 ou 2.")
                return

            # Set position preference
            if self.card_predictor:
                self.card_predictor.set_position_preference(position)
                position_text = "première" if position == 1 else "deuxième"
                self.send_message(
                    chat_id,
                    f"✅ DEPLOY299999 - Position mise à jour !\n\n"
                    f"🎯 Position : {position} ({position_text} carte)\n"
                    f"🔮 Prédictions utiliseront la {position_text} carte."
                )
            else:
                self.send_message(chat_id, "❌ Système de prédiction non disponible.")

        except Exception as e:
            logger.error(f"Error handling cos command: {e}")

    def _handle_cooldown_command(self, chat_id: int, text: str, user_id: int = None) -> None:
        """Handle /cooldown command"""
        try:
            if user_id and not self._is_authorized_user(user_id):
                self.send_message(chat_id, "🚫 Vous n'êtes pas autorisé à utiliser ce bot.")
                return

            parts = text.strip().split()
            if len(parts) == 1:
                # Show current cooldown
                current_cooldown = self.card_predictor.prediction_cooldown if self.card_predictor else 30
                self.send_message(
                    chat_id,
                    f"⏰ **COOLDOWN DEPLOY299999**\n\n"
                    f"🕒 Délai actuel: {current_cooldown} secondes\n\n"
                    f"💡 Usage: `/cooldown [secondes]`"
                )
                return

            if len(parts) != 2:
                self.send_message(chat_id, "❌ Format incorrect ! Usage: `/cooldown [secondes]`")
                return

            try:
                seconds = int(parts[1])
                if seconds < 30 or seconds > 600:
                    self.send_message(chat_id, "❌ Délai invalide ! Entre 30 et 600 secondes.")
                    return
            except ValueError:
                self.send_message(chat_id, "❌ Veuillez entrer un nombre valide.")
                return

            # Update cooldown
            if self.card_predictor:
                old_cooldown = self.card_predictor.prediction_cooldown
                self.card_predictor.prediction_cooldown = seconds
                self.send_message(
                    chat_id,
                    f"✅ **COOLDOWN DEPLOY299999 MIS À JOUR !**\n\n"
                    f"🕒 Ancien: {old_cooldown}s → Nouveau: {seconds}s"
                )
            else:
                self.send_message(chat_id, "❌ Système de prédiction non disponible.")

        except Exception as e:
            logger.error(f"Error handling cooldown command: {e}")

    def _handle_announce_command(self, chat_id: int, text: str, user_id: int = None) -> None:
        """Handle /announce command"""
        try:
            if user_id and not self._is_authorized_user(user_id):
                self.send_message(chat_id, "🚫 Vous n'êtes pas autorisé à utiliser ce bot.")
                return

            parts = text.strip().split(maxsplit=1)
            if len(parts) == 1:
                self.send_message(chat_id, "📢 Usage: `/announce [votre message]`")
                return

            announcement_text = parts[1]
            target_channel = self.get_redirect_channel(-1002682552255)

            formatted_message = f"📢 **ANNONCE DEPLOY299999** 📢\n\n{announcement_text}\n\n🤖 _Bot de prédiction DEPLOY299999 optimisé render.com_"

            sent_message_info = self.send_message(target_channel, formatted_message)
            if sent_message_info:
                self.send_message(chat_id, f"✅ **ANNONCE DEPLOY299999 ENVOYÉE !**")
            else:
                self.send_message(chat_id, "❌ Erreur lors de l'envoi de l'annonce.")

        except Exception as e:
            logger.error(f"Error handling announce command: {e}")

    def _handle_redirect_command(self, chat_id: int, text: str, user_id: int = None) -> None:
        """Handle /redirect command"""
        try:
            if user_id and not self._is_authorized_user(user_id):
                self.send_message(chat_id, "🚫 Vous n'êtes pas autorisé à utiliser ce bot.")
                return

            parts = text.strip().split()
            if len(parts) == 1:
                self.send_message(chat_id, "📍 Usage: `/redirect [source_id] [target_id]`")
                return

            if parts[1] == "clear":
                if self.card_predictor:
                    self.card_predictor.redirect_channels.clear()
                    self.send_message(chat_id, "✅ Redirections DEPLOY299999 supprimées !")
                return

            if len(parts) != 3:
                self.send_message(chat_id, "❌ Format incorrect ! Usage: `/redirect [source_id] [target_id]`")
                return

            try:
                source_id = int(parts[1].strip())
                target_id = int(parts[2].strip())
            except ValueError:
                self.send_message(chat_id, "❌ Les IDs doivent être des nombres.")
                return

            if self.card_predictor:
                self.card_predictor.set_redirect_channel(source_id, target_id)
                self.send_message(
                    chat_id,
                    f"✅ **REDIRECTION DEPLOY299999 CONFIGURÉE !**\n\n"
                    f"📍 {source_id} → {target_id}"
                )
            else:
                self.send_message(chat_id, "❌ Système de prédiction non disponible.")

        except Exception as e:
            logger.error(f"Error handling redirect command: {e}")

    def _handle_regular_message(self, message: Dict[str, Any]) -> None:
        """Handle regular text messages"""
        try:
            chat_id = message['chat']['id']
            chat_type = message['chat'].get('type', 'private')

            if chat_type == 'private':
                self.send_message(
                    chat_id,
                    "🎭 Salut ! Je suis le bot DEPLOY299999.\n"
                    "Utilisez /help pour voir mes commandes.\n\n"
                    "Optimisé pour render.com avec prédictions automatiques ! 🎯"
                )

        except Exception as e:
            logger.error(f"Error handling regular message: {e}")

    def _handle_new_chat_members(self, message: Dict[str, Any]) -> None:
        """Handle when bot is added to a channel"""
        try:
            chat_id = message['chat']['id']
            for member in message['new_chat_members']:
                if member.get('is_bot', False):
                    self.send_message(chat_id, GREETING_MESSAGE)
                    break
        except Exception as e:
            logger.error(f"Error handling new chat members: {e}")

    def _handle_redi_command(self, chat_id: int, sender_chat_id: int, user_id: int = None) -> None:
        """Handle /redi command"""
        try:
            if user_id and not self._is_authorized_user(user_id):
                self.send_message(chat_id, "🚫 Vous n'êtes pas autorisé à utiliser ce bot.")
                return
            self.redirected_channels[sender_chat_id] = chat_id
            self.send_message(chat_id, "✅ Redirection DEPLOY299999 configurée vers ce chat.")
        except Exception as e:
            logger.error(f"Error handling redi command: {e}")

    def _handle_reset_command(self, sender_chat_id: int, user_id: int = None) -> None:
        """Handle /reset command"""
        try:
            if user_id and not self._is_authorized_user(user_id):
                return
            if self.card_predictor:
                self.card_predictor.sent_predictions = {}
                self.send_message(sender_chat_id, "✅ Prédictions DEPLOY299999 réinitialisées.")
        except Exception as e:
            logger.error(f"Error handling reset command: {e}")

    def get_redirect_channel(self, source_chat_id: int) -> int:
        """Get redirect channel, defaults to PREDICTION_CHANNEL_ID"""
        if self.card_predictor and hasattr(self.card_predictor, 'redirect_channels'):
            redirect_target = self.card_predictor.redirect_channels.get(source_chat_id)
            if redirect_target:
                return redirect_target
        local_redirect = self.redirected_channels.get(source_chat_id)
        if local_redirect:
            return local_redirect
        return PREDICTION_CHANNEL_ID

    def send_message(self, chat_id: int, text: str) -> Any:
        """Send text message"""
        try:
            import requests
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            if result.get('ok'):
                return result.get('result', {})
            else:
                logger.error(f"Failed to send message: {result}")
                return False
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    def send_document(self, chat_id: int, file_path: str) -> bool:
        """Send document file"""
        try:
            import requests
            url = f"{self.base_url}/sendDocument"
            with open(file_path, 'rb') as file:
                files = {
                    'document': (os.path.basename(file_path), file, 'application/zip')
                }
                data = {
                    'chat_id': chat_id,
                    'caption': '📦 Package DEPLOY299999 pour render.com\n\n🎯 Prêt pour déploiement avec vérification et édition de messages !'
                }
                response = requests.post(url, data=data, files=files, timeout=60)
                result = response.json()
                return result.get('ok', False)
        except Exception as e:
            logger.error(f"Error sending document: {e}")
            return False

    def edit_message(self, chat_id: int, message_id: int, new_text: str) -> bool:
        """Edit an existing message - FONCTION CLEF DEPLOY299999"""
        try:
            import requests
            url = f"{self.base_url}/editMessageText"
            data = {
                'chat_id': chat_id,
                'message_id': message_id,
                'text': new_text,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            if result.get('ok'):
                logger.info(f"✅ DEPLOY299999 - Message édité avec succès dans chat {chat_id}")
                return True
            else:
                logger.error(f"❌ Failed to edit message: {result}")
                return False
        except Exception as e:
            logger.error(f"❌ Error editing message: {e}")
            return False
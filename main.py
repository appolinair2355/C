
"""
Main entry point for the Telegram bot deployment on Replit
Optimized for webhook deployment with enhanced verification system
"""
import os
import logging
from flask import Flask, request, jsonify
from bot import TelegramBot
from config import Config

# Configure logging with detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize bot with configuration
try:
    config = Config()
    bot = TelegramBot(config.BOT_TOKEN)
    logger.info("✅ Bot initialisé avec succès")
except Exception as e:
    logger.error(f"❌ Erreur initialisation bot: {e}")
    bot = None

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhook from Telegram with enhanced processing"""
    try:
        if not bot:
            logger.error("❌ Bot non initialisé")
            return 'Bot not initialized', 500
            
        update = request.get_json()
        
        if not update:
            logger.warning("⚠️ Update vide reçu")
            return 'Empty update', 400
        
        # Log type de message reçu avec détails
        if 'message' in update:
            msg = update['message']
            chat_id = msg.get('chat', {}).get('id', 'unknown')
            text = msg.get('text', '')[:50]
            logger.info(f"📨 WEBHOOK - Message normal reçu | Chat:{chat_id} | Text:{text}...")
        elif 'edited_message' in update:
            msg = update['edited_message']
            chat_id = msg.get('chat', {}).get('id', 'unknown')
            text = msg.get('text', '')[:50]
            logger.info(f"✏️ WEBHOOK - Message édité reçu | Chat:{chat_id} | Text:{text}...")
        
        # Traitement direct avec gestion des erreurs
        bot.handle_update(update)
        logger.info("✅ Update processed successfully via webhook")
        
        return 'OK', 200
    except Exception as e:
        logger.error(f"❌ Error handling webhook: {e}")
        return jsonify({'error': 'Webhook processing failed'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring"""
    try:
        bot_status = "healthy" if bot else "unhealthy"
        return jsonify({
            'status': bot_status, 
            'service': 'telegram-bot-deploy299999',
            'version': '2.1',
            'features': ['predictions', 'verification', 'edit_messages', 'cooldown'],
            'port': config.PORT if config else 'unknown'
        }), 200
    except Exception as e:
        logger.error(f"❌ Health check error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/', methods=['GET'])
def home():
    """Root endpoint with bot information"""
    try:
        return jsonify({
            'message': 'Telegram Bot DEPLOY299999 is running on Replit', 
            'status': 'active',
            'prediction_system': 'active' if bot else 'inactive',
            'verification_system': 'active' if bot else 'inactive',
            'deployment': 'replit',
            'port': config.PORT if config else 'unknown'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/status', methods=['GET'])
def status():
    """Detailed status endpoint"""
    try:
        if not bot:
            return jsonify({'error': 'Bot not initialized'}), 500
            
        # Get bot information
        bot_info = bot.get_bot_info()
        return jsonify({
            'bot_status': 'running',
            'bot_username': bot_info.get('username', 'unknown'),
            'webhook_configured': bool(config.WEBHOOK_URL),
            'prediction_channel': config.PREDICTION_CHANNEL_ID,
            'port': config.PORT,
            'deployment_platform': 'replit',
            'features': {
                'automatic_predictions': True,
                'message_verification': True,
                'status_updates': True,
                'cooldown_system': True,
                'edit_messages': True,
                'authorization': True
            }
        }), 200
    except Exception as e:
        logger.error(f"❌ Error getting status: {e}")
        return jsonify({'error': 'Status unavailable'}), 500

@app.route('/test', methods=['GET'])
def test_endpoint():
    """Test endpoint pour vérifier le fonctionnement"""
    try:
        if not bot:
            return jsonify({'test': 'failed', 'reason': 'bot not initialized'}), 500
            
        return jsonify({
            'test': 'success',
            'bot_token_present': bool(config.BOT_TOKEN),
            'handlers_loaded': hasattr(bot, 'handlers'),
            'predictor_loaded': bool(bot.handlers and bot.handlers.card_predictor),
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({'test': 'failed', 'error': str(e)}), 500

def setup_webhook():
    """Set up webhook on startup for Replit deployment"""
    try:
        if not bot:
            logger.error("❌ Cannot setup webhook - bot not initialized")
            return
            
        webhook_url = config.WEBHOOK_URL
        if webhook_url and webhook_url != "https://.repl.co":
            full_webhook_url = f"{webhook_url}/webhook"
            logger.info(f"🔗 Configuration webhook pour Replit: {full_webhook_url}")
            
            # Configure webhook avec URL Replit
            success = bot.set_webhook(full_webhook_url)
            if success:
                logger.info(f"✅ Webhook configuré avec succès sur Replit")
                logger.info(f"🎯 Bot DEPLOY299999 prêt - Prédictions + Vérifications + Éditions")
                logger.info(f"🌐 Port: {config.PORT} - URL: {webhook_url}")
            else:
                logger.error("❌ Échec configuration webhook Replit")
        else:
            logger.warning("⚠️ WEBHOOK_URL non configurée pour Replit")
            logger.info("💡 Mode polling recommandé pour développement")
    except Exception as e:
        logger.error(f"❌ Erreur configuration webhook Replit: {e}")

if __name__ == '__main__':
    # Configuration webhook au démarrage
    setup_webhook()
    
    # Port Replit (5000 par défaut, configurable)
    port = int(os.getenv('PORT', 5000))
    logger.info(f"🚀 DEPLOY299999 - Démarrage sur Replit port {port}")
    
    # Lancer l'application Flask pour Replit
    app.run(host='0.0.0.0', port=port, debug=False)

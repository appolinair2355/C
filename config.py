
"""
Configuration settings for Telegram Bot DEPLOY299999
Optimized for Replit deployment with automatic URL detection
"""
import os
import logging

logger = logging.getLogger(__name__)

class Config:
    """Configuration class for Replit deployment"""
    
    def __init__(self):
        # BOT_TOKEN - OBLIGATOIRE depuis variable d'environnement Replit
        self.BOT_TOKEN = os.getenv('BOT_TOKEN')
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN environment variable is required for Replit")
        
        # WEBHOOK_URL pour Replit (auto-détection améliorée)
        self.WEBHOOK_URL = self._get_replit_webhook_url()
        logger.info(f"🌐 Webhook URL Replit: {self.WEBHOOK_URL}")
        
        # Port pour Replit - 5000 par défaut (recommandé Replit)
        self.PORT = int(os.getenv('PORT', 5000))
        
        # Canal de destination pour les prédictions DEPLOY299999
        self.PREDICTION_CHANNEL_ID = -1002887687164
        
        # Mode debug (false en production Replit)
        self.DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
        
        # Variables spécifiques Replit
        self.REPLIT_MODE = self._is_replit_environment()
        
        # Validate configuration for Replit
        self._validate_config()
    
    def _get_replit_webhook_url(self) -> str:
        """Auto-détection URL webhook pour Replit"""
        # Méthode 1: Variable explicite
        explicit_url = os.getenv('WEBHOOK_URL')
        if explicit_url and explicit_url != "https://.repl.co":
            return explicit_url
        
        # Méthode 2: REPLIT_DOMAINS (nouvelle API)
        replit_domains = os.getenv('REPLIT_DOMAINS')
        if replit_domains:
            return f"https://{replit_domains}"
        
        # Méthode 3: Construction classique REPL_SLUG + REPL_OWNER
        repl_slug = os.getenv('REPL_SLUG', '')
        repl_owner = os.getenv('REPL_OWNER', '')
        if repl_slug and repl_owner:
            return f"https://{repl_slug}.{repl_owner}.repl.co"
        
        # Méthode 4: Recherche REPLIT_URL direct
        replit_url = os.getenv('REPLIT_URL')
        if replit_url:
            return replit_url
        
        # Fallback pour Replit
        logger.warning("⚠️ Impossible de détecter l'URL Replit automatiquement")
        return "https://your-repl.repl.co"
    
    def _is_replit_environment(self) -> bool:
        """Détecte si on est dans l'environnement Replit"""
        return (
            os.getenv('REPLIT_URL') is not None or
            os.getenv('REPL_SLUG') is not None or
            os.getenv('REPLIT_DOMAINS') is not None or
            'repl.co' in os.getenv('WEBHOOK_URL', '')
        )
    
    def _validate_config(self) -> None:
        """Validate configuration settings for Replit"""
        if not self.BOT_TOKEN:
            raise ValueError("Bot token is required for Replit deployment")
        
        if len(self.BOT_TOKEN.split(':')) != 2:
            raise ValueError("Invalid bot token format for Telegram")
        
        if self.WEBHOOK_URL and not self.WEBHOOK_URL.startswith('https://'):
            logger.warning("⚠️ Webhook URL should use HTTPS for Replit production")
        
        if self.PORT not in [5000, 8080, 3000]:
            logger.warning(f"⚠️ Port {self.PORT} détecté, Replit recommande 5000")
        
        logger.info("✅ Configuration validée pour Replit DEPLOY299999")
    
    def get_webhook_url(self) -> str:
        """Get full webhook URL for Replit"""
        if self.WEBHOOK_URL:
            return f"{self.WEBHOOK_URL}/webhook"
        return ""
    
    def is_replit_deployment(self) -> bool:
        """Check if running on Replit"""
        return self.REPLIT_MODE
    
    def get_environment_info(self) -> dict:
        """Get environment information for debugging"""
        return {
            'platform': 'replit' if self.is_replit_deployment() else 'other',
            'port': self.PORT,
            'debug': self.DEBUG,
            'webhook_configured': bool(self.WEBHOOK_URL),
            'replit_domains': os.getenv('REPLIT_DOMAINS'),
            'repl_slug': os.getenv('REPL_SLUG'),
            'repl_owner': os.getenv('REPL_OWNER')
        }
    
    def __str__(self) -> str:
        """String representation of config (without sensitive data)"""
        return f"Config(replit={self.is_replit_deployment()}, port={self.PORT}, debug={self.DEBUG})"

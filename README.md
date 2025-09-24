
# 🎯 Bot Telegram DEPLOY299999 - Replit

Bot de prédiction automatique avec système de vérification et édition de messages en temps réel, optimisé pour Replit.

## 🚀 Fonctionnalités DEPLOY299999

### ✨ Prédictions Automatiques
- Règle du miroir pour couleurs identiques (3+ occurrences)
- Cooldown configurable (30s par défaut)
- Exclusions automatiques (#R, #X, 🔰)
- Format : `🔵1435🔵:♦️statut :⏳`

### 🔍 Système de Vérification Avancé
- **Messages édités** avec ✅ ou 🔰
- **Messages normaux** avec ✅ ou 🔰
- Décalages : +0 (✅0️⃣), +1 (✅1️⃣), échec +2 (⭕)
- **Édition automatique** des messages de prédiction

### 📝 Édition de Messages
- Mise à jour automatique des statuts
- Format : `⏳` → `✅0️⃣` → `✅1️⃣` → `⭕`
- Persistance des messages stockés

## 🌐 Déploiement Replit

### Variables d'Environnement (Secrets)
```bash
BOT_TOKEN=7644537698:AAFjBt4dBfCB5YH4hxaPXV1bIXlNyIAQwjc
PORT=5000
WEBHOOK_URL=auto-détecté
```

### Auto-Configuration Replit
- **URL automatique** : Détection via REPLIT_DOMAINS
- **Port** : 5000 (recommandé Replit)
- **Webhook** : Configuration automatique au démarrage
- **Logging** : Fichier bot.log + console

## 🎯 Commandes

### Commandes de Base
- `/start` - Accueil DEPLOY299999
- `/help` - Guide complet
- `/deploy` - Package Replit

### Configuration
- `/cos [1|2]` - Position de carte
- `/cooldown [secondes]` - Délai prédictions
- `/redirect [source] [target]` - Redirection canaux

### Administration
- `/announce [message]` - Annonce officielle
- `/reset` - Réinitialiser prédictions

## 📊 Architecture

### Fichiers Principaux
- `main.py` - Serveur Flask webhook
- `bot.py` - Gestionnaire principal
- `handlers.py` - Commandes et événements
- `card_predictor.py` - Système de prédiction
- `config.py` - Configuration Replit

### Endpoints
- `/` - Statut général
- `/webhook` - Réception Telegram
- `/health` - Monitoring
- `/status` - Détails système
- `/test` - Test fonctionnement

### Canaux
- **Source** : -1002682552255 (Baccarat Kouamé)
- **Destination** : -1002887687164 (Prédictions)

## 🔧 Fonctionnement Technique

### Webhook Flask
```python
@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    bot.handle_update(update)
    return 'OK', 200
```

### Auto-détection URL Replit
```python
def _get_replit_webhook_url(self):
    # REPLIT_DOMAINS (nouvelle API)
    if os.getenv('REPLIT_DOMAINS'):
        return f"https://{os.getenv('REPLIT_DOMAINS')}"
    
    # Classique REPL_SLUG + REPL_OWNER
    repl_slug = os.getenv('REPL_SLUG')
    repl_owner = os.getenv('REPL_OWNER')
    return f"https://{repl_slug}.{repl_owner}.repl.co"
```

### Édition de Messages
```python
def edit_message(chat_id, message_id, new_text):
    # API Telegram editMessageText
    return requests.post(url, json=data)
```

## 🎯 Statuts de Prédiction

- `⏳` - En attente
- `✅0️⃣` - Succès immédiat (décalage 0)
- `✅1️⃣` - Succès au jeu suivant (+1)
- `⭕` - Échec après 2 tentatives

## 🚀 Instructions Déploiement Replit

### 1. Configuration Secrets
1. Aller dans **Secrets** (panneau latéral)
2. Ajouter `BOT_TOKEN` avec la valeur du token
3. (Optionnel) Ajouter `PORT=5000`

### 2. Démarrage
1. Cliquer sur **Run** ou exécuter `python main.py`
2. Le webhook se configure automatiquement
3. Vérifier les logs pour confirmation

### 3. Vérification
- Accéder à `https://votre-repl.repl.co/health`
- Vérifier le statut : `{"status": "healthy"}`
- Tester avec `/start` sur Telegram

## 🎯 Production Ready Replit

- ✅ Auto-détection URL Replit
- ✅ Port 5000 configuré (recommandé)
- ✅ Health checks et monitoring
- ✅ Logging détaillé (console + fichier)
- ✅ Gestion d'erreurs robuste
- ✅ Rate limiting intégré
- ✅ Autorisation utilisateur stricte

## 📝 Logs et Debug

### Fichiers de Log
- **Console** : Logs en temps réel
- **bot.log** : Fichier persistent

### Endpoints de Debug
- `/test` - Test complet du système
- `/status` - Informations détaillées
- `/health` - Statut de santé

---

**DEPLOY299999** - Version 2.1 - Optimisé Replit - Prêt pour production

🎯 **Token configuré** : `7644537698:AAFjBt4dBfCB5YH4hxaPXV1bIXlNyIAQwjc`

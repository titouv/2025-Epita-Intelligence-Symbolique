# ui/config.py
import os
import logging
from pathlib import Path
from dotenv import load_dotenv, find_dotenv # Gardé au cas où d'autres variables .env sont utilisées
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import json
from argumentation_analysis.paths import DATA_DIR

config_logger = logging.getLogger("App.UI.Config")
if not config_logger.handlers and not config_logger.propagate:
     handler = logging.StreamHandler(); formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'); handler.setFormatter(formatter); config_logger.addHandler(handler); config_logger.setLevel(logging.INFO)

# --- Chargement .env et Dérivation Clé ---
load_dotenv(find_dotenv()) # Gardé au cas où d'autres variables .env sont utilisées

# MODIFICATION: Utiliser directement "Propaganda" comme passphrase
TEXT_CONFIG_PASSPHRASE = "Propaganda"
passphrase = TEXT_CONFIG_PASSPHRASE # Assignation directe
ENCRYPTION_KEY = None
FIXED_SALT = b'q\x8b\t\x97\x8b\xe9\xa3\xf2\xe4\x8e\xea\xf5\xe8\xb7\xd6\x8c' # Sel fixe

config_logger.info(f"Utilisation de la phrase secrète fixe pour la dérivation de la clé.")
if passphrase: # Cette condition sera toujours vraie maintenant
    config_logger.info(f"✅ Phrase secrète définie sur \"{passphrase}\". Dérivation de la clé...")
    try:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(), length=32, salt=FIXED_SALT,
            iterations=480000, backend=default_backend()
        )
        derived_key_raw = kdf.derive(passphrase.encode('utf-8'))
        ENCRYPTION_KEY = base64.urlsafe_b64encode(derived_key_raw)
        if ENCRYPTION_KEY: config_logger.info("✅ Clé de chiffrement dérivée et encodée.")
    except Exception as e:
        config_logger.error(f"⚠️ Erreur dérivation clé : {e}. Chiffrement désactivé.", exc_info=True)
        ENCRYPTION_KEY = None
else:
    # Ce bloc ne devrait plus être atteint car passphrase est maintenant fixée.
    config_logger.critical(f"⚠️ La phrase secrète n'est pas définie malgré la modification. Problème inattendu.")
    ENCRYPTION_KEY = None

# --- URLs et Chemins ---
# Utiliser l'URL du serveur Tika depuis le fichier .env ou utiliser l'URL par défaut
# Assurez-vous que l'URL du serveur Tika se termine par '/tika'
tika_url = os.getenv("TIKA_SERVER_ENDPOINT", "https://tika.open-webui.myia.io/tika")
TIKA_SERVER_URL = tika_url if tika_url.endswith('/tika') else f"{tika_url.rstrip('/')}/tika"
TIKA_SERVER_TIMEOUT = int(os.getenv("TIKA_SERVER_TIMEOUT", "30"))
config_logger.info(f"URL du serveur Tika: {TIKA_SERVER_URL}")
JINA_READER_PREFIX = "https://r.jina.ai/"

# Chemins relatifs au projet
_project_root = Path(__file__).parent.parent # Remonte de ui/ vers la racine
CACHE_DIR = _project_root / "text_cache"
CONFIG_DIR = _project_root / DATA_DIR # Fichier de config UI dans data/
CONFIG_FILE_JSON = CONFIG_DIR / "extract_sources.json" # Chemin vers le fichier JSON non chiffré
CONFIG_FILE_ENC = CONFIG_DIR / "extract_sources.json.gz.enc" # Chemin vers le futur fichier chiffré
CONFIG_FILE = CONFIG_FILE_ENC  # Variable utilisée par app.py pour charger les définitions
TEMP_DOWNLOAD_DIR = _project_root / "temp_downloads" # Pour cache brut Tika

# Extensions texte simple
PLAINTEXT_EXTENSIONS = ['.txt', '.md', '.json', '.csv', '.xml', '.py', '.js', '.html', '.htm']

# Création des répertoires nécessaires
try:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    config_logger.info(f"Cache répertoire assuré : {CACHE_DIR.resolve()}")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True) # S'assurer que data/ existe
    config_logger.info(f"Répertoire config UI assuré : {CONFIG_DIR.resolve()}")
    TEMP_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    config_logger.info(f"Répertoire temporaire assuré : {TEMP_DOWNLOAD_DIR.resolve()}")
except Exception as e:
    config_logger.error(f"Erreur création répertoires (cache/config/temp): {e}")


# --- Définitions Sources par Défaut ---
DEFAULT_EXTRACT_SOURCES = [
    {"source_name": "Exemple Vide (Config manquante)", "source_type": "jina",
     "schema": "https:", "host_parts": ["example", "com"], "path": "/",
     "extracts": []}
]

# --- Chargement des Sources d'Extraction ---

def load_extract_sources(config_path: Path) -> list:
    """Charge les définitions des sources depuis un fichier JSON."""
    if config_path.exists() and config_path.is_file():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                sources = json.load(f)
            config_logger.info(f"✅ Configuration chargée depuis {config_path.name}")
            return sources
        except json.JSONDecodeError as e:
            config_logger.warning(f"⚠️ Erreur décodage JSON dans {config_path.name}: {e}. Utilisation config par défaut.")
            return DEFAULT_EXTRACT_SOURCES
        except Exception as e:
            config_logger.error(f"❌ Erreur lecture fichier config {config_path.name}: {e}. Utilisation config par défaut.", exc_info=True)
            return DEFAULT_EXTRACT_SOURCES
    else:
        config_logger.warning(f"⚠️ Fichier config {config_path.name} non trouvé. Utilisation config par défaut.")
        return DEFAULT_EXTRACT_SOURCES

# Tentative de chargement des sources depuis le fichier chiffré
EXTRACT_SOURCES = DEFAULT_EXTRACT_SOURCES

# Si la clé de chiffrement est disponible, essayer de charger depuis le fichier chiffré
if ENCRYPTION_KEY and CONFIG_FILE_ENC.exists():
    try:
        config_logger.info(f"Tentative de chargement depuis le fichier chiffré {CONFIG_FILE_ENC.name}...")
        # Import local pour éviter l'import circulaire
        from .file_operations import load_extract_definitions
        # load_extract_definitions de file_operations n'a pas besoin d'app_config pour le chargement simple
        loaded_sources = load_extract_definitions(CONFIG_FILE_ENC, ENCRYPTION_KEY)
        if loaded_sources:
            EXTRACT_SOURCES = loaded_sources
            config_logger.info(f"✅ Définitions chargées depuis le fichier chiffré {CONFIG_FILE_ENC.name}.")
        else:
            config_logger.warning(f"⚠️ Échec du chargement depuis le fichier chiffré. Utilisation des définitions par défaut.")
    except Exception as e:
        config_logger.error(f"❌ Erreur lors du chargement du fichier chiffré: {e}", exc_info=True)
elif CONFIG_FILE_JSON.exists() and ENCRYPTION_KEY:
    # Migration: si le fichier JSON existe mais pas le fichier chiffré, créer le fichier chiffré
    try:
        from .file_operations import save_extract_definitions # MODIFIÉ
        config_logger.info(f"Migration: création du fichier chiffré à partir de {CONFIG_FILE_JSON.name}...")
        json_sources = load_extract_sources(CONFIG_FILE_JSON)
        # save_extract_definitions de file_operations attend encryption_key et config_file
        # et le paramètre 'config' (app_config) est optionnel si embed_full_text=False
        success = save_extract_definitions(
            extract_definitions=json_sources,
            config_file=CONFIG_FILE_ENC,
            encryption_key=ENCRYPTION_KEY,
            embed_full_text=False # Pour la migration initiale, ne pas essayer de fetch
        )
        if success:
            config_logger.info(f"✅ Fichier chiffré {CONFIG_FILE_ENC.name} créé avec succès à partir de {CONFIG_FILE_JSON.name}.")
            EXTRACT_SOURCES = json_sources
            # Suppression du fichier JSON après migration réussie
            try:
                CONFIG_FILE_JSON.unlink()
                config_logger.info(f"✅ Fichier JSON {CONFIG_FILE_JSON.name} supprimé après migration.")
            except Exception as e_unlink:
                config_logger.warning(f"⚠️ Impossible de supprimer le fichier JSON après migration: {e_unlink}")
        else:
            config_logger.warning(f"⚠️ Échec de la migration vers le fichier chiffré. Utilisation des définitions par défaut.")
    except Exception as e:
        config_logger.error(f"❌ Erreur lors de la migration vers le fichier chiffré: {e}", exc_info=True)

# --- État Global (pour ce module UI) ---
# Note: Utiliser global ici est une simplification liée à la structure UI originale.
# Une approche plus orientée objet pourrait encapsuler cela.
current_extract_definitions = [] # Sera peuplé par load_extract_definitions

config_logger.info(f"Config UI initialisée. {len(EXTRACT_SOURCES)} sources chargées.")
# argumentation_analysis/ui/file_operations.py
from typing import Optional, Union, List, Dict, Any
import json
import gzip
import logging
import base64 
from pathlib import Path
# from typing import Optional, List, Dict, Any # Redondant avec la première ligne
from cryptography.fernet import InvalidToken 

from . import config as ui_config_module
from .utils import get_full_text_for_source, utils_logger 
from argumentation_analysis.utils.core_utils.crypto_utils import encrypt_data_with_fernet, decrypt_data_with_fernet

file_ops_logger = utils_logger


def load_extract_definitions(
    config_file: Path,
    b64_derived_key: Optional[str],
    app_config: Optional[Dict[str, Any]] = None,
    raise_on_decrypt_error: bool = False
) -> list:
    """Charge, déchiffre et décompresse les définitions depuis le fichier chiffré."""
    # Utiliser uniquement DEFAULT_EXTRACT_SOURCES comme fallback pour éviter le cycle avec EXTRACT_SOURCES
    # qui est en cours de définition par l'appelant (config.py)
    fallback_definitions = ui_config_module.DEFAULT_EXTRACT_SOURCES

    if not config_file.exists():
        file_ops_logger.info(f"Fichier config '{config_file}' non trouvé. Utilisation définitions par défaut.")
        return [item.copy() for item in fallback_definitions]

    if b64_derived_key: # Clé fournie, tenter le déchiffrement
        file_ops_logger.info(f"Chargement et déchiffrement de '{config_file}' avec clé...")
        try:
            with open(config_file, 'rb') as f: encrypted_data = f.read()
            decrypted_compressed_data = decrypt_data_with_fernet(encrypted_data, b64_derived_key)
            
            if not decrypted_compressed_data:
                file_ops_logger.error(f"Échec du déchiffrement pour '{config_file}'. Le token est peut-être invalide.")
                raise InvalidToken(f"Échec du déchiffrement pour '{config_file}'.")

            decompressed_data = gzip.decompress(decrypted_compressed_data)
            definitions = json.loads(decompressed_data.decode('utf-8'))
            file_ops_logger.info("✅ Définitions chargées et déchiffrées.")

        except InvalidToken:
            # Ce bloc est spécifiquement pour quand decrypt_data_with_fernet lève InvalidToken
            file_ops_logger.error(f"❌ Token invalide (InvalidToken) lors du déchiffrement de '{config_file}'.", exc_info=True)
            if raise_on_decrypt_error:
                raise
            return [item.copy() for item in fallback_definitions]
        except Exception as e:
            file_ops_logger.error(f"[FAIL] Erreur chargement/dechiffrement '{config_file}': {e}. Utilisation definitions par defaut.", exc_info=True)
            return [item.copy() for item in fallback_definitions]
    
    else: # Pas de clé, essayer de lire comme JSON simple
        file_ops_logger.info(f"Aucune clé fournie. Tentative de chargement de '{config_file}' comme JSON simple...")
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                definitions = json.load(f)
            file_ops_logger.info(f"[OK] Définitions chargées comme JSON simple depuis '{config_file}'.")
        
        except json.JSONDecodeError as e_json:
            file_ops_logger.error(f"[FAIL] Erreur decodage JSON pour '{config_file}': {e_json}. L'exception sera relancee.", exc_info=False)
            raise
        except Exception as e:
            file_ops_logger.error(f"[FAIL] Erreur chargement JSON simple '{config_file}': {e}. Utilisation definitions par defaut.", exc_info=True)
            return [item.copy() for item in fallback_definitions]

    # Validation du format (commun aux deux chemins)
    if not isinstance(definitions, list) or not all(
        isinstance(item, dict) and
        "source_name" in item and "source_type" in item and "schema" in item and
        "host_parts" in item and "path" in item and isinstance(item.get("extracts"), list)
        for item in definitions
    ):
        file_ops_logger.warning(f"[WARN] Format definitions invalide apres chargement de '{config_file}'. Utilisation definitions par defaut.")
        return [item.copy() for item in fallback_definitions]

    file_ops_logger.info(f"-> {len(definitions)} définitions chargées depuis '{config_file}'.")
    return definitions

def save_extract_definitions(
    extract_definitions: List[Dict[str, Any]],
    config_file: Path,
    b64_derived_key: Optional[Union[str, bytes]], 
    embed_full_text: bool = False,
    config: Optional[Dict[str, Any]] = None 
) -> bool:
    """Sauvegarde, compresse et chiffre les définitions dans le fichier.
    Peut optionnellement embarquer le texte complet des sources.
    """
    if not b64_derived_key: 
        file_ops_logger.error("Clé chiffrement (b64_derived_key) absente ou vide. Sauvegarde annulée.")
        return False
    if not isinstance(extract_definitions, list):
        file_ops_logger.error("Erreur sauvegarde: définitions non valides (doit être une liste).")
        return False

    file_ops_logger.info(f"Préparation sauvegarde vers '{config_file}'...")

    definitions_to_process = [dict(d) for d in extract_definitions]


    if embed_full_text:
        file_ops_logger.info("Option embed_full_text activée. Tentative de récupération des textes complets manquants...")
        for source_info in definitions_to_process: 
            if not isinstance(source_info, dict):
                file_ops_logger.warning(f"Élément non-dictionnaire ignoré dans extract_definitions: {type(source_info)}")
                continue

            current_full_text = source_info.get("full_text")
            if not current_full_text:
                source_name = source_info.get('source_name', 'Source inconnue')
                file_ops_logger.info(f"Texte complet manquant pour '{source_name}'. Récupération...")
                try:
                    retrieved_text = get_full_text_for_source(source_info, app_config=config)
                    if retrieved_text is not None:
                        source_info["full_text"] = retrieved_text
                        file_ops_logger.info(f"Texte complet récupéré et ajouté pour '{source_name}'.")
                    else:
                        file_ops_logger.warning(f"Échec de la récupération du texte complet (texte vide retourné) pour '{source_name}'. Champ 'full_text' non peuplé.")
                        source_info["full_text"] = None
                except ConnectionError as e_conn:
                    file_ops_logger.warning(f"Erreur de connexion lors de la récupération du texte pour '{source_name}': {e_conn}. Champ 'full_text' non peuplé.")
                    source_info["full_text"] = None
                except Exception as e_get_text:
                    file_ops_logger.error(f"Erreur inattendue lors de la récupération du texte pour '{source_name}': {e_get_text}. Champ 'full_text' non peuplé.", exc_info=True)
                    source_info["full_text"] = None
    else:
        file_ops_logger.info("Option embed_full_text désactivée. Suppression des textes complets des définitions...")
        for source_info in definitions_to_process: 
            if not isinstance(source_info, dict):
                continue
            if "full_text" in source_info:
                source_info.pop("full_text", None)
                file_ops_logger.debug(f"Champ 'full_text' retiré pour '{source_info.get('source_name', 'Source inconnue')}'.")

    try:
        json_data = json.dumps(definitions_to_process, indent=2, ensure_ascii=False).encode('utf-8')
        compressed_data = gzip.compress(json_data)
        encrypted_data_to_save = encrypt_data_with_fernet(compressed_data, b64_derived_key)
        if not encrypted_data_to_save:
            raise ValueError("Échec du chiffrement des données (encrypt_data_with_fernet a retourné None).")

        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'wb') as f:
            f.write(encrypted_data_to_save)
        file_ops_logger.info(f"[OK] Définitions sauvegardées dans '{config_file}'.")
        return True
    except Exception as e:
        file_ops_logger.error(f"[FAIL] Erreur lors de la sauvegarde chiffrée vers '{config_file}': {e}", exc_info=True)
        return False

file_ops_logger.info("Fonctions d'opérations sur fichiers UI définies.")
# -*- coding: utf-8 -*-
"""Tests pour les utilitaires de cryptographie."""

import pytest
import os
from unittest.mock import patch
from argumentation_analysis.core.utils.crypto_utils import (
    derive_encryption_key,
    load_encryption_key,
    encrypt_data_with_fernet,
    decrypt_data_with_fernet
)

# FIXED_SALT est défini dans crypto_utils, pas besoin de le redéfinir ici.

def test_derive_encryption_key_success():
    """Teste la dérivation de clé réussie."""
    passphrase = "ma_super_phrase_secrete_de_test"
    key1 = derive_encryption_key(passphrase)
    assert key1 is not None
    assert isinstance(key1, bytes)
    
    key2 = derive_encryption_key(passphrase)
    assert key1 == key2, "La dérivation de clé doit être déterministe pour la même passphrase et le même sel."

def test_derive_encryption_key_empty_passphrase():
    """Teste la dérivation avec une phrase secrète vide."""
    key = derive_encryption_key("")
    assert key is None, "Doit retourner None pour une passphrase vide."

def test_derive_encryption_key_type():
    """Vérifie que la clé retournée est bien de type bytes."""
    key = derive_encryption_key("une_passphrase_valide")
    assert isinstance(key, bytes)

# Tests pour load_encryption_key
@patch.dict(os.environ, {}, clear=True) # Assure un environnement propre pour chaque test de variable d'env
def test_load_encryption_key_from_arg():
    """Teste le chargement de la clé depuis l'argument passphrase."""
    passphrase_arg = "arg_passphrase"
    expected_key = derive_encryption_key(passphrase_arg)
    
    loaded_key = load_encryption_key(passphrase_arg=passphrase_arg)
    assert loaded_key == expected_key

@patch.dict(os.environ, {}, clear=True)
@patch('argumentation_analysis.core.utils.crypto_utils.settings')
def test_load_encryption_key_from_settings(mock_settings):
    """Teste le chargement de la clé depuis la configuration centrale."""
    passphrase = "settings_passphrase"
    mock_settings.passphrase.get_secret_value.return_value = passphrase
    mock_settings.passphrase_arg = None # Assurer que l'argument direct n'est pas utilisé
    
    expected_key = derive_encryption_key(passphrase)
    
    # Configure la valeur de retour pour le mock settings
    loaded_key = load_encryption_key() # Ne pas passer d'argument direct
    
    assert loaded_key == expected_key
    mock_settings.passphrase.get_secret_value.assert_called_once()

@patch('argumentation_analysis.core.utils.crypto_utils.settings')
def test_load_encryption_key_arg_priority_over_settings(mock_settings):
    """Teste que l'argument passphrase a la priorité sur la configuration centrale."""
    passphrase_arg = "priority_passphrase"
    
    # Même si les settings existent, ils ne devraient pas être utilisés
    mock_settings.passphrase.get_secret_value.return_value = "should_be_ignored"
    
    expected_key = derive_encryption_key(passphrase_arg)
    loaded_key = load_encryption_key(passphrase_arg=passphrase_arg)
    
    assert loaded_key == expected_key
    mock_settings.passphrase.get_secret_value.assert_not_called()

@patch.dict(os.environ, {}, clear=True)
@patch('argumentation_analysis.core.utils.crypto_utils.settings', passphrase=None)
def test_load_encryption_key_no_source(mock_settings):
    """Teste le cas où aucune source de passphrase n'est disponible."""
    loaded_key = load_encryption_key()
    assert loaded_key is None

@patch('argumentation_analysis.core.utils.crypto_utils.settings')
def test_load_encryption_key_empty_settings_passphrase(mock_settings):
    """Teste le cas où la configuration centrale contient une passphrase vide."""
    mock_settings.passphrase.get_secret_value.return_value = ""
    mock_settings.passphrase_arg = None
    
    loaded_key = load_encryption_key()
    assert loaded_key is None

# Tests pour encrypt_data_with_fernet et decrypt_data_with_fernet
def test_fernet_encryption_decryption_cycle():
    """Teste un cycle complet de chiffrement et déchiffrement Fernet."""
    test_data = b"Donn\xc3\xa9es secr\xc3\xa8tes \xc3\xa0 chiffrer!"
    passphrase = "uneAutrePhrasePourFernet"
    
    derived_key_bytes = derive_encryption_key(passphrase)
    assert derived_key_bytes is not None, "La dérivation de clé a échoué avant le test Fernet."

    encrypted = encrypt_data_with_fernet(test_data, derived_key_bytes)
    assert encrypted is not None, "Le chiffrement Fernet a échoué."
    assert encrypted != test_data, "Les données chiffrées doivent être différentes des originales."

    decrypted = decrypt_data_with_fernet(encrypted, derived_key_bytes)
    assert decrypted is not None, "Le déchiffrement Fernet a échoué."
    assert decrypted == test_data, "Les données déchiffrées ne correspondent pas aux originales."

def test_decrypt_with_wrong_key_fernet():
    """Teste le déchiffrement Fernet avec une mauvaise clé."""
    test_data = b"Test data for wrong key."
    correct_passphrase = "correct_fernet_pass"
    wrong_passphrase = "wrong_fernet_pass"

    correct_key_bytes = derive_encryption_key(correct_passphrase)
    wrong_key_bytes = derive_encryption_key(wrong_passphrase)

    assert correct_key_bytes is not None
    assert wrong_key_bytes is not None
    assert correct_key_bytes != wrong_key_bytes, "Les clés correcte et incorrecte doivent être différentes."

    encrypted_with_correct_key = encrypt_data_with_fernet(test_data, correct_key_bytes)
    assert encrypted_with_correct_key is not None

    decrypted_with_wrong_key = decrypt_data_with_fernet(encrypted_with_correct_key, wrong_key_bytes)
    assert decrypted_with_wrong_key is None, "Le déchiffrement avec une mauvaise clé doit retourner None (InvalidToken)."

def test_encrypt_decrypt_empty_data_fernet():
    """Teste le chiffrement/déchiffrement de données vides."""
    empty_data = b""
    passphrase = "fernet_empty_data_test"
    key_bytes = derive_encryption_key(passphrase)
    assert key_bytes is not None

    encrypted = encrypt_data_with_fernet(empty_data, key_bytes)
    assert encrypted is not None
    
    decrypted = decrypt_data_with_fernet(encrypted, key_bytes)
    assert decrypted == empty_data

def test_encrypt_with_no_key_fernet():
    """Teste le chiffrement avec une clé None."""
    test_data = b"some data"
    encrypted = encrypt_data_with_fernet(test_data, None)
    assert encrypted is None

def test_decrypt_with_no_key_fernet():
    """Teste le déchiffrement avec une clé None."""
    test_data_encrypted = b"some encrypted data" # La validité n'importe pas ici
    decrypted = decrypt_data_with_fernet(test_data_encrypted, None)
    assert decrypted is None
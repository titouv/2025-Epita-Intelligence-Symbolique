#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
API Flask pour l'analyse argumentative.

Cette API expose les fonctionnalités du moteur d'analyse argumentative
pour permettre aux étudiants de créer des interfaces web facilement.
"""

import os
import sys
import logging
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import Dict, Any, Optional

# Import des services
from argumentation_analysis.services.web_api.services.analysis_service import AnalysisService
from argumentation_analysis.services.web_api.services.validation_service import ValidationService
from argumentation_analysis.services.web_api.services.fallacy_service import FallacyService
from argumentation_analysis.services.web_api.services.framework_service import FrameworkService
from argumentation_analysis.services.web_api.services.logic_service import LogicService
from argumentation_analysis.services.web_api.models.request_models import (
    AnalysisRequest, ValidationRequest, FallacyRequest, FrameworkRequest,
    LogicBeliefSetRequest, LogicQueryRequest, LogicGenerateQueriesRequest, LogicOptions
)
from argumentation_analysis.services.web_api.models.response_models import (
    AnalysisResponse, ValidationResponse, FallacyResponse, FrameworkResponse, ErrorResponse,
    LogicBeliefSetResponse, LogicQueryResponse, LogicGenerateQueriesResponse, LogicInterpretationResponse, LogicQueryResult
)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("WebAPI")

# Création de l'application Flask
app = Flask(__name__)
CORS(app)  # Activer CORS pour les appels depuis React

# Configuration
app.config['JSON_AS_ASCII'] = False  # Support des caractères UTF-8
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

# Initialisation des services
analysis_service = AnalysisService()
validation_service = ValidationService()
fallacy_service = FallacyService()
framework_service = FrameworkService()
logic_service = LogicService()


@app.errorhandler(Exception)
def handle_error(error):
    """Gestionnaire d'erreurs global."""
    logger.error(f"Erreur non gérée: {str(error)}", exc_info=True)
    return jsonify(ErrorResponse(
        error="Erreur interne du serveur",
        message=str(error),
        status_code=500
    ).dict()), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Vérification de l'état de l'API."""
    try:
        return jsonify({
            "status": "healthy",
            "message": "API d'analyse argumentative opérationnelle",
            "version": "1.0.0",
            "services": {
                "analysis": analysis_service.is_healthy(),
                "validation": validation_service.is_healthy(),
                "fallacy": fallacy_service.is_healthy(),
                "framework": framework_service.is_healthy(),
                "logic": logic_service.is_healthy()
            }
        })
    except Exception as e:
        logger.error(f"Erreur lors du health check: {str(e)}")
        return jsonify(ErrorResponse(
            error="Erreur de health check",
            message=str(e),
            status_code=500
        ).dict()), 500


@app.route('/api/analyze', methods=['POST'])
def analyze_text():
    """
    Analyse complète d'un texte argumentatif.
    
    Body JSON:
    {
        "text": "Texte à analyser",
        "options": {
            "detect_fallacies": true,
            "analyze_structure": true,
            "evaluate_coherence": true
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(
                error="Données manquantes",
                message="Le body JSON est requis",
                status_code=400
            ).dict()), 400
        
        # Validation de la requête
        try:
            analysis_request = AnalysisRequest(**data)
        except Exception as e:
            return jsonify(ErrorResponse(
                error="Données invalides",
                message=f"Erreur de validation: {str(e)}",
                status_code=400
            ).dict()), 400
        
        # Analyse du texte
        result = analysis_service.analyze_text(analysis_request)
        
        return jsonify(result.dict())
        
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse: {str(e)}")
        return jsonify(ErrorResponse(
            error="Erreur d'analyse",
            message=str(e),
            status_code=500
        ).dict()), 500


@app.route('/api/validate', methods=['POST'])
def validate_argument():
    """
    Validation logique d'un argument.
    
    Body JSON:
    {
        "premises": ["Prémisse 1", "Prémisse 2"],
        "conclusion": "Conclusion",
        "argument_type": "deductive"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(
                error="Données manquantes",
                message="Le body JSON est requis",
                status_code=400
            ).dict()), 400
        
        # Validation de la requête
        try:
            validation_request = ValidationRequest(**data)
        except Exception as e:
            return jsonify(ErrorResponse(
                error="Données invalides",
                message=f"Erreur de validation: {str(e)}",
                status_code=400
            ).dict()), 400
        
        # Validation de l'argument
        result = validation_service.validate_argument(validation_request)
        
        return jsonify(result.dict())
        
    except Exception as e:
        logger.error(f"Erreur lors de la validation: {str(e)}")
        return jsonify(ErrorResponse(
            error="Erreur de validation",
            message=str(e),
            status_code=500
        ).dict()), 500


@app.route('/api/fallacies', methods=['POST'])
def detect_fallacies():
    """
    Détection de sophismes dans un texte.
    
    Body JSON:
    {
        "text": "Texte à analyser",
        "options": {
            "severity_threshold": 0.5,
            "include_context": true
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(
                error="Données manquantes",
                message="Le body JSON est requis",
                status_code=400
            ).dict()), 400
        
        # Validation de la requête
        try:
            fallacy_request = FallacyRequest(**data)
        except Exception as e:
            return jsonify(ErrorResponse(
                error="Données invalides",
                message=f"Erreur de validation: {str(e)}",
                status_code=400
            ).dict()), 400
        
        # Détection des sophismes
        result = fallacy_service.detect_fallacies(fallacy_request)
        
        return jsonify(result.dict())
        
    except Exception as e:
        logger.error(f"Erreur lors de la détection de sophismes: {str(e)}")
        return jsonify(ErrorResponse(
            error="Erreur de détection",
            message=str(e),
            status_code=500
        ).dict()), 500


@app.route('/api/framework', methods=['POST'])
def build_framework():
    """
    Construction d'un framework de Dung.
    
    Body JSON:
    {
        "arguments": [
            {
                "id": "arg1",
                "content": "Contenu de l'argument",
                "attacks": ["arg2"]
            }
        ],
        "options": {
            "compute_extensions": true,
            "semantics": "preferred"
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(
                error="Données manquantes",
                message="Le body JSON est requis",
                status_code=400
            ).dict()), 400
        
        # Validation de la requête
        try:
            framework_request = FrameworkRequest(**data)
        except Exception as e:
            return jsonify(ErrorResponse(
                error="Données invalides",
                message=f"Erreur de validation: {str(e)}",
                status_code=400
            ).dict()), 400
        
        # Construction du framework
        result = framework_service.build_framework(framework_request)
        
        return jsonify(result.dict())
        
    except Exception as e:
        logger.error(f"Erreur lors de la construction du framework: {str(e)}")
        return jsonify(ErrorResponse(
            error="Erreur de framework",
            message=str(e),
            status_code=500
        ).dict()), 500


@app.route('/api/endpoints', methods=['GET'])
def list_endpoints():
    """Liste tous les endpoints disponibles avec leur documentation."""
    endpoints = {
        "GET /api/health": {
            "description": "Vérification de l'état de l'API",
            "parameters": None,
            "response": "Status de l'API et des services"
        },
        "POST /api/analyze": {
            "description": "Analyse complète d'un texte argumentatif",
            "parameters": {
                "text": "string (requis) - Texte à analyser",
                "options": "object (optionnel) - Options d'analyse"
            },
            "response": "Résultat complet de l'analyse"
        },
        "POST /api/validate": {
            "description": "Validation logique d'un argument",
            "parameters": {
                "premises": "array[string] (requis) - Liste des prémisses",
                "conclusion": "string (requis) - Conclusion",
                "argument_type": "string (optionnel) - Type d'argument"
            },
            "response": "Résultat de la validation"
        },
        "POST /api/fallacies": {
            "description": "Détection de sophismes",
            "parameters": {
                "text": "string (requis) - Texte à analyser",
                "options": "object (optionnel) - Options de détection"
            },
            "response": "Liste des sophismes détectés"
        },
        "POST /api/framework": {
            "description": "Construction d'un framework de Dung",
            "parameters": {
                "arguments": "array (requis) - Liste des arguments",
                "options": "object (optionnel) - Options du framework"
            },
            "response": "Framework construit avec extensions"
        },
        "POST /api/logic/belief-set": {
            "description": "Conversion d'un texte en ensemble de croyances logiques",
            "parameters": {
                "text": "string (requis) - Texte à convertir",
                "logic_type": "string (requis) - Type de logique (propositional, first_order, modal)",
                "options": "object (optionnel) - Options de conversion"
            },
            "response": "Ensemble de croyances créé"
        },
        "POST /api/logic/query": {
            "description": "Exécution d'une requête logique",
            "parameters": {
                "belief_set_id": "string (requis) - ID de l'ensemble de croyances",
                "query": "string (requis) - Requête logique à exécuter",
                "logic_type": "string (requis) - Type de logique",
                "options": "object (optionnel) - Options d'exécution"
            },
            "response": "Résultat de la requête"
        },
        "POST /api/logic/generate-queries": {
            "description": "Génération de requêtes logiques pertinentes",
            "parameters": {
                "belief_set_id": "string (requis) - ID de l'ensemble de croyances",
                "text": "string (requis) - Texte source",
                "logic_type": "string (requis) - Type de logique",
                "options": "object (optionnel) - Options de génération"
            },
            "response": "Liste des requêtes générées"
        },
        "POST /api/logic/interpret": {
            "description": "Interprétation des résultats de requêtes logiques",
            "parameters": {
                "belief_set_id": "string (requis) - ID de l'ensemble de croyances",
                "logic_type": "string (requis) - Type de logique",
                "text": "string (requis) - Texte source",
                "queries": "array (requis) - Requêtes exécutées",
                "results": "array (requis) - Résultats des requêtes",
                "options": "object (optionnel) - Options d'interprétation"
            },
            "response": "Interprétation des résultats"
        }
    }
    
    return jsonify({
        "api_name": "API d'Analyse Argumentative",
        "version": "1.0.0",
        "endpoints": endpoints
    })


@app.route('/api/logic/belief-set', methods=['POST'])
def create_belief_set():
    """
    Convertit un texte en ensemble de croyances logiques.
    
    Body JSON:
    {
        "text": "Texte à convertir",
        "logic_type": "propositional",
        "options": {
            "include_explanation": true,
            "max_queries": 5
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(
                error="Données manquantes",
                message="Le body JSON est requis",
                status_code=400
            ).dict()), 400
        
        # Validation de la requête
        try:
            belief_set_request = LogicBeliefSetRequest(**data)
        except Exception as e:
            return jsonify(ErrorResponse(
                error="Données invalides",
                message=f"Erreur de validation: {str(e)}",
                status_code=400
            ).dict()), 400
        
        # Conversion du texte en ensemble de croyances
        result = logic_service.text_to_belief_set(belief_set_request)
        
        return jsonify(result.dict())
        
    except Exception as e:
        logger.error(f"Erreur lors de la conversion en ensemble de croyances: {str(e)}")
        return jsonify(ErrorResponse(
            error="Erreur de conversion",
            message=str(e),
            status_code=500
        ).dict()), 500


@app.route('/api/logic/query', methods=['POST'])
def execute_logic_query():
    """
    Exécute une requête logique sur un ensemble de croyances.
    
    Body JSON:
    {
        "belief_set_id": "id-de-l-ensemble-de-croyances",
        "query": "a => b",
        "logic_type": "propositional",
        "options": {
            "include_explanation": true
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(
                error="Données manquantes",
                message="Le body JSON est requis",
                status_code=400
            ).dict()), 400
        
        # Validation de la requête
        try:
            query_request = LogicQueryRequest(**data)
        except Exception as e:
            return jsonify(ErrorResponse(
                error="Données invalides",
                message=f"Erreur de validation: {str(e)}",
                status_code=400
            ).dict()), 400
        
        # Exécution de la requête
        result = logic_service.execute_query(query_request)
        
        return jsonify(result.dict())
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de la requête logique: {str(e)}")
        return jsonify(ErrorResponse(
            error="Erreur d'exécution",
            message=str(e),
            status_code=500
        ).dict()), 500


@app.route('/api/logic/generate-queries', methods=['POST'])
def generate_logic_queries():
    """
    Génère des requêtes logiques pertinentes.
    
    Body JSON:
    {
        "belief_set_id": "id-de-l-ensemble-de-croyances",
        "text": "Texte source",
        "logic_type": "propositional",
        "options": {
            "max_queries": 5
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(
                error="Données manquantes",
                message="Le body JSON est requis",
                status_code=400
            ).dict()), 400
        
        # Validation de la requête
        try:
            generate_request = LogicGenerateQueriesRequest(**data)
        except Exception as e:
            return jsonify(ErrorResponse(
                error="Données invalides",
                message=f"Erreur de validation: {str(e)}",
                status_code=400
            ).dict()), 400
        
        # Génération des requêtes
        result = logic_service.generate_queries(generate_request)
        
        return jsonify(result.dict())
        
    except Exception as e:
        logger.error(f"Erreur lors de la génération de requêtes logiques: {str(e)}")
        return jsonify(ErrorResponse(
            error="Erreur de génération",
            message=str(e),
            status_code=500
        ).dict()), 500


@app.route('/api/logic/interpret', methods=['POST'])
def interpret_logic_results():
    """
    Interprète les résultats de requêtes logiques.
    
    Body JSON:
    {
        "belief_set_id": "id-de-l-ensemble-de-croyances",
        "logic_type": "propositional",
        "text": "Texte source",
        "queries": ["a", "b", "a => b"],
        "results": [
            {
                "query": "a",
                "result": true,
                "formatted_result": "Tweety Result: Query 'a' is ACCEPTED (True)."
            },
            ...
        ],
        "options": {
            "include_explanation": true
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify(ErrorResponse(
                error="Données manquantes",
                message="Le body JSON est requis",
                status_code=400
            ).dict()), 400
        
        # Extraction des données
        try:
            belief_set_id = data.get("belief_set_id")
            logic_type = data.get("logic_type")
            text = data.get("text")
            queries = data.get("queries", [])
            results_data = data.get("results", [])
            options_data = data.get("options", {})
            
            if not belief_set_id or not logic_type or not text or not queries or not results_data:
                return jsonify(ErrorResponse(
                    error="Données manquantes",
                    message="Les champs belief_set_id, logic_type, text, queries et results sont requis",
                    status_code=400
                ).dict()), 400
            
            # Conversion des résultats en objets LogicQueryResult
            results = [LogicQueryResult(**result) for result in results_data]
            
            # Conversion des options en objet LogicOptions
            options = LogicOptions(**options_data) if options_data else None
            
        except Exception as e:
            return jsonify(ErrorResponse(
                error="Données invalides",
                message=f"Erreur de validation: {str(e)}",
                status_code=400
            ).dict()), 400
        
        # Interprétation des résultats
        result = logic_service.interpret_results(
            belief_set_id=belief_set_id,
            logic_type=logic_type,
            text=text,
            queries=queries,
            results=results,
            options=options
        )
        
        return jsonify(result.dict())
        
    except Exception as e:
        logger.error(f"Erreur lors de l'interprétation des résultats logiques: {str(e)}")
        return jsonify(ErrorResponse(
            error="Erreur d'interprétation",
            message=str(e),
            status_code=500
        ).dict()), 500


if __name__ == '__main__':
    # Configuration pour le développement
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    logger.info(f"Démarrage de l'API sur le port {port}")
    logger.info(f"Mode debug: {debug}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
﻿# -*- coding: utf-8 -*-
"""
Tests d'intégration pour l'interaction entre les différents agents.

Ce module contient des tests d'intégration qui vérifient l'interaction
entre les différents agents (PM, PL, Informal, Extract) dans le contexte
de la stratégie d'équilibrage de participation.
"""

import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import semantic_kernel as sk

# Correction de l'importation de AuthorRole suite à la refactorisation de semantic-kernel
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from semantic_kernel.agents import Agent, AgentGroupChat

# Utiliser la fonction setup_import_paths pour résoudre les problèmes d'imports relatifs
# from tests import setup_import_paths # Commenté pour investigation
# setup_import_paths() # Commenté pour investigation

from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentation_analysis.core.strategies import BalancedParticipationStrategy
# from argumentation_analysis.orchestration.analysis_runner import run_analysis_conversation # Commenté, non utilisé dans ce fichier
from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
from argumentation_analysis.agents.core.pl.pl_definitions import setup_pl_kernel
from argumentation_analysis.agents.core.informal.informal_definitions import setup_informal_kernel
from argumentation_analysis.agents.core.pm.pm_definitions import setup_pm_kernel
# from tests.async_test_case import AsyncTestCase # Suppression de l'import


class TestAgentInteraction: # Suppression de l'héritage AsyncTestCase
    """Tests d'intégration pour l'interaction entre les différents agents."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """Initialisation avant chaque test."""
        self.test_text = """
        La Terre est plate car l'horizon semble plat quand on regarde au loin.
        De plus, si la Terre était ronde, les gens à l'autre bout tomberaient.
        Certains scientifiques affirment que la Terre est ronde, mais ils sont payés par la NASA.
        """
        
        self.state = RhetoricalAnalysisState(self.test_text)
        
        self.llm_service = MagicMock()
        self.llm_service.service_id = "test_service"
        
        self.kernel = sk.Kernel()
        
        self.state_manager = StateManagerPlugin(self.state)
        self.kernel.add_plugin(self.state_manager, "StateManager")
        
        self.pm_agent = MagicMock()
        self.pm_agent.name = "ProjectManagerAgent"
        
        self.pl_agent = MagicMock()
        self.pl_agent.name = "PropositionalLogicAgent"
        
        self.informal_agent = MagicMock()
        self.informal_agent.name = "InformalAnalysisAgent"
        
        self.extract_agent = MagicMock()
        self.extract_agent.name = "ExtractAgent"
        
        self.agents = [self.pm_agent, self.pl_agent, self.informal_agent, self.extract_agent]
        
        self.balanced_strategy = BalancedParticipationStrategy(
            agents=self.agents,
            state=self.state,
            default_agent_name="ProjectManagerAgent"
        )

    @pytest.mark.asyncio
    async def test_pm_informal_interaction(self):
        """Vérifie la transition du PM à l'agent Informal."""
        history = []
        
        self.state.add_task("Identifier les arguments dans le texte")
        self.state.designate_next_agent("InformalAnalysisAgent")
        
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        assert selected_agent == self.informal_agent
        
        informal_message = MagicMock(spec=ChatMessageContent)
        informal_message.role = AuthorRole.ASSISTANT
        informal_message.name = "InformalAnalysisAgent"
        informal_message.content = "J'ai identifié les arguments suivants."
        history.append(informal_message)
        
        arg1_id = self.state.add_argument("La Terre est plate car l'horizon semble plat")
        arg2_id = self.state.add_argument("Si la Terre était ronde, les gens tomberaient")
        
        task_id = next(iter(self.state.analysis_tasks))
        
        self.state.add_answer(
            task_id,
            "InformalAnalysisAgent",
            "J'ai identifié 2 arguments dans le texte.",
            [arg1_id, arg2_id]
        )
        
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        assert selected_agent != self.informal_agent
        
        assert len(self.state.analysis_tasks) == 1
        assert len(self.state.identified_arguments) == 2
        assert len(self.state.answers) == 1

    @pytest.mark.asyncio
    async def test_informal_pl_interaction(self):
        """Vérifie la transition de l'agent Informal à l'agent PL."""
        history = []
        
        arg_id = self.state.add_argument("La Terre est plate car l'horizon semble plat")
        
        informal_message = MagicMock(spec=ChatMessageContent)
        informal_message.role = AuthorRole.ASSISTANT
        informal_message.name = "InformalAnalysisAgent"
        informal_message.content = "J'ai identifié un argument."
        history.append(informal_message)
        
        self.state.designate_next_agent("PropositionalLogicAgent")
        
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        assert selected_agent == self.pl_agent
        
        pl_message = MagicMock(spec=ChatMessageContent)
        pl_message.role = AuthorRole.ASSISTANT
        pl_message.name = "PropositionalLogicAgent"
        pl_message.content = "Je vais formaliser cet argument."
        history.append(pl_message)
        
        bs_id = self.state.add_belief_set("Propositional", "p => q\np\n")
        log_id = self.state.log_query(bs_id, "p => q", "ACCEPTED (True)")
        
        assert len(self.state.identified_arguments) == 1
        assert len(self.state.belief_sets) == 1
        assert len(self.state.query_log) == 1

    @pytest.mark.asyncio
    async def test_pl_extract_interaction(self):
        """Vérifie la transition de l'agent PL à l'agent Extract."""
        history = []
        
        bs_id = self.state.add_belief_set("Propositional", "p => q\np\n")
        
        pl_message = MagicMock(spec=ChatMessageContent)
        pl_message.role = AuthorRole.ASSISTANT
        pl_message.name = "PropositionalLogicAgent"
        pl_message.content = "J'ai formalisé l'argument."
        history.append(pl_message)
        
        self.state.designate_next_agent("ExtractAgent")
        
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        assert selected_agent == self.extract_agent
        
        extract_message = MagicMock(spec=ChatMessageContent)
        extract_message.role = AuthorRole.ASSISTANT
        extract_message.name = "ExtractAgent"
        extract_message.content = "Je vais analyser l'extrait du texte."
        history.append(extract_message)
        
        extract_id = self.state.add_extract("Extrait du texte", "La Terre est plate car l'horizon semble plat")
        
        assert len(self.state.belief_sets) == 1
        assert len(self.state.extracts) == 1

    @pytest.mark.asyncio
    async def test_extract_pm_interaction(self):
        """Vérifie la transition de l'agent Extract au PM pour la conclusion."""
        history = []
        
        extract_id = self.state.add_extract("Extrait du texte", "La Terre est plate car l'horizon semble plat")
        
        extract_message = MagicMock(spec=ChatMessageContent)
        extract_message.role = AuthorRole.ASSISTANT
        extract_message.name = "ExtractAgent"
        extract_message.content = "J'ai analysé l'extrait du texte."
        history.append(extract_message)
        
        self.state.designate_next_agent("ProjectManagerAgent")
        
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        assert selected_agent == self.pm_agent
        
        pm_message = MagicMock(spec=ChatMessageContent)
        pm_message.role = AuthorRole.ASSISTANT
        pm_message.name = "ProjectManagerAgent"
        pm_message.content = "Je vais conclure l'analyse."
        history.append(pm_message)
        
        self.state.set_conclusion("Le texte contient plusieurs sophismes qui invalident l'argument principal.")
        
        assert len(self.state.extracts) == 1
        assert self.state.final_conclusion is not None

    @pytest.mark.asyncio
    async def test_full_agent_interaction_cycle(self):
        """Vérifie un cycle complet d'interaction entre tous les agents."""
        history = []
        
        self.state.add_task("Identifier les arguments dans le texte")
        
        pm_message = MagicMock(spec=ChatMessageContent)
        pm_message.role = AuthorRole.ASSISTANT
        pm_message.name = "ProjectManagerAgent"
        pm_message.content = "Je vais définir les tâches d'analyse."
        history.append(pm_message)
        
        self.state.designate_next_agent("InformalAnalysisAgent")
        
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        assert selected_agent == self.informal_agent
        
        arg1_id = self.state.add_argument("La Terre est plate car l'horizon semble plat")
        
        informal_message = MagicMock(spec=ChatMessageContent)
        informal_message.role = AuthorRole.ASSISTANT
        informal_message.name = "InformalAnalysisAgent"
        informal_message.content = "J'ai identifié un argument."
        history.append(informal_message)
        
        self.state.designate_next_agent("PropositionalLogicAgent")
        
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        assert selected_agent == self.pl_agent
        
        bs_id = self.state.add_belief_set("Propositional", "p => q\np\n")
        
        pl_message = MagicMock(spec=ChatMessageContent)
        pl_message.role = AuthorRole.ASSISTANT
        pl_message.name = "PropositionalLogicAgent"
        pl_message.content = "J'ai formalisé l'argument."
        history.append(pl_message)
        
        self.state.designate_next_agent("ExtractAgent")
        
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        assert selected_agent == self.extract_agent
        
        extract_id = self.state.add_extract("Extrait du texte", "La Terre est plate car l'horizon semble plat")
        
        extract_message = MagicMock(spec=ChatMessageContent)
        extract_message.role = AuthorRole.ASSISTANT
        extract_message.name = "ExtractAgent"
        extract_message.content = "J'ai analysé l'extrait du texte."
        history.append(extract_message)
        
        self.state.designate_next_agent("ProjectManagerAgent")
        
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        assert selected_agent == self.pm_agent
        
        self.state.set_conclusion("Le texte contient plusieurs sophismes qui invalident l'argument principal.")
        
        assert len(self.state.analysis_tasks) == 1
        assert len(self.state.identified_arguments) == 1
        assert len(self.state.belief_sets) == 1
        assert len(self.state.extracts) == 1
        assert self.state.final_conclusion is not None
        
        assert self.balanced_strategy._participation_counts["ProjectManagerAgent"] == 1
        assert self.balanced_strategy._participation_counts["InformalAnalysisAgent"] == 1
        assert self.balanced_strategy._participation_counts["PropositionalLogicAgent"] == 1
        assert self.balanced_strategy._participation_counts["ExtractAgent"] == 1
        assert self.balanced_strategy._total_turns == 4


class TestAgentInteractionWithErrors: # Suppression de l'héritage AsyncTestCase
    """Tests d'intégration pour l'interaction entre les agents avec des erreurs."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        self.test_text = """
        La Terre est plate car l'horizon semble plat quand on regarde au loin.
        De plus, si la Terre était ronde, les gens à l'autre bout tomberaient.
        Certains scientifiques affirment que la Terre est ronde, mais ils sont payés par la NASA.
        """
        
        self.state = RhetoricalAnalysisState(self.test_text)
        
        self.llm_service = MagicMock()
        self.llm_service.service_id = "test_service"
        
        self.kernel = sk.Kernel()
        
        self.state_manager = StateManagerPlugin(self.state)
        self.kernel.add_plugin(self.state_manager, "StateManager")
        
        self.pm_agent = MagicMock()
        self.pm_agent.name = "ProjectManagerAgent"
        
        self.pl_agent = MagicMock()
        self.pl_agent.name = "PropositionalLogicAgent"
        
        self.informal_agent = MagicMock()
        self.informal_agent.name = "InformalAnalysisAgent"
        
        self.extract_agent = MagicMock()
        self.extract_agent.name = "ExtractAgent"
        
        self.agents = [self.pm_agent, self.pl_agent, self.informal_agent, self.extract_agent]
        
        self.balanced_strategy = BalancedParticipationStrategy(
            agents=self.agents,
            state=self.state,
            default_agent_name="ProjectManagerAgent"
        )

    @pytest.mark.asyncio
    async def test_error_recovery_interaction(self):
        """Teste la capacité du PM à gérer une erreur d'un autre agent."""
        history = []
        
        self.state.add_task("Identifier les arguments dans le texte")
        
        pm_message = MagicMock(spec=ChatMessageContent)
        pm_message.role = AuthorRole.ASSISTANT
        pm_message.name = "ProjectManagerAgent"
        pm_message.content = "Je vais définir les tâches d'analyse."
        history.append(pm_message)
        
        self.state.designate_next_agent("InformalAnalysisAgent")
        
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        assert selected_agent == self.informal_agent
        
        self.state.log_error("InformalAnalysisAgent", "Erreur lors de l'identification des arguments")
        
        informal_error_message = MagicMock(spec=ChatMessageContent)
        informal_error_message.role = AuthorRole.ASSISTANT
        informal_error_message.name = "InformalAnalysisAgent"
        informal_error_message.content = "Je rencontre une difficulté pour identifier les arguments."
        history.append(informal_error_message)
        
        self.state.designate_next_agent("ProjectManagerAgent")
        
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        assert selected_agent == self.pm_agent
        
        self.state.add_task("Analyser directement les sophismes potentiels")
        
        pm_recovery_message = MagicMock(spec=ChatMessageContent)
        pm_recovery_message.role = AuthorRole.ASSISTANT
        pm_recovery_message.name = "ProjectManagerAgent"
        pm_recovery_message.content = "Je vais gérer cette erreur et rediriger l'analyse."
        history.append(pm_recovery_message)
        
        self.state.designate_next_agent("PropositionalLogicAgent")
        
        selected_agent = await self.balanced_strategy.next(self.agents, history)
        assert selected_agent == self.pl_agent
        
        pl_message = MagicMock(spec=ChatMessageContent)
        pl_message.role = AuthorRole.ASSISTANT
        pl_message.name = "PropositionalLogicAgent"
        pl_message.content = "Je vais formaliser les arguments potentiels."
        history.append(pl_message)
        
        assert len(self.state.analysis_tasks) == 2
        assert len(self.state.errors) == 1
        assert self.state.errors[0]["agent_name"] == "InformalAnalysisAgent"
        assert self.state.errors[0]["message"] == "Erreur lors de l'identification des arguments"
        
        assert self.balanced_strategy._participation_counts["ProjectManagerAgent"] == 1
        assert self.balanced_strategy._participation_counts["InformalAnalysisAgent"] == 1
        assert self.balanced_strategy._participation_counts["PropositionalLogicAgent"] == 1
        assert self.balanced_strategy._total_turns == 3


if __name__ == '__main__':
    # Utiliser pytest pour exécuter les tests si ce fichier est exécuté directement
    # Cela permet de bénéficier des fixtures et des plugins pytest comme anyio.
    pytest.main(['-xvs', __file__])



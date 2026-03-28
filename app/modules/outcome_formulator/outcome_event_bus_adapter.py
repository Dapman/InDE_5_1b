"""
Outcome Event Bus Adapter

InDE MVP v4.6.0 - The Outcome Engine

Lightweight adapter that registers the OutcomeFormulatorEngine as a subscriber
on the InDE event bus. No business logic - routing only.

Called at application startup (app/main.py or equivalent).
"""

import logging

logger = logging.getLogger(__name__)


class OutcomeEventBusAdapter:
    """
    Registers the Outcome Formulator Engine on the event bus at startup.
    """

    def __init__(self, outcome_formulator_engine):
        self.engine = outcome_formulator_engine

    def register(self) -> None:
        """
        Call this at application startup, after all services are initialized.
        The engine registers its own subscriptions via initialize().
        """
        self.engine.initialize()
        logger.info("OutcomeEventBusAdapter: Outcome Formulator Engine registered.")

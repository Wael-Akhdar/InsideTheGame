"""Match feeds: anything that can stream events in the GamePulse event contract (see docs/EVENT_CONTRACT.md)."""
from .contract import ContractError, Feed, validate_event, validate_stream
from .simulator_feed import SimulatorFeed

__all__ = ["ContractError", "Feed", "SimulatorFeed", "validate_event", "validate_stream"]

import pytest

from alert_engine.lifecycle import InvalidLifecycleTransition, can_transition, transition
from alert_engine.models import AlertState


def test_valid_transition_new_to_acknowledged():
    result = transition(AlertState.NEW, AlertState.ACKNOWLEDGED)
    assert result == AlertState.ACKNOWLEDGED


def test_valid_transition_investigating_to_escalated():
    assert can_transition(AlertState.INVESTIGATING, AlertState.ESCALATED) is True


def test_invalid_transition_closed_to_new_raises():
    with pytest.raises(InvalidLifecycleTransition):
        transition(AlertState.CLOSED, AlertState.NEW)


def test_same_state_transition_is_noop():
    assert transition(AlertState.ACKNOWLEDGED, AlertState.ACKNOWLEDGED) == AlertState.ACKNOWLEDGED


def test_dismissed_can_only_reach_closed():
    assert can_transition(AlertState.DISMISSED, AlertState.CLOSED) is True
    assert can_transition(AlertState.DISMISSED, AlertState.INVESTIGATING) is False

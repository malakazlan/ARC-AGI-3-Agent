"""Dials: a repeated action on the same thing cycles a property with period k. Learn k, cap presses."""
from __future__ import annotations

from arc3.world_model import DialModel


def test_cycle_of_four_states_is_a_dial_with_k_4():
    d = DialModel()
    cls = (5,)
    for src, dst in (("s1", "s2"), ("s2", "s3"), ("s3", "s4"), ("s4", "s1")):
        d.note(cls, src, dst)
    assert d.period(cls) == 4


def test_no_op_and_non_returning_chains_are_not_dials():
    d = DialModel()
    d.note((5,), "s1", "s1")                       # a no-op is not a dial
    assert d.period((5,)) is None
    for src, dst in (("a", "b"), ("b", "c"), ("c", "d"), ("d", "e")):
        d.note((7,), src, dst)
    assert d.period((7,)) is None


def test_chain_restarts_when_the_source_is_not_the_last_destination():
    d = DialModel()
    d.note((5,), "s1", "s2")
    d.note((5,), "x1", "x2")                        # pressed somewhere else: new chain
    d.note((5,), "x2", "x1")
    assert d.period((5,)) == 2


def test_period_is_confirmed_by_a_second_cycle_before_capping_hard():
    d = DialModel()
    cls = (6, 4, "1x1:1", 1)
    for src, dst in (("s1", "s2"), ("s2", "s1")):
        d.note(cls, src, dst)
    assert d.period(cls) == 2
    assert d.confirmed(cls) is False
    for src, dst in (("s1", "s2"), ("s2", "s1")):
        d.note(cls, src, dst)
    assert d.confirmed(cls) is True

"""Dials: an action class that, repeated on the same thing, cycles a property with period k.

Detected from executed transitions: pressing the class from s1 gives s2, from s2 gives s3, ...
and after k presses we are back at s1. Once the period is known (and confirmed by a second
cycle), the explorer has nothing left to learn from pressing it in new states: it caps presses
instead of rotating four times at every position (cn04, re86).
"""
from __future__ import annotations

from dataclasses import dataclass, field

MAX_PERIOD = 8


@dataclass
class Chain:
    start: str
    last: str
    length: int


@dataclass
class DialModel:
    chains: dict[tuple, Chain] = field(default_factory=dict)
    periods: dict[tuple, int] = field(default_factory=dict)
    cycles: dict[tuple, int] = field(default_factory=dict)

    def note(self, cls: tuple, src_key: str, dst_key: str | None) -> None:
        """One executed press of `cls` taking the state from src to dst."""
        if dst_key is None or dst_key == src_key:
            self.chains.pop(cls, None)
            return
        chain = self.chains.get(cls)
        if chain is None or chain.last != src_key or chain.length >= MAX_PERIOD:
            chain = Chain(start=src_key, last=src_key, length=0)
            self.chains[cls] = chain
        chain.length += 1
        chain.last = dst_key
        if dst_key == chain.start:
            period = chain.length
            if self.periods.get(cls) == period:
                self.cycles[cls] = self.cycles.get(cls, 1) + 1
            else:
                self.periods[cls] = period
                self.cycles[cls] = 1
            self.chains[cls] = Chain(start=dst_key, last=dst_key, length=0)

    def period(self, cls: tuple) -> int | None:
        return self.periods.get(cls)

    def confirmed(self, cls: tuple) -> bool:
        return self.cycles.get(cls, 0) >= 2

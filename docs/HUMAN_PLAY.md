# Human play notes

First-contact notes by the owner on public games. Kept verbatim-ish; the general lessons go to
`docs/INSIGHTS.md`. These are our "what a human sees that the agent misses" data.

## ls20 (played L1 to L5, 2026-09-18)

- Avatar: orange/blue block, A1 to A4 move it, each step drains the energy bar; empty = death.
- Objects: `+` = rotator (a dial over orientation). Rainbow box = colour dial, vanishes when
  used. White bars = conveyors, jump N cells, no energy cost. Yellow = refill.
- Panels: bottom-left = current avatar shape/colour (changeable). Top box = target (static).
- Win: panels equal on all properties, then step on the exit.
- L1 discovery: no clue; touched `+`, the panel changed; noticed the panel resembles the target
  box; hypothesis "make them equal"; rotated to match; exit. Failures happen when the
  hypothesis is wrong; fallback is a rotate / try-exit loop.
- L2+: same rule plus one new mechanic per level (colour, conveyors, two rotators). Zero
  actions on known rules; about 2 actions per new mechanic; the rest is navigation.
- L4: conveyor guess wrong once, corrected and re-planned. Dial needed 2 touches.
- L5: planned before moving: goal, known tools, delta (2 rotators), order dial -> rotator ->
  exit, energy check.

# Pebble Interpreter

Implement a correct interpreter for "Pebble" — a small imperative language with first-class functions and dual closure capture semantics.

## Overview
The agent must build an interpreter that handles two closure capture modes: plain `fn` closures capture mutable variables by snapshot (frozen value at creation time), while `&fn` closures capture by reference (shared mutable cell). Nested closures with mixed modes create non-obvious interactions.

## Environment
- Python 3.13 container with 20 test programs at `/app/programs/*.pbl`
- Agent produces `/app/pebble` (executable interpreter)
- 600s timeout

## Verification
The verifier runs all 20 programs through the interpreter and compares stdout to expected outputs (exact string match). Programs cover basic operations, snapshot capture, reference capture, and mixed-mode interactions.

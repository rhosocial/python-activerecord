# src/rhosocial/activerecord/backend/suggestion/__init__.py
"""Backend suggestions.

The two halves live in sibling packages:

* ``backend.suggestion.protocols`` -- the ``*SuggestionSupport`` interfaces
  (core declares only these; concrete backends implement them).
* ``backend.suggestion.definitions`` -- one frozen dataclass per ``suggest_*``
  method, describing the shape of a backend's answer.

A suggestion is a complete decision returned as a value. There is no renderer
layer here: consumers read the value's fields directly (see
``base.derivation`` for partition / auto-increment consumers).
"""
from .definitions import *  # noqa: F401,F403

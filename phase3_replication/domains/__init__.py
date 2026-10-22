"""Domain resources, keyed by the `domain` a suite declares."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from errors import ConfigurationError


@dataclass(frozen=True)
class Domain:
    name: str
    handles: dict[str, Callable[[], Any]]   # runtime variable name -> value loader
    functions: dict[str, Callable]          # tool name -> function
    required_settings: tuple[str, ...] = ()  # settings fields a live run needs


def _hk() -> Domain:
    from domains import hk

    return Domain("hk", hk.HANDLES, hk.FUNCTIONS, ("hk_database_url",))


def _beijing() -> Domain:
    from domains import beijing

    return Domain("beijing", beijing.HANDLES, beijing.FUNCTIONS)


# Factories, so a domain's heavy imports happen only when it is used.
_REGISTRY: dict[str, Callable[[], Domain]] = {"hk": _hk, "beijing": _beijing}


def register_domain(name: str, factory: Callable[[], Domain]) -> None:
    """Add a domain (tests register an offline one)."""
    _REGISTRY[name] = factory


def get_domain(name: str) -> Domain:
    if name not in _REGISTRY:
        raise ConfigurationError(f"unknown domain {name!r}; known: {sorted(_REGISTRY)}")
    return _REGISTRY[name]()

"""Local development settings."""

from .base import *  # noqa: F403


DEBUG = env_bool("DEBUG", True)  # noqa: F405
OFFLINE_KNOWLEDGE_ENABLED = env_bool("OFFLINE_KNOWLEDGE_ENABLED", True)  # noqa: F405

"""
Shared state module for active calls and pending configurations.
This module is used to share state between main.py and API routes.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from call_handler import CallHandler

# Active calls dictionary - shared across all modules
active_calls: dict[str, "CallHandler"] = {}

# Pending call configurations (prompt configs for calls initiated via API)
pending_call_configs: dict[str, dict] = {}

# Pending call numbers (phone numbers for calls initiated via API)
pending_call_numbers: dict[str, str] = {}

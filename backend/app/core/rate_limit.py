"""Shared rate limiter. Applied to the endpoints an attacker would target."""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Tight limits on credential endpoints, looser on everything else.
LOGIN_LIMIT = "10/minute"
REGISTER_LIMIT = "5/hour"
# Browsers refresh every 15 minutes per tab; this only stops scripted hammering.
REFRESH_LIMIT = "30/minute"
EXPORT_LIMIT = "5/minute"

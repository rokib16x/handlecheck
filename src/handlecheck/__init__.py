"""handlecheck: login-free username lookups for seven social platforms."""
from .checkers import CHECKERS, Result, Status, check, check_all, validate_username

__all__ = ["CHECKERS", "Result", "Status", "check", "check_all", "validate_username"]
__version__ = "0.2.0"

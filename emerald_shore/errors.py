"""Stable error types for agent callers."""


class EmeraldError(Exception):
    def __init__(self, code, message, recovery, details=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.recovery = recovery
        self.details = details or {}

    def as_dict(self):
        return {
            "ok": False,
            "code": self.code,
            "message": self.message,
            "recovery": self.recovery,
            "details": self.details,
        }

class AdapterError(Exception):
    def __init__(self, message: str, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


class GoogleAuthError401(AdapterError):
    """raised by the gmail adapter when the failure-drill flag is on, before any real request goes out"""

    def __init__(self):
        super().__init__("gmail auth failed (401) — demo failure mode is on", retryable=True)

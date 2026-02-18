
class CustomAPIException(Exception):

    def __init__(self, message, error_code=500) -> None:
        super().__init__(message)
        self.message = message
        self.error_code= error_code

    def __str__(self) -> str:
        return f"{self.message} (Error code {self.error_code})"

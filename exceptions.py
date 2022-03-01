class ErrorCity(Exception):
    """Base class for all Custom Exceptions"""


class BrokenRequest(ErrorCity):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'{self.message}'

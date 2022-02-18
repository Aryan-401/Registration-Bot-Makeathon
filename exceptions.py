
class ErrorCity(Exception):
    """Base class for all Custom Exceptions"""


class DuplicateInDatabaseError(ErrorCity):
    def __init__(self, message='The Following Team name is already taken, Please input your own team name and try again'):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message


class BrokenRequest(ErrorCity):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f'{self.message} '


class NotInDataBaseError(ErrorCity):
    def __init__(self, message='Entry not found in database, Please try entering correct values or contact a Database Admin'):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message

class TooManyMembers(ErrorCity):
    def __init__(self, message='You can only have a maximum of 5 members (including leader) in a team. Please try again later'):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message

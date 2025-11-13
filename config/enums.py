from enum import Enum

class ViewAction(str, Enum):
    CREATE = 'create'
    UPDATE = 'update'
    PARTIAL_UPDATE = 'partial_update'
    DESTROY = 'destroy'
    PROCESS = 'process'
    COMPLETE = 'complete'
    CANCEL = 'cancel'
    LIST = 'list'
    REGISTER = 'register'
'''
Created on Sep 19, 2020

@author: esdev
'''

class SlacmException(Exception):
    '''
    Base class for all SLAcM expressions 
    '''
    def __init__(self, message):
        super().__init__(message)
        
        
class NotYetImplemented(SlacmException):
    def __init__(self, message):
        super().__init__(message)
        
class LoadError(SlacmException):
    def __init__(self, message):
        super().__init__(message)
        
class PeerOperationError(SlacmException):
    def __init__(self, message):
        super().__init__(message)
        
class PortOperationError(SlacmException):
    def __init__(self, message):
        super().__init__(message)

class UndefinedOperation(SlacmException):
    def __init__(self, message):
        super().__init__(message)
        
class InvalidOperation(SlacmException):
    def __init__(self, message):
        super().__init__(message)

class UndefinedHandler(SlacmException):
    def __init__(self, message):
        super().__init__(message)
        
class ParameterLoadError(SlacmException):
    def __init__(self, message):
        super().__init__(message)
        
class BuildError(SlacmException):
    def __init__(self, message):
        super().__init__(message)
        
        
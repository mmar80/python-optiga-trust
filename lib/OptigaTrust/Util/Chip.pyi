from ctypes import CDLL
from OptigaTrust.Util.Defines import UID

def init() -> CDLL: ...
	
def deinit() -> None: ...
	
def fwversion() -> None: ...
	
def uid() -> UID: ...
from hashlib import md5
from secrets import token_hex

import hashlib

class Crypto:
    @staticmethod
    def encryptPassword(password):
        hash = hashlib.md5(password.encode('utf-8')).hexdigest()
        swappedHash = hash[16:32] + hash[0:16]
        
        return swappedHash
        
    @staticmethod
    def get_login_hash(password, rndk):
        key = Crypto.encryptPassword(password).upper()
        key += rndk
        key += 'Y(02.>\'H}t":E1'
        hash = Crypto.encryptPassword(key)
        return hash
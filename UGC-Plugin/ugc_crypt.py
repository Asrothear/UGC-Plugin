import os
import uuid
import hashlib
import subprocess
from datetime import datetime
from hashlib import blake2b
from hmac import compare_digest

class ugc_crypt(object):
    def sign(self, cmdr, hwID = None):
        h = blake2b(digest_size=16, key=self.muuid(cmdr) )
        h.update(self.muuid(cmdr, hwID))
        return h.hexdigest()
    def verify(self, cmdr, sig):
        return compare_digest(cmdr, sig)
    def muuid(self, cmdr, hwID = None):
        if not hwID:
            hwID = self.ghwid()
        _uuid = uuid.uuid5(uuid.NAMESPACE_OID, cmdr + hwID)
        return _uuid.bytes
    def ghwid(self):
        hwID = str(uuid.UUID(int=uuid.getnode()).hex)
        return hwID
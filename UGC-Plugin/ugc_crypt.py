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
        if 'nt' in os.name:
            hwID = str(subprocess.check_output('wmic csproduct get uuid'), 'utf-8').split('\n')[1].strip()
        else:
            hwID = str("HwID-for-Mac-an-Linux-Systems-(WIP)")
        return hwID
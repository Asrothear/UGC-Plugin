import os
import uuid
import hashlib
import subprocess
from datetime import datetime
from hashlib import blake2b
from hmac import compare_digest

def sign(cmdr):
    if 'nt' in os.name:
        hwID = str(subprocess.check_output('wmic csproduct get uuid'), 'utf-8').split('\n')[1].strip()
    else:
        hwID = str(subprocess.Popen('hal-get-property --udi /org/freedesktop/Hal/devices/computer --key system.hardware.uuid'.split()))
    uuid = uuid.uuid5(uuid.NAMESPACE_OID, cmdr + hwID)
    salt = bytes(datetime.utcnow().isoformat(" "), "utf-8")
    h = blake2b(digest_size=16, key=salt )
    h.update(cookie)
    return h.hexdigest().encode('utf-8')
def verify(cookie, sig):
    good_sig = sign(cookie)
    return compare_digest(good_sig, sig)
import hashlib, json, ecdsa

def hash1(item):
    return hashlib.sha256(item.encode()).hexdigest()

def hash1_dic(dic):
    return hash1(json.dumps(dic))

def hash2(item):
    interm = hashlib.sha256(item.encode()).digest()
    return hashlib.sha256(interm).hexdigest()

def hash2_dic(dic):
    return hash2(json.dumps(dic))

def verify_sig(sig, msg, pubkey):
    ecdsa_pubkey = ecdsa.VerifyingKey.from_string(bytes.fromhex(pubkey))
    return ecdsa_pubkey.verify(bytes.fromhex(sig), msg.encode())

def sign(msg, privkey):
    ecdsa_privkey = ecdsa.SigningKey.from_string(bytes.fromhex(privkey))
    return ecdsa_privkey.sign(msg.encode()).hex()

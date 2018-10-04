"""Custom algorithm helper declaration file"""
import hashlib
import json
import ecdsa

HASH_LEN = 64
NONCE_LEN = 64
SIG_LEN = 96
KEY_LEN = 96


def hash1(item):
    """Hash the encoded item once using SHA256"""
    return hashlib.sha256(item.encode()).hexdigest()


def hash1_dic(dic):
    """Hash the JSON of dictionary once using SHA256"""
    return hash1(json.dumps(dic))


def hash2(item):
    """Hash the encoded item twice using SHA256"""
    interm = hashlib.sha256(item.encode()).digest()
    return hashlib.sha256(interm).hexdigest()


def hash2_dic(dic):
    """Hash the JSON of dictionary twice using SHA256"""
    return hash2(json.dumps(dic))


def verify_sig(sig, msg, pubkey):
    """Verify the signature with public key, using default ECDSA"""
    ecdsa_pubkey = ecdsa.VerifyingKey.from_string(bytes.fromhex(pubkey))
    return ecdsa_pubkey.verify(bytes.fromhex(sig), msg.encode())


def sign(msg, privkey):
    """Sign the encoded message with private key, using default ECDSA"""
    ecdsa_privkey = ecdsa.SigningKey.from_string(bytes.fromhex(privkey))
    return ecdsa_privkey.sign(msg.encode()).hex()

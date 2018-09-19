import hashlib

string = b"Blockchain Technology"

# Using hashlib for SHA hashing
print("SHA256: " + hashlib.sha256(string).hexdigest())
print("SHA512: " + hashlib.sha512(string).hexdigest())
print("SHA3_256: " + hashlib.sha3_256(string).hexdigest())
print("SHA3_512: " + hashlib.sha3_512(string).hexdigest())

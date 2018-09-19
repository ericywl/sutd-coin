import ecdsa

msg = b"Blockchain Technology"
# Generate signing key
sk = ecdsa.SigningKey.generate()
# Compute verifying key using default curve
vk = sk.get_verifying_key()
# Sign message
signature = sk.sign(msg)
# Verify signature
if vk.verify(signature, msg):
    print("Success")
else:
    print("Failure")

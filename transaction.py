import ecdsa, json, datetime, os

class Transaction:
    SIG_LEN = 96
    KEY_LEN = 96
    NONCE_LEN = 64

    def __init__(self, sender, receiver, amount, comment="", timestamp=None,
                 nonce=None, signature=None):
        self._sender = sender
        self._receiver = receiver
        self._amount = amount
        self._comment = comment
        self._timestamp = datetime.datetime.utcnow().timestamp() if \
            timestamp == None else timestamp
        self._nonce = os.urandom(32).hex() if nonce == None else nonce
        self._signature = signature

    @classmethod
    def new(cls, sender, receiver, amount, privkey, comment=""):
        # Instantiates object from passed values
        sender_str = sender.to_string().hex()
        receiver_str = receiver.to_string().hex()
        trans = cls(sender_str, receiver_str, amount, comment)
        trans.sign(privkey)
        if trans.validate():
            return trans

    def to_json(self):
        # Serializes object to JSON string
        return json.dumps({
            "sender": self._sender,
            "receiver": self._receiver,
            "amount": self._amount,
            "comment": self._comment,
            "timestamp": self._timestamp,
            "nonce": self._nonce,
            "signature": self._signature
        })

    @classmethod
    def from_json(cls, json_str):
        # Instantiates/Deserializes object from JSON string
        obj = json.loads(json_str)
        fields = [
            "sender", "receiver", "amount", "comment",
            "timestamp", "nonce", "signature"
        ]
        for f in fields:
            if not obj[f]:
                raise Exception("JSON string is invalid.")
        trans = cls(
            obj["sender"], obj["receiver"], obj["amount"], obj["comment"],
            obj["timestamp"], obj["nonce"], obj["signature"]
        )
        if trans.validate():
            return trans

    def sign(self, privkey):
        # Sign object with private key passed
        # That can be called within new()
        self._signature = privkey.sign(self.to_json().encode()).hex()

    def verify(self):
        # Verify signature
        # Remove signature before verifying
        sig = self._signature
        self._signature = None
        sender_key = ecdsa.VerifyingKey.from_string(bytes.fromhex(self._sender))
        res = sender_key.verify(bytes.fromhex(sig), self.to_json().encode())
        self._signature = sig
        return res

    def validate(self):
        # Validate transaction correctness.
        # Can be called within from_json()
        ## Validate sender public key
        if type(self._sender) != str:
            raise Exception("Sender public key not string.")
        if len(self._sender) != Transaction.KEY_LEN:
            raise Exception("Sender public key length invalid.")
        ## Validate receiver public key
        if type(self._receiver) != str:
            raise Exception("Receiver public key not string.")
        if len(self._receiver) != Transaction.KEY_LEN:
            raise Exception("Receiver public key length invalid.")
        ## Check transaction amount > 0
        if self._amount <= 0:
            raise Exception("Invalid transaction amount.")
        ## Validate signature
        if type(self._signature) != str:
            raise Exception("Signature not string.")
        if len(self._signature) != Transaction.SIG_LEN:
            raise Exception("Signature length invalid.")
        ## Validate nonce
        if type(self._nonce) != str:
            raise Exception("Nonce not string.")
        if len(self._nonce) != Transaction.NONCE_LEN:
            raise Exception("Nonce length invalid.")
        ## Validate timestamp
        if self._timestamp <= 0:
            raise Exception("Invalid timestamp.")
        return True

    def __str__(self):
        # String method for printing
        string = "Transaction Information\n"
        string += "============================\n"
        string += "Sender: {}\n".format(self._sender)
        string += "Receiver: {}\n".format(self._receiver)
        string += "Amount: {}\n".format(self._amount)
        dt_obj = datetime.datetime.fromtimestamp(self._timestamp)
        string += "Timestamp: {} UTC\n".format(dt_obj)
        temp_comment = "N/A" if self._comment == "" else self._comment
        string += "Comment: {}\n".format(temp_comment)
        string += "Nonce: {}\n".format(self._nonce)
        temp_sig = "N/A" if self._signature == None else self._signature
        string += "Signature: {}".format(temp_sig)
        return string

    def __eq__(self, other):
        # Check whether transactions are the same
        j1 = self.to_json()
        j2 = other.to_json()
        return j1 == j2

    @property
    def sender(self):
        return self._sender

    @property
    def receiver(self):
        return self._receiver

    @property
    def amount(self):
        return self._amount

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def comment(self):
        return self._comment

    @property
    def signature(self):
        return self._signature

    @property
    def nonce(self):
        return self._nonce


if __name__ == "__main__":
    sender_sk = ecdsa.SigningKey.generate()
    sender_vk = sender_sk.get_verifying_key()
    receiver_sk = ecdsa.SigningKey.generate()
    receiver_vk = receiver_sk.get_verifying_key()
    t = Transaction.new(sender_vk, receiver_vk, 1, sender_sk, "hello world")
    t2 = Transaction.from_json(t.to_json())
    print(t)
    assert t2.verify()
    assert t == t2

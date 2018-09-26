import ecdsa, json, datetime, os

class Transaction:
    def __init__(self, sender, receiver, amount, comment=""):
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.comment = comment
        self.timestamp = datetime.datetime.utcnow().timestamp()
        self.nonce = os.urandom(32).hex()
        self.signature = None

    @classmethod
    def new(cls, sender, receiver, amount, privkey, comment=""):
        # Instantiates object from passed values
        sender = sender.to_string().hex()
        receiver = receiver.to_string().hex()
        trans = cls(sender, receiver, amount, comment)
        trans.sign(privkey)
        if not trans.validate():
            raise Exception("Invalid new Transaction parameters.")
        else:
            return trans

    def to_json(self):
        # Serializes object to JSON string
        return json.dumps({
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "comment": self.comment,
            "timestamp": self.timestamp,
            "signature": self.signature
        })

    @classmethod
    def from_json(cls, json_str):
        # Instantiates/Deserializes object from JSON string
        obj = json.loads(json_str)
        trans = cls(
            obj["sender"],
            obj["receiver"],
            obj["amount"],
            obj["comment"]
        )
        trans.timestamp = obj["timestamp"]
        trans.signature = obj["signature"]
        if not trans.validate():
            raise Exception("JSON string is invalid.")
        else:
            return trans

    def sign(self, privkey):
        # Sign object with private key passed
        # That can be called within new()
        self.signature = privkey.sign(self.to_json().encode()).hex()

    def verify(self):
        # Verify signature
        # Remove signature before verifying
        sig = self.signature
        self.signature = None
        sender_key = ecdsa.VerifyingKey.from_string(bytes.fromhex(self.sender))
        res = sender_key.verify(bytes.fromhex(sig), self.to_json().encode())
        self.signature = sig
        return res

    def validate(self):
        # Validate transaction correctness.
        # Can be called within from_json()
        ## Validate sender public key
        if type(self.sender) != str:
            return False
        if len(self.sender) != 96:
            return False
        ## Validate receiver public key
        if type(self.receiver) != str:
            return False
        if len(self.receiver) != 96:
            return False
        ## Check transaction amount > 0
        if self.amount <= 0:
            return False
        ## Validate signature
        if type(self.signature) != str:
            return False
        return len(self.signature) == 96

    def __str__(self):
        # String method for printing
        string = "Transaction Information\n"
        string += "============================\n"
        string += "Sender: {}\n".format(self.sender)
        string += "Receiver: {}\n".format(self.receiver)
        string += "Amount: {}\n".format(self.amount)
        dt_obj = datetime.datetime.fromtimestamp(self.timestamp)
        string += "Timestamp: {} UTC\n".format(dt_obj)
        temp_comment = "N/A" if self.comment == "" else self.comment
        string += "Comment: {}\n".format(temp_comment)
        temp_sig = "N/A" if self.signature == None else self.signature
        string += "Signature: {}".format(temp_sig)
        return string

    def __eq__(self, other):
        # Check whether transactions are the same
        j1 = self.to_json()
        j2 = other.to_json()
        return j1 == j2


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

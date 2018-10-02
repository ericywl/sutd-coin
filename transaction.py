import algo
import ecdsa
import json
import datetime
import os


class Transaction:
    def __init__(self, sender, receiver, amount, nonce,
                 comment="", signature=None):
        self._sender = sender
        self._receiver = receiver
        self._amount = amount
        self._comment = comment
        self._nonce = nonce
        self._signature = signature

    # Instantiates object from passed values
    @classmethod
    def new(cls, sender, receiver, amount, privkey, nonce, comment=""):
        sender_str = sender
        receiver_str = receiver
        trans = cls(sender_str, receiver_str, amount, nonce, comment)
        trans.sign(privkey)
        if trans.validate():
            return trans

    # Serializes object to JSON string
    def to_json(self):
        return json.dumps({
            "sender": self._sender,
            "receiver": self._receiver,
            "amount": self._amount,
            "comment": self._comment,
            "nonce": self._nonce,
            "signature": self._signature
        })

    # Instantiates/Deserializes object from JSON string
    @classmethod
    def from_json(cls, json_str):
        obj = json.loads(json_str)
        fields = [
            "sender", "receiver", "amount", "comment",
            "nonce", "signature"
        ]
        if not all(elem in obj.keys() for elem in fields):
            raise Exception("Transaction JSON string is invalid.")
        trans = cls(
            sender=obj["sender"],
            receiver=obj["receiver"],
            amount=obj["amount"],
            nonce=obj["nonce"],
            comment=obj["comment"],
            signature=obj["signature"]
        )
        if trans.validate():
            return trans

    # Validate transaction correctness.
    def validate(self):
        # Can be called within from_json()
        # Validate sender public key
        if type(self._sender) != str:
            raise Exception("Sender public key not string.")
        if len(self._sender) != algo.KEY_LEN:
            raise Exception("Sender public key length is invalid.")
        # Validate receiver public key
        if type(self._receiver) != str:
            raise Exception("Receiver public key not string.")
        if len(self._receiver) != algo.KEY_LEN:
            raise Exception("Receiver public key length is invalid.")
        # Check transaction amount > 0
        if type(self._amount) != int:
            raise Exception("Transaction amount not integer.")
        if self._amount <= 0:
            raise Exception("Invalid transaction amount.")
        # Validate signature
        if type(self._signature) != str:
            raise Exception("Transaction signature not string.")
        if len(self._signature) != algo.SIG_LEN:
            raise Exception("Transaction signature length is invalid.")
        # Validate nonce
        if type(self._nonce) != int:
            raise Exception("Transaction nonce not integer.")
        if self._nonce < 0:
            raise Exception("Transaction nonce cannot be negative.")
        return True

    # Sign object with private key passed
    def sign(self, privkey):
        # Can be called within new()
        self._signature = algo.sign(self.to_json(), privkey)

    # Verify signature
    def verify(self):
        # Remove signature before verifying
        sig = self._signature
        self._signature = None
        res = algo.verify_sig(sig, self.to_json(), self._sender)
        self._signature = sig
        return res

    # String method for printing
    def __str__(self):
        string = "Transaction Information\n"
        string += "============================\n"
        string += "Sender: {}\n".format(self._sender)
        string += "Receiver: {}\n".format(self._receiver)
        string += "Amount: {}\n".format(self._amount)
        temp_comment = "N/A" if self._comment == "" else self._comment
        string += "Comment: {}\n".format(temp_comment)
        string += "Nonce: {}\n".format(self._nonce)
        temp_sig = "N/A" if self._signature == None else self._signature
        string += "Signature: {}".format(temp_sig)
        return string

    # Check whether transactions are the same
    def __eq__(self, other):
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
    sender_privkey = sender_sk.to_string().hex()
    sender_pubkey = sender_sk.get_verifying_key().to_string().hex()
    receiver_sk = ecdsa.SigningKey.generate()
    receiver_pubkey = receiver_sk.get_verifying_key().to_string().hex()
    t = Transaction.new(sender_pubkey, receiver_pubkey, 1, sender_privkey,
                        1, "hello world")
    t2 = Transaction.from_json(t.to_json())
    print(t)
    assert t2.verify()
    assert t == t2

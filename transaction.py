"""Transaction class declaration file"""
import json
import os
import ecdsa

import algo


class Transaction:
    """Transaction class"""

    def __init__(self, sender, receiver, amount, nonce, comment="",
                 signature=None):
        self._sender = sender
        self._receiver = receiver
        self._amount = amount
        self._comment = comment
        self._nonce = nonce
        self._signature = signature

    @classmethod
    def new(cls, sender, receiver, amount, privkey, comment=""):
        """Instantiates object from passed values"""
        sender_str = sender
        receiver_str = receiver
        nonce = os.urandom(algo.NONCE_LEN // 2).hex()
        trans = cls(sender_str, receiver_str, amount, nonce, comment)
        trans.sign(privkey)
        if not trans.validate():
            return None
        return trans

    def to_json(self):
        """Serializes object to JSON string"""
        return json.dumps({
            "sender": self._sender,
            "receiver": self._receiver,
            "amount": self._amount,
            "comment": self._comment,
            "nonce": self._nonce,
            "signature": self._signature
        })

    @classmethod
    def from_json(cls, json_str):
        """Instantiates/Deserializes object from JSON string"""
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
        if not trans.validate():
            return None
        return trans

    def validate(self):
        """Validate transaction correctness"""
        # Can be called within from_json()
        # Validate sender public key
        if not isinstance(self._sender, str):
            raise Exception("Sender public key not string.")
        if len(self._sender) != algo.KEY_LEN:
            raise Exception("Sender public key length is invalid.")
        # Validate receiver public key
        if not isinstance(self._receiver, str):
            raise Exception("Receiver public key not string.")
        if len(self._receiver) != algo.KEY_LEN:
            raise Exception("Receiver public key length is invalid.")
        # Check transaction amount > 0
        if not isinstance(self._amount, int):
            raise Exception("Transaction amount not integer.")
        if self._amount <= 0:
            raise Exception("Invalid transaction amount.")
        # Validate signature
        if not isinstance(self._signature, str):
            raise Exception("Transaction signature not string.")
        if len(self._signature) != algo.SIG_LEN:
            raise Exception("Transaction signature length is invalid.")
        # Validate nonce
        if not isinstance(self._nonce, str):
            raise Exception("Transaction nonce not integer.")
        if len(self._nonce) != algo.NONCE_LEN:
            raise Exception("Transaction nonce cannot be negative.")
        return True

    def sign(self, privkey):
        """Sign object with private key passed"""
        # Can be called within new()
        self._signature = algo.sign(self.to_json(), privkey)

    def verify(self):
        """Verify signature"""
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
        temp_sig = "N/A" if self._signature is None else self._signature
        string += "Signature: {}\n".format(temp_sig)
        return string

    # Check whether transactions are the same
    def __eq__(self, other):
        json1 = self.to_json()
        json2 = other.to_json()
        return json1 == json2

    @property
    def sender(self):
        """Sender public key"""
        return self._sender

    @property
    def receiver(self):
        """Receiver public key"""
        return self._receiver

    @property
    def amount(self):
        """Amount in transaction"""
        return self._amount

    @property
    def comment(self):
        """Optional comment"""
        return self._comment

    @property
    def signature(self):
        """Signature to be verified"""
        return self._signature

    @property
    def nonce(self):
        """Randomly generated nonce"""
        return self._nonce


if __name__ == "__main__":
    SENDER_SK = ecdsa.SigningKey.generate()
    SENDER_PRIVKEY = SENDER_SK.to_string().hex()
    SENDER_PUBKEY = SENDER_PRIVKEY.get_verifying_key().to_string().hex()
    RECEIVER_SK = ecdsa.SigningKey.generate()
    RECEIVER_PUBKEY = RECEIVER_SK.get_verifying_key().to_string().hex()
    T1 = Transaction.new(SENDER_PUBKEY, RECEIVER_PUBKEY, 1, SENDER_PRIVKEY,
                         "hello world")
    T2 = Transaction.from_json(T1.to_json())
    print(T1)
    assert T2.verify()
    assert T1 == T2

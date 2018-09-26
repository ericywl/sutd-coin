import ecdsa
from transaction import *
from blockchain import *

class Miner:
    def __init__(self, privkey, pubkey):
        self.privkey = privkey
        self.pubkey = pubkey
        self.blockchain = None
        self.transactions = set()

    @classmethod
    def new(cls):
        privkey = ecdsa.SigningKey.generate()
        pubkey = privkey.get_verifying_key()
        return cls(privkey, pubkey)

    def create_transaction():
        return

    def add_transaction(self, trans_json):
        trans = Transaction.from_json(trans_json)
        if not trans.verify():
            raise Exception("Transaction verification failed.")
        else:
            self.transactions.add(trans_json)

    def create_block():
        return

    def add_block():
        return





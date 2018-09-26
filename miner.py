import ecdsa
from transaction import *
from blockchain import *

class Miner:
    def __init__(self, privkey, pubkey):
        self._privkey = privkey
        self._pubkey = pubkey
        self._blockchain = None
        self._transactions = set()
        self._peers = []

    @classmethod
    def new(cls):
        privkey = ecdsa.SigningKey.generate()
        pubkey = privkey.get_verifying_key()
        return cls(privkey, pubkey)

    def _broadcast_transaction(self, trans_json):
        # assume that peers are all nodes in the network
        # (of course, not practical IRL since its not scalable)
        for p in self._peers:
            p.add_transaction(trans_json)

    def create_transaction(self, receiver, amount, comment):
        trans = Transaction.new(self.pubkey, receiver, amount, comment)
        trans_json = trans.to_json()
        self.add_transaction(trans_json)
        self._broadcast_transaction(trans_json)

    def add_transaction(self, trans_json):
        trans = Transaction.from_json(trans_json)
        if not trans.verify():
            raise Exception("Transaction verification failed.")
        else:
            self.transactions.add(trans_json)

    def create_block(self):
        self.blockchain.resolve()
        added_trans =
        return

    def add_block():
        return





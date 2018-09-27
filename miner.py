from transaction import *
from blockchain import *
from block import *
import algo

import ecdsa, random

class Miner:
    MIN_TRANS = 10
    MAX_TRANS = 100

    def __init__(self, privkey, pubkey):
        self._privkey = privkey
        self._pubkey = pubkey
        self._blockchain = None
        self._transactions = set()
        self._peers = []
        self._sutd_coins = 0
        self._nonce = 0

    @classmethod
    def new(cls):
        privkey = ecdsa.SigningKey.generate()
        pubkey = privkey.get_verifying_key()
        return cls(privkey, pubkey)

    # Broadcast the transaction to the network
    def _broadcast_transaction(self, trans_json):
        # Assume that peers are all nodes in the network
        # (of course, not practical IRL since its not scalable)
        for p in self._peers:
            p.add_transaction(trans_json)

    # Create a new transaction
    def create_transaction(self, receiver, amount, comment):
        sender = self._pubkey
        nonce = self._nonce
        try:
            trans = Transaction.new(sender, receiver, amount, nonce, comment)
        except Exception:
            print("The transaction created is invalid.")
            return None
        trans_json = trans.to_json()
        self.add_transaction(trans_json)
        self._broadcast_transaction(trans_json)
        return trans

    # Add transaction to the pool of transactions
    def add_transaction(self, trans_json):
        trans = Transaction.from_json(trans_json)
        if not trans.verify():
            print("Transaction verification failed.")
            return
        else:
            self._transactions.add(trans_json)

    # Broadcast the block to the network
    def _broadcast_block(self, block_json):
        for p in self._peers:
            p.add_block(block_json)

    # Create a new block
    def create_block(self):
        last_blk = self._blockchain.resolve()
        added_transactions = set(self._blockchain.transactions)
        remaining_transactions = self._transactions - added_transactions
        n_trans = random.randint(Miner.MIN_TRANS, MINER.MAX_TRANS)
        gathered_transactions = random.sample(remaining_transactions, n_trans)
        for t in gathered_transactions:
            if not t.verify():
                print("Set contains invalid transaction.")
                return None
        prev_hash = algo.hash2_dic(last_blk.header)
        try:
            block = Block.new(prev_hash, gathered_transactions)
            self._blockchain.add(block)
            self._sutd_coins += 100
        except Exception:
            print("Invalid block cannot be added to chain.")
        return block

    # Add new block to the blockchain
    def add_block(self, block_json):
        block = Block.from_json(block_json)
        self._blockchain.add(block)






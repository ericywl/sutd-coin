from transaction import *
from blockchain import *
from block import *
import algo

import ecdsa, random

class Miner:
    MAX_TRANS = 100

    def __init__(self, privkey, pubkey):
        self._privkey = privkey
        self._pubkey = pubkey
        self._sutd_coins = 0
        self._pending = 0
        self._nonce = 0
        self._blockchain = Blockchain.new()
        self._transaction_pool = set()
        self._peers = []

    @classmethod
    def new(cls):
        sk = ecdsa.SigningKey.generate()
        vk = sk.get_verifying_key()
        privkey = sk.to_string().hex()
        pubkey = vk.to_string().hex()
        return cls(privkey, pubkey)

    # Broadcast the transaction to the network
    def _broadcast_transaction(self, trans_json):
        # Assume that peers are all nodes in the network
        # (of course, not practical IRL since its not scalable)
        for p in self._peers:
            p.add_transaction(trans_json)

    # Create a new transaction
    def create_transaction(self, receiver_pubkey, amount, comment):
        sender = ecdsa.VerifyingKey.from_string(self._sender)
        receiver = ecdsa.VerifyingKey.from_string(receiver_pubkey)
        nonce = self._nonce
        try:
            if amount > self._sutdcoins:
                raise Exception("Amount is higher than available balance.")
            trans = Transaction.new(sender, receiver, amount, nonce, comment)
        except Exception as e:
            print("TRANS_CREATION_FAIL: {}".format(repr(e)))
            return None
        else:
            self._sutdcoins -= amount
            self._pending += amount
            self._nonce += 1
            trans_json = trans.to_json()
            self.add_transaction(trans_json)
            self._broadcast_transaction(trans_json)
            return trans

    # Add transaction to the pool of transactions
    def add_transaction(self, trans_json):
        if trans_json in self._transaction_pool:
            print("TRANS_ADD_FAIL: Transaction already exist in pool.")
            return
        trans = Transaction.from_json(trans_json)
        try:
            trans.verify()
            self._transaction_pool.add(trans_json)
        except ecdsa.BadSignatureError:
            print("TRANS_VERIFY_FAIL: Transaction verification failed.")

    # Broadcast the block to the network
    def _broadcast_block(self, block_json):
        # Assume that peers are all nodes in the network
        # (of course, not practical IRL since its not scalable)
        for p in self._peers:
            p.add_block(block_json)

    # Create a new block
    def create_block(self):
        # Resolve blockchain to get last block
        last_blk = self._blockchain.resolve()
        # Remove blockchain transactions from pool
        added_transactions = set(self._blockchain.transactions)
        remaining_transactions = self._transaction_pool - added_transactions
        # Get a set of random transactions from pool
        max_n = min(Miner.MAX_TRANS, len(remaining_transactions))
        n_trans = random.randint(1, max_n)
        gathered_transactions = random.sample(remaining_transactions, n_trans)
        # Verify all transactions in set
        for t_json in gathered_transactions:
            t = Transaction.from_json(t_json)
            if not t.verify():
                print("TRANS_VERIFY_FAIL: Set contains invalid transaction.")
                return None
        try:
            prev_hash = algo.hash2_dic(last_blk.header)
            block = Block.new(prev_hash, gathered_transactions)
        except Exception as e:
            print("BLK_CREATION_FAIL: {}".format(repr(e)))
            return None
        else:
            block_json = block.to_json()
            self.add_block(block_json)
            #self._broadcast_block(block_json)
            self._sutd_coins += 100
            return block

    # Recompute miner's balance using transactions in added block
    def _compute_balance(self, transactions):
        for t_json in transactions:
            t = Transaction.from_json(t_json)
            if self._pubkey == t.sender:
                self._pending -= t.amount
            if self._pubkey == t.receiver:
                self._sutd_coins += t.amount

    # Add new block to the blockchain
    def add_block(self, block_json):
        block = Block.from_json(block_json)
        try:
            self._blockchain.add(block)
        except Exception as e:
            print("BLK_ADD_FAIL: {}".format(repr(e)))
        else:
            self._compute_balance(block.transactions)

    # Add miner to peer list
    def add_peer(self, miner):
        self._peers.append(miner)

    @property
    def pubkey(self):
        return self._pubkey

    @property
    def privkey(self):
        return self._privkey

    @property
    def available_balance(self):
        return self._sutd_coins

    @property
    def pending_balance(self):
        return self._pending

    @property
    def total_balance(self):
        return self._sutd_coins + self._pending

    @property
    def blockchain(self):
        return self._blockchain

    @property
    def transaction_pool(self):
        return self._transaction_pool


def create_miner_network(n):
    miners = [Miner.new() for _ in range(n)]
    for m1 in miners:
        for m2 in miners:
            if m1 != m2:
                m1.add_peer(m2)
    return miners

if __name__ == "__main__":
    miners = create_miner_network(5)
    creator_sk = ecdsa.SigningKey.generate()
    creator_privkey = creator_sk.to_string().hex()
    creator_pubkey = creator_sk.get_verifying_key().to_string().hex()
    for i in range(20):
        t = Transaction.new(sender=creator_pubkey, receiver=miners[0].pubkey,
                            amount=10, privkey=creator_privkey,
                            nonce=i, comment="init")
        for m in miners:
            m.add_transaction(t.to_json())
    print("Mining...")
    miners[0].create_block()
    print(miners[0].total_balance)






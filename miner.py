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
        self._balance = 0
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
    def create_transaction(self, receiver, amount, comment):
        try:
            if amount > self._balance:
                raise Exception("Amount is higher than available balance.")
            trans = Transaction.new(sender=self._pubkey, receiver=receiver,
                                    amount=amount, privkey=self._privkey,
                                    nonce=self._nonce, comment=comment)
        except Exception as e:
            print("TRANS_CREATION_FAIL: {}".format(repr(e)))
            return None
        else:
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
            self._broadcast_block(block_json)
            self._balance += 100
            return block

    # Recompute miner's balance using transactions in added block
    def _compute_balance(self):

    # Add new block to the blockchain
    def add_block(self, block_json):
        block = Block.from_json(block_json)
        try:
            self._blockchain.add(block)
        except Exception as e:
            print("BLK_ADD_FAIL: {}".format(repr(e)))
        else:
            # Block successfully added to blockchain
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
    def balance(self):
        return self._balance

    def deposit(self, value):
        if value > 0:
            self._balance += value

    def withdraw(self, value):
        if value > 0:
            self._balance -= value

    @property
    def nonce(self):
        return self._nonce

    def increment_nonce(self):
        self._nonce += 1

    @property
    def blockchain(self):
        return self._blockchain

    @property
    def transaction_pool(self):
        return self._transaction_pool


def create_miner_network(n):
    if n < 2:
        raise Exception("Network must have at least 2 miners.")
    miners = [Miner.new() for _ in range(n)]
    for m1 in miners:
        for m2 in miners:
            if m1 != m2:
                m1.add_peer(m2)
    return miners

if __name__ == "__main__":
    num_miners = 5
    miners = create_miner_network(num_miners)
    creator_sk = ecdsa.SigningKey.generate()
    creator_privkey = creator_sk.to_string().hex()
    creator_pubkey = creator_sk.get_verifying_key().to_string().hex()
    # Test spending with 0 coins
    print("(Miner 0) Trying to spend with no coins...")
    miners[0].create_transaction(receiver=miners[1].pubkey, amount=100,
                                 comment="cant spend")
    # Initialize coins
    num_trans = 20
    print("(Creator) Sending {} transactions to Miner 0...".format(num_trans))
    for i in range(num_trans):
        t = Transaction.new(sender=creator_pubkey, receiver=miners[0].pubkey,
                            amount=10, privkey=creator_privkey,
                            nonce=i, comment="init")
        for m in miners:
            m.add_transaction(t.to_json())
    # Mining initial block
    print("(Miner 0) Mining...")
    miners[0].create_block()
    # Blockchain of Miner 1 is updated because Miner 0 broadcasted block
    print("(Miner 1) Blockchain:{}"\
            .format(miners[1].blockchain.endhash_clen_map))
    # Balance is updated with 100 from mining and some more from creator
    print("(Miner 0) Total balance: {}".format(miners[0].total_balance))
    print("(Miner 0) Sending {} transactions to random miners..."\
            .format(num_trans))
    for i in range(num_trans):
        index = random.randint(1, num_miners - 1)
        miners[0].create_transaction(receiver=miners[index].pubkey,
                                     amount=5, comment="random")
    # Miner 1 has all the transactions sent previously
    print("(Miner 1) Num. transactions: {}"\
            .format(len(miners[1].transaction_pool)))

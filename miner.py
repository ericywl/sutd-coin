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
        self._total_balance = 0
        self._pending_balance = 0
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
            if amount > self.available_balance:
                raise Exception("Amount is higher than available balance.")
            trans = Transaction.new(sender=self._pubkey, receiver=receiver,
                                    amount=amount, privkey=self._privkey,
                                    nonce=self._nonce, comment=comment)
        except Exception as e:
            print("TRANS_CREATION_FAIL: {}".format(repr(e)))
            return None
        else:
            self._nonce += 1
            self._pending_balance += amount
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
    def create_block(self, n_trans=None):
        # Resolve blockchain to get last block
        last_blk = self._blockchain.resolve()
        # Remove blockchain transactions from pool
        added_transactions = set(self._blockchain.transactions)
        remaining_transactions = self._transaction_pool - added_transactions
        if len(remaining_transactions) == 0:
            print("BLK_CREATION_FAIL: No more transactions left.")
            return None
        # Get a set of random transactions from pool
        if n_trans == None:
            max_n = min(Miner.MAX_TRANS, len(remaining_transactions))
            n_trans = random.randint(1, max_n)
        if n_trans <= 0:
            print("BLK_CREATION_FAIL: Num. transactions less than 1.")
            return None
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
            self._total_balance += 100
            return block

    # Recompute miner's balance using transactions in added block
    def _compute_balance(self, block):
        for t_json in block.transactions:
            t = Transaction.from_json(t_json)
            if t.receiver == self._pubkey:
                self._total_balance += t.amount

    # Add new block to the blockchain
    def add_block(self, block_json):
        block = Block.from_json(block_json)
        try:
            self._blockchain.add(block)
        except Exception as e:
            print("BLK_ADD_FAIL: {}".format(repr(e)))
        else:
            # Block successfully added to blockchain
            self._compute_balance(block)

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
    def total_balance(self):
        return self._total_balance

    @property
    def pending_balance(self):
        return self._pending_balance

    @property
    def available_balance(self):
        return self._total_balance - self._pending_balance

    @property
    def nonce(self):
        return self._nonce

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

def print_balance(miners):
    print("===================================================")
    for j in range(len(miners)):
        print("(Miner {3}) Total: {0}, Pending: {1}, Available: {2}"\
          .format(miners[j].total_balance, miners[j].pending_balance,
                  miners[j].available_balance, j))
    print()

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
    n1 = 20
    amt1 = 10
    print("(Creator) Sending {0} transactions of amount {1} to Miner 0..."\
            .format(n1, amt1))
    for i in range(n1):
        t = Transaction.new(sender=creator_pubkey, receiver=miners[0].pubkey,
                            amount=amt1, privkey=creator_privkey,
                            nonce=i, comment="init")
        for m in miners:
            m.add_transaction(t.to_json())
    print_balance(miners)
    # Mining initial block
    num_trans = 10
    print("(Miner 0) Mining with {} transactions...".format(num_trans))
    miners[0].create_block(num_trans)
    print_balance(miners)
    # Blockchain of Miner 1 is updated because Miner 0 broadcasted block
    print("(Miner 1) Blockchain: {}"\
            .format(miners[1].blockchain.endhash_clen_map))
    # Balance is updated with 100 from mining and some more from creator
    # Sending transactions to others
    n2 = 20
    amt2 = 5
    print(("(Miner 0) Sending {0} transactions with amount {1} "
           "to random miners...").format(n2, amt2))
    for i in range(n2):
        index = random.randint(1, num_miners - 1)
        miners[0].create_transaction(receiver=miners[index].pubkey,
                                     amount=amt2, comment="random")
    print_balance(miners)
    # All miners start competing (random)
    for _ in range(1, len(miners)):
        i = random.randint(0, len(miners) - 1)
        print("(Miner {0}) Mining with {1} transactions...".format(i, num_trans))
        miners[i].create_block(num_trans)
        print_balance(miners)

"""Miner class declaration file"""
import random
import copy
import ecdsa

from transaction import Transaction
from blockchain import Blockchain
from block import Block
import algo


class Miner:
    """Miner class"""

    def __init__(self, privkey, pubkey):
        self._privkey = privkey
        self._pubkey = pubkey
        self._balance = {}
        self._blockchain = Blockchain.new()
        self._all_transactions = set()
        self._peers = []

    @classmethod
    def new(cls):
        """Create new Miner instance"""
        signing_key = ecdsa.SigningKey.generate()
        verifying_key = signing_key.get_verifying_key()
        priverifying_keyey = signing_key.to_string().hex()
        pubkey = verifying_key.to_string().hex()
        return cls(priverifying_keyey, pubkey)

    def _broadcast_transaction(self, trans_json):
        """Broadcast the transaction to the network"""
        # Assume that peers are all nodes in the network
        # (of course, not practical IRL since its not scalable)
        for peer in self._peers:
            peer.add_transaction(trans_json)

    def create_transaction(self, receiver, amount, comment=""):
        """Create a new transaction"""
        trans = Transaction.new(sender=self._pubkey, receiver=receiver,
                                amount=amount, privkey=self._privkey,
                                comment=comment)
        trans_json = trans.to_json()
        self.add_transaction(trans_json)
        self._broadcast_transaction(trans_json)
        return trans

    def add_transaction(self, trans_json):
        """Add transaction to the pool of transactions"""
        if trans_json in self._all_transactions:
            print("Transaction already exist in pool.")
            return
        trans = Transaction.from_json(trans_json)
        if not trans.verify():
            raise Exception("New transaction failed signature verification.")
        self._all_transactions.add(trans_json)

    def _broadcast_block(self, block_json):
        """Broadcast the block to the network"""
        # Assume that peers are all nodes in the network
        # (of course, not practical IRL since its not scalable)
        for peer in self._peers:
            peer.add_block(block_json)

    def _check_transactions_balance(self, transactions):
        """Check balance state if transactions were applied"""
        balance = copy.deepcopy(self._balance)
        for t_json in transactions:
            trans = Transaction.from_json(t_json)
            # Sender must exist so if it doesn't, return false
            if trans.sender not in balance:
                return False
            # Create new account for receiver if it doesn't exist
            if trans.receiver not in balance:
                balance[trans.receiver] = 0
            balance[trans.sender] -= trans.amount
            balance[trans.receiver] += trans.amount
            # Negative balance, return false
            if balance[trans.sender] < 0 or balance[trans.receiver] < 0:
                return False
        return True

    def _gather_transactions(self, transaction_pool):
        """Gather a random number of transactions that are valid"""
        # Put in coinbase transaction
        coinbase_trans = Transaction.new(
            sender=self._pubkey,
            receiver=self._pubkey,
            amount=Block.REWARD,
            privkey=self._privkey,
            comment="Coinbase"
        )
        gathered_transactions = [coinbase_trans.to_json()]
        # No transactions to process, return coinbase transaction only
        if not transaction_pool:
            return gathered_transactions
        n_trans = random.randint(1, len(transaction_pool))
        while True:
            if n_trans <= 0:
                raise Exception("Not enough valid transactions in pool.")
            trans_sample = random.sample(transaction_pool, n_trans)
            n_trans -= 1
            if self._check_transactions_balance(trans_sample):
                break
        gathered_transactions.extend(trans_sample)
        return gathered_transactions

    def create_block(self):
        """Create a new block"""
        # Resolve blockchain to get last block
        last_blk = self._blockchain.resolve()
        # Update own balance state with latest
        self._balance = self._blockchain.get_balance_by_fork(last_blk)
        # Get a set of random transactions from remaining transaction
        used_trans = self._blockchain.get_transactions_by_fork(last_blk)
        used_transactions = set(used_trans)
        remaining_transactions = self._all_transactions - used_transactions
        gathered_transactions =\
            self._gather_transactions(remaining_transactions)
        # Mine new block
        prev_hash = algo.hash2_dic(last_blk.header)
        block = Block.new(prev_hash, gathered_transactions)
        block_json = block.to_json()
        # Add and broadcast block
        self.add_block(block_json)
        self._broadcast_block(block_json)
        return block

    def add_block(self, block_json):
        """Add new block to the blockchain"""
        block = Block.from_json(block_json)
        self._blockchain.add(block)
        # Resolve blockchain to get last block
        last_blk = self._blockchain.resolve()
        # Update own balance state with latest
        self._balance = self._blockchain.get_balance_by_fork(last_blk)

    def add_peer(self, miner):
        """Add miner to peer list"""
        self._peers.append(miner)

    @property
    def pubkey(self):
        """Public key"""
        return self._pubkey

    @property
    def privkey(self):
        """Private key"""
        return self._privkey

    @property
    def balance(self):
        """Copy of balance state"""
        return copy.deepcopy(self._balance)

    @property
    def blockchain(self):
        """Copy of blockchain"""
        return copy.deepcopy(self._blockchain)

    @property
    def all_transactions(self):
        """Copy of all transactions (both used and unused)"""
        return copy.deepcopy(self._all_transactions)


def create_miner_network(num):
    """Create a miner network of num miners where all miners are connected to
    each other"""
    if num < 2:
        raise Exception("Network must have at least 2 miners.")
    miner_list = [Miner.new() for _ in range(num)]
    for miner1 in miner_list:
        for miner2 in miner_list:
            if miner1 != miner2:
                miner1.add_peer(miner2)
    return miner_list


def main():
    """Main function"""
    num_miners = 5
    miners = create_miner_network(num_miners)
    miners[0].create_block()
    print(miners[0].balance)
    for _ in range(5):
        index = random.randint(1, num_miners - 1)
        miners[0].create_transaction(miners[index].pubkey, 10)
    miners[1].create_block()
    print(miners[0].balance)


if __name__ == "__main__":
    main()

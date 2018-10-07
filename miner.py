"""Miner class declaration file"""
import random
import copy
import threading
import socket
import ecdsa

from transaction import Transaction
from blockchain import Blockchain
from block import Block
from server import Server
import algo


class Miner:
    """Miner class"""

    def __init__(self, privkey, pubkey, address):
        self._privkey = privkey
        self._pubkey = pubkey
        self._address = address
        self._balance = {}
        self._blockchain = Blockchain.new()
        self._added_transactions = set()
        self._all_transactions = set()
        self._peers = []
        # Thread locks and events
        self._blockchain_lock = threading.RLock()
        self._all_trans_lock = threading.RLock()
        self._added_trans_lock = threading.RLock()
        self._stop_mine = threading.Event()
        # Server
        self._server = Server(address, self)
        threading.Thread(target=self._server.run).start()

    @classmethod
    def new(cls, address):
        """Create new Miner instance"""
        signing_key = ecdsa.SigningKey.generate()
        verifying_key = signing_key.get_verifying_key()
        privkey = signing_key.to_string().hex()
        pubkey = verifying_key.to_string().hex()
        return cls(privkey, pubkey, address)

    @staticmethod
    def _send_message(msg, addr):
        """Send transaction to a single node"""
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(addr)
            client.sendall(msg.encode())
        finally:
            client.close()

    def _broadcast_message(self, msg):
        """Broadcast the transaction to the network"""
        # Assume that peers are all nodes in the network
        # (of course, not practical IRL since its not scalable)
        threads = []
        for peer in self._peers:
            new_thread = threading.Thread(target=self._send_message,
                                          args=(msg, peer.address))
            new_thread.start()
            threads.append(new_thread)
        for thread in threads:
            thread.join()

    def create_transaction(self, receiver, amount, comment=""):
        """Create a new transaction"""
        trans = Transaction.new(sender=self._pubkey, receiver=receiver,
                                amount=amount, privkey=self._privkey,
                                comment=comment)
        trans_json = trans.to_json()
        self.add_transaction(trans_json)
        self._broadcast_message("t" + trans_json)
        return trans

    def add_transaction(self, trans_json):
        """Add transaction to the pool of transactions"""
        trans = Transaction.from_json(trans_json)
        if not trans.verify():
            raise Exception("New transaction failed signature verification.")
        self._all_trans_lock.acquire()
        try:
            if trans_json in self._all_transactions:
                print("Transaction already exist in pool.")
                return
            self._all_transactions.add(trans_json)
        finally:
            self._all_trans_lock.release()

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
        self._blockchain_lock.acquire()
        self._added_trans_lock.acquire()
        self._all_trans_lock.acquire()
        try:
            last_blk = self._update()
            # Get a set of random transactions from pending transactions
            pending_transactions \
                = self._all_transactions - self._added_transactions
            gathered_transactions \
                = self._gather_transactions(pending_transactions)
            # Mine new block
            prev_hash = algo.hash1_dic(last_blk.header)
            block = Block.new(prev_hash, gathered_transactions,
                              self._stop_mine)
            if block is None:
                # Mining stopped by server
                return None
            block_json = block.to_json()
            # Add and broadcast block
            self.add_block(block_json)
            self._broadcast_message("b" + block_json)
            # Remove gathered transactions from pool and them to added pile
            self._added_transactions |= set(gathered_transactions)
        finally:
            self._blockchain_lock.release()
            self._added_trans_lock.release()
            self._all_trans_lock.release()
        return block

    def add_block(self, block_json):
        """Add new block to the blockchain"""
        block = Block.from_json(block_json)
        self._blockchain_lock.acquire()
        self._added_trans_lock.acquire()
        try:
            self._blockchain.add(block)
            self._update()
        finally:
            self._blockchain_lock.release()
            self._added_trans_lock.release()

    def _update(self):
        """Update miner's blockchain, balance state and transactions"""
        # Not thread safe! Only used in other thread safe methods
        # Resolve blockchain to get last block
        last_blk = self._blockchain.resolve()
        # Update balance state with latest
        self._balance = self._blockchain.get_balance_by_fork(last_blk)
        # Update added transactions with transactions in blockchain
        blockchain_transactions \
            = self._blockchain.get_transactions_by_fork(last_blk)
        self._added_transactions = set(blockchain_transactions)
        return last_blk

    def get_transaction_proof(self, tx_hash):
        """Get proof of transaction given transaction hash"""
        self._blockchain_lock.acquire()
        try:
            last_blk = self._blockchain.resolve()
            res = self._blockchain.get_transaction_proof_in_fork(
                tx_hash, last_blk)
        finally:
            self._blockchain_lock.release()
        return res

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
    def address(self):
        """Address tuple with IP and port"""
        return self._address

    @property
    def balance(self):
        """Copy of balance state"""
        return copy.deepcopy(self._balance)

    @property
    def blockchain(self):
        """Copy of blockchain"""
        self._blockchain_lock.acquire()
        try:
            blkchain_copy = copy.deepcopy(self._blockchain)
        finally:
            self._blockchain_lock.release()
        return blkchain_copy

    @property
    def pending_transactions(self):
        """Copy of pending transactions"""
        self._added_trans_lock.acquire()
        self._all_trans_lock.acquire()
        try:
            pending_transactions \
                = self._all_transactions - self._added_transactions
        finally:
            self._added_trans_lock.release()
            self._all_trans_lock.release()
        return copy.deepcopy(pending_transactions)

    @property
    def added_transactions(self):
        """Copy of added transactions"""
        self._added_trans_lock.acquire()
        try:
            added_trans_copy = copy.deepcopy(self._added_transactions)
        finally:
            self._added_trans_lock.release()
        return added_trans_copy

    @property
    def stop_mine(self):
        """Threading Event to stop mining"""
        return self._stop_mine


def create_miner_network(num, starting_port):
    """Create a miner network of num miners where all miners are connected to
    each other"""
    if num < 2:
        raise Exception("Network must have at least 2 miners.")
    miner_list = []
    for i in range(num):
        addr = ("localhost", starting_port + i)
        miner_list.append(Miner.new(addr))
    for miner1 in miner_list:
        for miner2 in miner_list:
            if miner1 != miner2:
                miner1.add_peer(miner2)
    return miner_list


def main():
    """Main function"""
    import time
    num_miners = 3
    miners = create_miner_network(num_miners, 12345)
    print(miners[1].blockchain.endhash_clen_map)
    thread1 = threading.Thread(target=miners[0].create_block)
    thread2 = threading.Thread(target=miners[1].create_block)
    thread1.start()
    thread2.start()
    thread1.join()
    thread2.join()
    time.sleep(3)
    print(miners[1].blockchain.endhash_clen_map)
    for _ in range(5):
        index = random.randint(1, num_miners - 1)
        miners[0].create_transaction(miners[index].pubkey, 10)
    time.sleep(2)
    print(len(miners[0].pending_transactions))
    print(len(miners[1].pending_transactions))
    print(len(miners[2].pending_transactions))


if __name__ == "__main__":
    main()

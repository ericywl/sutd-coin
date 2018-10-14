"""Miner class declaration file"""
from concurrent.futures import ThreadPoolExecutor
import time
import sys
import copy
import json
import random
import threading
import queue
import os.path
import ecdsa

import algo

from net_node import NetNode, _NetNodeListener
from block import Block
from blockchain import Blockchain
from transaction import Transaction


class Miner(NetNode):
    """Miner class"""

    def __init__(self, privkey, pubkey, address, listen=True):
        super().__init__(privkey, pubkey, address)
        self._balance = {}
        self._blockchain = Blockchain.new()
        self._added_transactions = set()
        self._all_transactions = set()
        # Queue
        self.block_queue = queue.Queue()
        self.tx_queue = queue.Queue()
        # Thread locks and events
        self.blockchain_lock = threading.RLock()
        self.all_tx_lock = threading.RLock()
        self.added_tx_lock = threading.RLock()
        self.balance_lock = threading.RLock()
        self.stop_mine = threading.Event()
        # Listener
        if listen:
            self._listener = _MinerListener(address, self)
            threading.Thread(target=self._listener.run).start()

    @classmethod
    def new(cls, address):
        """Create new Miner instance"""
        signing_key = ecdsa.SigningKey.generate()
        verifying_key = signing_key.get_verifying_key()
        privkey = signing_key.to_string().hex()
        pubkey = verifying_key.to_string().hex()
        return cls(privkey, pubkey, address)

    @property
    def balance(self):
        """Copy of balance state"""
        self._update()
        with self.balance_lock:
            balance_copy = copy.deepcopy(self._balance)
        return balance_copy

    @property
    def blockchain(self):
        """Copy of blockchain"""
        self._update()
        with self.blockchain_lock:
            blkchain_copy = copy.deepcopy(self._blockchain)
        return blkchain_copy

    @property
    def pending_transactions(self):
        """Copy of pending transactions"""
        self._update()
        self.added_tx_lock.acquire()
        self.all_tx_lock.acquire()
        try:
            pending_tx = self._all_transactions - self._added_transactions
        finally:
            self.added_tx_lock.release()
            self.all_tx_lock.release()
        return copy.deepcopy(pending_tx)

    @property
    def added_transactions(self):
        """Copy of added transactions"""
        self._update()
        with self.added_tx_lock:
            added_tx_copy = copy.deepcopy(self._added_transactions)
        return added_tx_copy

    @property
    def all_transactions(self):
        """Copy of all transactions"""
        self._update()
        with self.all_tx_lock:
            all_tx_copy = copy.deepcopy(self._all_transactions)
        return all_tx_copy

    def create_transaction(self, receiver, amount, comment=""):
        """Create a new transaction"""
        new_tx = Transaction.new(sender=self.pubkey, receiver=receiver,
                                 amount=amount, privkey=self.privkey,
                                 comment=comment)
        tx_json = new_tx.to_json()
        msg = "t" + json.dumps({"tx_json": tx_json})
        self.add_transaction(tx_json)
        self.broadcast_message(msg)
        return new_tx

    def add_transaction(self, tx_json):
        """Add transaction to the pool of transactions"""
        recv_tx = Transaction.from_json(tx_json)
        if not recv_tx.verify():
            raise Exception("New transaction failed signature verification.")
        with self.all_tx_lock:
            if tx_json in self._all_transactions:
                print(f"{self.name} - Transaction already exist in pool.")
                return
            self._all_transactions.add(tx_json)

    def create_block(self, prev_hash=None):
        """Create a new block"""
        # Update blockchain and balance state (thread safe)
        prev_blk = None if prev_hash is None else \
            self._blockchain.hash_block_map[prev_hash]
        last_blk = self._update(prev_blk)
        gathered_tx = self._gather_transactions()
        block = self._mine_new_block(last_blk.header, gathered_tx)
        if block is not None:
            blk_json = block.to_json()
            # Add block to blockchain (thread safe)
            self.add_block(blk_json)
            # Broadcast block and the header.
            self._broadcast_block(block)
            # Remove gathered transactions from pool and them to added pile
            with self.added_tx_lock:
                self._added_transactions |= set(gathered_tx)
            print(f"{self.__class__.__name__} {self.name} created a block.")
        self._update()
        return block

    def add_block(self, blk_json):
        """Add new block to the blockchain"""
        block = Block.from_json(blk_json)
        with self.blockchain_lock:
            self._blockchain.add(block)

    def get_transaction_proof(self, tx_hash):
        """Get proof of transaction given transaction hash"""
        with self.blockchain_lock:
            last_blk = self._blockchain.resolve()
            res = self._blockchain.get_transaction_proof_in_fork(
                tx_hash, last_blk)
        if res is None:
            return None
        last_blk_hash = algo.hash1_dic(last_blk.header)
        return res[0], res[1], last_blk_hash

    def get_balance(self, identifier):
        """Get balance given identifier ie. pubkey"""
        self._update()
        with self.balance_lock:
            if identifier not in self._balance:
                return 0
            return self._balance[identifier]

    # PRIVATE METHODS

    def _mine_new_block(self, last_blk_hdr, gathered_tx):
        # Mine new block
        prev_hash = algo.hash1_dic(last_blk_hdr)
        block = Block.new(prev_hash, gathered_tx, self.stop_mine)
        if block is None:
            # Mining stopped because a new block is received
            return None
        return block

    def _clear_queue(self):
        while self.block_queue.qsize() > 0:
            blk_json = self.block_queue.get()
            self.add_block(blk_json)
        while self.tx_queue.qsize() > 0:
            tx_json = self.tx_queue.get()
            with self.all_tx_lock:
                self.add_transaction(tx_json)

    def _broadcast_block(self, block):
        # b is only taken by miners while h is taken by spv_clients
        blk_json = block.to_json()
        self.broadcast_message("b" + json.dumps({"blk_json": blk_json}))
        self.broadcast_message("h" + json.dumps(block.header))

    def _update(self, last_blk=None):
        """Update miner's blockchain, balance state and transactions"""
        self._clear_queue()
        self.blockchain_lock.acquire()
        self.added_tx_lock.acquire()
        self.balance_lock.acquire()
        try:
            # Resolve blockchain to get last block
            if last_blk is None:
                last_blk = self._blockchain.resolve()
            # Update added transactions with transactions in blockchain
            blockchain_tx = self._blockchain.get_transactions_by_fork(last_blk)
            self._added_transactions = set(blockchain_tx)
            # Update balance state with latest
            self._balance = self._blockchain.get_balance_by_fork(last_blk)
        finally:
            self.blockchain_lock.release()
            self.added_tx_lock.release()
            self.balance_lock.release()
        self.stop_mine.clear()
        return last_blk

    def _check_transactions_balance(self, transactions):
        """Check balance state if transactions were applied"""
        self.balance_lock.acquire()
        try:
            balance = copy.deepcopy(self._balance)
        finally:
            self.balance_lock.release()
        for tx_json in transactions:
            recv_tx = Transaction.from_json(tx_json)
            # Sender must exist so if it doesn't, return false
            if recv_tx.sender not in balance:
                return False
            # Create new account for receiver if it doesn't exist
            if recv_tx.receiver not in balance:
                balance[recv_tx.receiver] = 0
            balance[recv_tx.sender] -= recv_tx.amount
            balance[recv_tx.receiver] += recv_tx.amount
            # Negative balance, return false
            if balance[recv_tx.sender] < 0 \
                    or balance[recv_tx.receiver] < 0:
                return False
        return True

    def _gather_transactions(self):
        """Gather transactions that are valid from pending"""
        # Get a set of random transactions from pending transactions
        self.added_tx_lock.acquire()
        self.all_tx_lock.acquire()
        try:
            pending_tx = self._all_transactions - self._added_transactions
            # Put in coinbase transaction
            coinbase_tx = Transaction.new(
                sender=self.pubkey,
                receiver=self.pubkey,
                amount=Block.REWARD,
                privkey=self.privkey,
                comment="Coinbase"
            )
            gathered_transactions = [coinbase_tx.to_json()]
            # No transactions to process, return coinbase transaction only
            if not pending_tx:
                return gathered_transactions
            # num_tx = random.randint(1, len(transaction_pool))
            num_tx = len(pending_tx)
            while True:
                if num_tx <= 0:
                    return gathered_transactions
                trans_sample = random.sample(pending_tx, num_tx)
                num_tx -= 1
                if self._check_transactions_balance(trans_sample):
                    break
            gathered_transactions.extend(trans_sample)
        finally:
            self.added_tx_lock.release()
            self.all_tx_lock.release()
        return gathered_transactions


class _MinerListener(_NetNodeListener):
    """Miner's Listener class"""

    def handle_client_data(self, data, client_sock):
        """Handle client data based on protocol indicator"""
        prot = data[0].lower()
        if prot == "n":
            # Sent by the central server when a new node joins
            peer = json.loads(data[1:])
            # print(f"{self._worker.name} has added a node to their network.")
            self._worker.add_peer(peer)
            client_sock.close()
        elif prot == "b":
            self._handle_block(data, client_sock)
        elif prot == "t":
            self._handle_transaction(data, client_sock)
        elif prot == "r":
            self._handle_transaction_proof(data, client_sock)
        elif prot == "x":
            self._handle_balance(data, client_sock)
        else:
            # either header or wrong message format
            client_sock.close()

    def _handle_block(self, data, client_sock):
        # Receive new block
        blk_json = json.loads(data[1:])["blk_json"]
        client_sock.close()
        # Stop mining if new block is received
        self._worker.stop_mine.set()
        self._worker.block_queue.put(blk_json)

    def _handle_transaction(self, data, client_sock):
        # Receive new transaction
        tx_json = json.loads(data[1:])["tx_json"]
        client_sock.close()
        if self._worker.all_tx_lock.acquire(False):
            self._worker.add_transaction(tx_json)
            self._worker.all_tx_lock.release()
        else:
            self._worker.tx_queue.put(tx_json)

    def _handle_transaction_proof(self, data, client_sock):
        # Process request for transaction proof
        tx_hash = json.loads(data[1:])["tx_hash"]
        tup = self._worker.get_transaction_proof(tx_hash)
        if tup is None:
            msg = json.dumps({
                "blk_hash": None,
                "proof": None,
                "last_blk_hash": None
            })
        else:
            msg = json.dumps({
                "blk_hash": tup[0],
                "proof": tup[1],
                "last_blk_hash": tup[2]
            })
        client_sock.sendall(msg.encode())
        client_sock.close()

    def _handle_balance(self, data, client_sock):
        pubkey = json.loads(data[1:])["identifier"]
        bal = self._worker.get_balance(pubkey)
        client_sock.sendall(str(bal).encode())
        client_sock.close()


def miner_main_send_tx(miner):
    """Used in main to send one transaction"""
    if miner.pubkey in miner.balance:
        if miner.balance[miner.pubkey] > 50:
            other = random.choice(miner.peers)
            miner.create_transaction(other["pubkey"], 50)
            print(f"Miner {miner.name} sent transaction to {other['name']}")


def main():
    """Main function"""
    # Execute miner routine
    miner = Miner.new(("127.0.0.1", int(sys.argv[1])))
    miner.startup()
    print(f"Miner established connection with {len(miner.peers)} peers")
    while not os.path.exists("mine_lock"):
        time.sleep(0.5)
    while True:
        # miner_main_send_tx(miner)
        blk = miner.create_block()
        time.sleep(1)
        if blk:
            print(miner.blockchain.endhash_clen_map)


if __name__ == "__main__":
    main()

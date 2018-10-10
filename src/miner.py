"""Miner class declaration file"""
import time
import sys
import copy
import json
import random
import threading
import ecdsa

import algo

from net_node import NetNode, _NetNodeListener
from block import Block
from blockchain import Blockchain
from transaction import Transaction


class Miner(NetNode):
    """Miner class"""

    def _clsname(self):
        return "Miner"

    def __init__(self, privkey, pubkey, address, listen=True):
        super().__init__(privkey, pubkey, address)
        print(f"Starting {self._clsname()} - {self.name} on {address}")

        self._balance = {}
        self._blockchain = Blockchain.new()
        self._added_transactions = set()
        self._all_transactions = set()
        # Thread locks and events
        self._blockchain_lock = threading.RLock()
        self._all_tx_lock = threading.RLock()
        self._added_tx_lock = threading.RLock()
        self._balance_lock = threading.RLock()
        self._stop_mine = threading.Event()
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
        self._added_tx_lock.acquire()
        self._all_tx_lock.acquire()
        try:
            pending_tx = self._all_transactions - self._added_transactions
        finally:
            self._added_tx_lock.release()
            self._all_tx_lock.release()
        return copy.deepcopy(pending_tx)

    @property
    def added_transactions(self):
        """Copy of added transactions"""
        self._added_tx_lock.acquire()
        try:
            added_tx_copy = copy.deepcopy(self._added_transactions)
        finally:
            self._added_tx_lock.release()
        return added_tx_copy

    @property
    def stop_mine(self):
        """Threading Event to stop mining"""
        return self._stop_mine

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
        self._all_tx_lock.acquire()
        try:
            if tx_json in self._all_transactions:
                print(f"{self.name} - Transaction already exist in pool.")
                return
            self._all_transactions.add(tx_json)
        finally:
            self._all_tx_lock.release()

    def create_block(self):
        """Create a new block"""
        # Update blockchain and balance state (thread safe)
        last_blk = self._update()
        # Get a set of random transactions from pending transactions
        self._added_tx_lock.acquire()
        self._all_tx_lock.acquire()
        try:
            pending_tx = self._all_transactions - self._added_transactions
            gathered_tx = self._gather_transactions(pending_tx)
        finally:
            self._added_tx_lock.release()
            self._all_tx_lock.release()
        # Mine new block
        prev_hash = algo.hash1_dic(last_blk.header)
        block = Block.new(prev_hash, gathered_tx, self._stop_mine)
        if block is None:
            # Mining stopped because a new block is received
            return None
        blk_json = block.to_json()
        # Add block to blockchain (thread safe)
        self.add_block(blk_json)
        # Broadcast block and the header.
        # b is only taken by miners while h is taken by spv_clients
        self.broadcast_message("b" + json.dumps({"blk_json": blk_json}))
        self.broadcast_message("h" + json.dumps(block.header))
        # Remove gathered transactions from pool and them to added pile
        self._added_tx_lock.acquire()
        try:
            self._added_transactions |= set(gathered_tx)
        finally:
            self._added_tx_lock.release()
            print("{} created a block.".format(self._name))
        return block

    def add_block(self, blk_json):
        """Add new block to the blockchain"""
        block = Block.from_json(blk_json)
        self._blockchain_lock.acquire()
        try:
            self._blockchain.add(block)
        finally:
            self._blockchain_lock.release()
        self._update()

    def get_transaction_proof(self, tx_hash):
        """Get proof of transaction given transaction hash"""
        self._blockchain_lock.acquire()
        try:
            last_blk = self._blockchain.resolve()
            res = self._blockchain.get_transaction_proof_in_fork(
                tx_hash, last_blk)
        finally:
            self._blockchain_lock.release()
        if res is None:
            return None
        last_blk_hash = algo.hash1_dic(last_blk.header)
        return res[0], res[1], last_blk_hash

    def get_balance(self, identifier):
        """Get balance given identifier ie. pubkey"""
        self._update()
        self._balance_lock.acquire()
        try:
            if identifier not in self._balance:
                return 0
            return self._balance[identifier]
        finally:
            self._balance_lock.release()

    # PRIVATE METHODS

    def _update(self):
        """Update miner's blockchain, balance state and transactions"""
        self._blockchain_lock.acquire()
        self._added_tx_lock.acquire()
        self._balance_lock.acquire()
        try:
            # Resolve blockchain to get last block
            last_blk = self._blockchain.resolve()
            # Update added transactions with transactions in blockchain
            blockchain_tx = self._blockchain.get_transactions_by_fork(last_blk)
            self._added_transactions = set(blockchain_tx)
            # Update balance state with latest
            self._balance = self._blockchain.get_balance_by_fork(last_blk)
        finally:
            self._blockchain_lock.release()
            self._added_tx_lock.release()
            self._balance_lock.release()
        return last_blk

    def _check_transactions_balance(self, transactions):
        """Check balance state if transactions were applied"""
        self._balance_lock.acquire()
        try:
            balance = copy.deepcopy(self._balance)
        finally:
            self._balance_lock.release()
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

    def _gather_transactions(self, transaction_pool):
        """Gather a random number of transactions that are valid"""
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
        if not transaction_pool:
            return gathered_transactions
        # num_tx = random.randint(1, len(transaction_pool))
        num_tx = len(transaction_pool)
        while True:
            if num_tx <= 0:
                return gathered_transactions
            trans_sample = random.sample(transaction_pool, num_tx)
            num_tx -= 1
            if self._check_transactions_balance(trans_sample):
                break
        gathered_transactions.extend(trans_sample)
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
        elif prot == "b":
            self._handle_block(data)
        elif prot == "t":
            self._handle_transaction(data)
        elif prot == "r":
            self._handle_transaction_proof(data, client_sock)
        elif prot == "x":
            self._handle_balance(data, client_sock)

    def _handle_block(self, data):
        # Receive new block
        blk_json = json.loads(data[1:])["blk_json"]
        # Stop mining if new block is received
        self._worker.stop_mine.set()
        self._worker.add_block(blk_json)
        self._worker.stop_mine.clear()

    def _handle_transaction(self, data):
        # Receive new transaction
        tx_json = json.loads(data[1:])["tx_json"]
        self._worker.add_transaction(tx_json)

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

    def _handle_balance(self, data, client_sock):
        pubkey = json.loads(data[1:])["identifier"]
        bal = self._worker.get_balance(pubkey)
        client_sock.sendall(str(bal).encode())

# def create_miner_network(num, starting_port):
#     """Create a miner network of num miners where all miners are connected to
#     each other"""
#     if num < 2:
#         raise Exception("Network must have at least 2 miners.")
#     miner_list = []
#     for i in range(num):
#         addr = ("localhost", starting_port + i)
#         miner_list.append(Miner.new(addr))
#     for miner1 in miner_list:
#         for miner2 in miner_list:
#             if miner1 != miner2:
#                 miner1.add_peer(miner2)
#     return miner_list

# def miner_run(miner):
#     """Execute miner routine"""
#     if miner.pubkey in miner.balance:
#         if miner.balance[miner.pubkey] > 50:
#             peer_index = random.randint(0, len(miner.peers) - 1)
#             miner.create_transaction(miner.peers[peer_index].pubkey, 50)
#     blk = miner.create_block()
#     if blk is None:
#         print(f"{miner.pubkey} stopped mining")
#     else:
#         print(f"{miner.pubkey} mined block")


# def parallel_miners_run(miners):
#     """Run miner routine parallely"""
#     import time
#     with ThreadPoolExecutor(max_workers=len(miners)) as executor:
#         for miner in miners:
#             executor.submit(miner_run, miner)
#     time.sleep(2)
#     print(miners[0].balance)
#     print(miners[0].blockchain.endhash_clen_map)


def main_send_transaction(miner):
    """Used in main to send one transaction"""
    if miner.pubkey in miner.balance:
        if miner.balance[miner.pubkey] > 50:
            other = random.choice(miner.peers)
            miner.create_transaction(other["pubkey"], 50)


def main():
    """Main function"""
    # Execute miner routine
    miner = Miner.new(("127.0.0.1", int(sys.argv[1])))
    miner.startup()
    print(f"Miner established connection with {len(miner.peers)} peers")
    time.sleep(5)
    print(len(miner.peers))
    while True:
        # main_send_transaction(miner)
        miner.create_block()


if __name__ == "__main__":
    main()

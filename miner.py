"""Miner class declaration file"""
from concurrent.futures import ThreadPoolExecutor
import time
import sys
import copy
import json
import random
import socket
import threading
import ecdsa

import algo


from parent import Parent
from block import Block
from blockchain import Blockchain
from transaction import Transaction


class Miner(Parent):
    """Miner class"""

    def __init__(self, privkey, pubkey, address, listen=True):
        super().__init__(privkey, pubkey, address)
        print("Starting Miner - {} on {}".format(self.name, address))

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

        if listen:
            # Listener
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

    def create_transaction(self, receiver, amount, comment=""):
        """Create a new transaction"""
        new_tx = Transaction.new(sender=self.pubkey, receiver=receiver,
                                 amount=amount, privkey=self.privkey,
                                 comment=comment)
        tx_json = new_tx.to_json()
        msg = "t" + json.dumps({"tx_json": tx_json})
        self.add_transaction(tx_json)
        self._broadcast_message(msg)
        return new_tx

    def add_transaction(self, tx_json):
        """Add transaction to the pool of transactions"""
        recv_tx = Transaction.from_json(tx_json)
        if not recv_tx.verify():
            raise Exception("New transaction failed signature verification.")
        self._all_tx_lock.acquire()
        try:
            if tx_json in self._all_transactions:
                print("{} - Transaction already exist in pool.".format(self.name))
                return
            self._all_transactions.add(tx_json)
        finally:
            self._all_tx_lock.release()

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
        self._broadcast_message("b" + json.dumps({"blk_json": blk_json}))
        self._broadcast_message("h" + json.dumps(block.header))
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


class _MinerListener:
    """Miner's Listener class"""

    def __init__(self, server_addr, miner):
        self._server_addr = server_addr
        self._miner = miner
        # TCP socket configuration
        self._tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._tcp_sock.bind(server_addr)
        self._tcp_sock.listen(5)

    def run(self):
        """Start the listener"""
        with ThreadPoolExecutor(max_workers=5) as executor:
            while True:
                conn, _ = self._tcp_sock.accept()
                # Start new thread to handle client
                executor.submit(self.handle_client, conn)

    def handle_client(self, client_sock):
        """Handle receiving and sending"""
        data = client_sock.recv(4096).decode()
        self.handle_client_data(data, client_sock)

    def handle_client_data(self, data, client_sock):
        """Handle the data switching"""
        prot = data[0].lower()
        if prot == "n":
            # sent by the central server when a new node joins
            peer = json.loads(data[1:])
            # print("{} has added a node to their network.".format(self._miner.name))
            self._miner.add_peer(peer)
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
        self._miner.stop_mine.set()
        self._miner.add_block(blk_json)
        self._miner.stop_mine.clear()

    def _handle_transaction(self, data, client_sock):
        # Receive new transaction
        tx_json = json.loads(data[1:])["tx_json"]
        client_sock.close()
        self._miner.add_transaction(tx_json)

    def _handle_transaction_proof(self, data, client_sock):
        # Process request for transaction proof
        tx_hash = json.loads(data[1:])["tx_hash"]
        tup = self._miner.get_transaction_proof(tx_hash)
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
        bal = self._miner.get_balance(pubkey)
        client_sock.sendall(str(bal).encode())
        client_sock.close()

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


# def main():
#     """Main function"""
#     num_miners = 8
#     miners = create_miner_network(num_miners, 12345)
#     for _ in range(5):
#         parallel_miners_run(miners)


# if __name__ == "__main__":
#     main()

if __name__ == "__main__":
    # Execute miner routine
    miner = Miner.new(("127.0.0.1", int(sys.argv[1])))
    miner.startup()
    # time.sleep(5)
    print("Miner established connection with {} peers".format(len(miner.peers)))
    while True:
        # if miner.pubkey in miner.balance:
        #     if miner.balance[miner.pubkey] > 50:
        #         peer_index = random.randint(0, len(miner.peers) - 1)
        #         miner.create_transaction(miner.peers[peer_index]["pubkey"], 50)
        # time.sleep(5)
        miner.create_block()
        print(miner.balance, miner.balance[miner.pubkey])
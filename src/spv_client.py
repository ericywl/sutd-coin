"""SPV Client class declaration file"""
from concurrent.futures import ThreadPoolExecutor
import copy
import json
import threading
import sys
import time
import random
import ecdsa

import algo

from net_node import NetNode, _NetNodeListener
from block import Block
from merkle_tree import verify_proof
from transaction import Transaction


class SPVClient(NetNode):
    """SPVClient class"""

    def __init__(self, privkey, pubkey, address):
        super().__init__(privkey, pubkey, address)
        print(f"Starting SPVClient - {self.name} on {address}")

        self._hash_transactions_map = {}
        genesis = Block.get_genesis()
        genesis_hash = algo.hash1_dic(genesis.header)
        self._hash_blkheader_map = {genesis_hash: genesis.header}
        # Thread locks
        self._trans_lock = threading.RLock()
        self._blkheader_lock = threading.RLock()
        # Listener
        self._listener = _SPVClientListener(address, self)
        threading.Thread(target=self._listener.run).start()

    @classmethod
    def new(cls, address):
        """Create new SPVClient instance"""
        signing_key = ecdsa.SigningKey.generate()
        verifying_key = signing_key.get_verifying_key()
        privkey = signing_key.to_string().hex()
        pubkey = verifying_key.to_string().hex()
        return cls(privkey, pubkey, address)

    @property
    def transactions(self):
        """Copy of list of own transactions"""
        self._trans_lock.acquire()
        try:
            tx_copy = copy.deepcopy(list(
                self._hash_transactions_map.values()))
        finally:
            self._trans_lock.release()
        return tx_copy

    @property
    def block_headers(self):
        """Copy of list of block headers"""
        self._blkheader_lock.acquire()
        try:
            blkheaders_copy = copy.deepcopy(list(
                self._hash_blkheader_map.values()))
        finally:
            self._blkheader_lock.release()
        return blkheaders_copy

    def create_transaction(self, receiver, amount, comment=""):
        """Create a new transaction"""
        trans = Transaction.new(sender=self.pubkey, receiver=receiver,
                                amount=amount, privkey=self.privkey,
                                comment=comment)
        tx_json = trans.to_json()
        msg = "t" + json.dumps({"tx_json": tx_json})
        self.broadcast_message(msg)
        return trans

    def add_transaction(self, tx_json):
        """Add transaction to the pool of transactions"""
        recv_tx = Transaction.from_json(tx_json)
        if not recv_tx.verify():
            raise Exception("New transaction failed signature verification.")
        if self.pubkey not in [recv_tx.sender, recv_tx.receiver]:
            # Transaction does not concern us, discard it
            return
        tx_hash = algo.hash1(tx_json)
        self._trans_lock.acquire()
        try:
            self._hash_transactions_map[tx_hash] = tx_json
        finally:
            self._trans_lock.release()

    def add_block_header(self, header):
        """Add block header to dictionary"""
        header_hash = algo.hash1_dic(header)
        if header_hash >= Block.TARGET:
            raise Exception("Invalid block header hash.")
        self._blkheader_lock.acquire()
        try:
            if header["prev_hash"] not in self._hash_blkheader_map:
                raise Exception("Previous block does not exist.")
            self._hash_blkheader_map[header_hash] = header
        finally:
            self._blkheader_lock.release()

    def request_balance(self):
        """Request balance from network"""
        req = "x" + json.dumps({"identifier": self.pubkey})
        replies = self.broadcast_request(req)
        return int(SPVClient._process_replies(replies))

    def verify_transaction_proof(self, tx_hash):
        """Verify that transaction is in blockchain"""
        req = "r" + json.dumps({"tx_hash": tx_hash})
        replies = self.broadcast_request(req)
        valid_reply = SPVClient._process_replies(replies)
        blk_hash = valid_reply["blk_hash"]
        proof = valid_reply["proof"]
        last_blk_hash = valid_reply["last_blk_hash"]
        # Transaction not in blockchain
        if proof is None:
            return False
        # Assume majority reply is not lying and that two hash checks
        # are sufficient (may not be true IRL)
        self._blkheader_lock.acquire()
        self._trans_lock.acquire()
        try:
            if blk_hash not in self._hash_blkheader_map \
                    or last_blk_hash not in self._hash_blkheader_map:
                raise Exception("Invalid transaction proof reply.")
            tx_json = self._hash_transactions_map[tx_hash]
            blk_header = self._hash_blkheader_map[blk_hash]
            if not verify_proof(tx_json, proof, blk_header["root"]):
                # Majority lied (eclipse attack)
                raise Exception("Transaction proof verification failed.")
        finally:
            self._blkheader_lock.release()
            self._trans_lock.release()
        return True

    # STATIC METHODS

    @staticmethod
    def _process_replies(replies):
        """Process the replies from sending requests"""
        replies = [rep for rep in replies if rep.lower() != "spv"]
        if not replies:
            raise Exception("No miner replies for request.")
        # Assume majority reply is valid
        valid_reply = max(replies, key=replies.count)
        return json.loads(valid_reply)


class _SPVClientListener(_NetNodeListener):
    """SPV client's Listener class"""

    def handle_client_data(self, data, client_sock):
        """Handle client data based on protocol indicator"""
        prot = data[0].lower()
        if prot == "n":
            # Sent by the central server when a new node joins
            address = json.loads(data[1:])
            # print(f"{self._worker.name} added a node to their network.")
            self._worker.add_peer(address)
            client_sock.close()
        elif prot == "h":
            # Receive new block header
            block_header = json.loads(data[1:])
            client_sock.close()
            self._worker.add_block_header(block_header)
        elif prot == "t":
            # Receive new transaction
            tx_json = json.loads(data[1:])["tx_json"]
            client_sock.close()
            self._worker.add_transaction(tx_json)
        elif prot in "rx":
            # Receive request for transaction proof or balance
            # Send "spv" back so client can exclude this reply
            client_sock.sendall("spv".encode())
            client_sock.close()
        else:
            client_sock.close()


def main():
    """Main function"""
    spv = SPVClient.new(("127.0.0.1", int(sys.argv[1])))
    spv.startup()
    print(f"SPVClient established connection with {len(spv.peers)} peers")
    spv_name = spv.name
    time.sleep(5)
    while True:
        print("fuck")
        # Request transaction proof
        transactions = spv.transactions
        if transactions:
            print("trans")
            i = random.randint(0, len(transactions) - 1)
            tx_hash = algo.hash1(transactions[i])
            tx_in_bc = spv.verify_transaction_proof(tx_hash)
            print(f"SPV {spv_name} check {tx_hash} in blockchain: {tx_in_bc}")
        time.sleep(1)
        # Create new transaction
        balance = spv.request_balance()
        if balance > 10:
            peer_index = random.randint(0, len(spv.peers) - 1)
            chosen_peer = spv.peers[peer_index]
            created_tx = spv.create_transaction(chosen_peer.pubkey, 10)
            tx_json = created_tx.to_json()
            tx_hash = algo.hash1(tx_json)
            print(f"SPV {spv_name} sent {tx_hash} to {chosen_peer['pubkey']}")


if __name__ == "__main__":
    main()

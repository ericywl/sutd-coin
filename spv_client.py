"""SPV Client class declaration file"""
from concurrent.futures import ThreadPoolExecutor
import copy
import json
import socket
import threading
import ecdsa

import algo
from block import Block
from merkle_tree import verify_proof
from transaction import Transaction


class SPVClient:
    """SPVClient class"""

    def __init__(self, privkey, pubkey, address):
        self._keypair = (privkey, pubkey)
        self._address = address
        self._hash_transactions_map = {}
        genesis = Block.get_genesis()
        genesis_hash = algo.hash1_dic(genesis.header)
        self._hash_blkheader_map = {genesis_hash: genesis}
        self._peers = []
        # Thread locks
        self._trans_lock = threading.RLock()
        self._blkheader_lock = threading.RLock()

    @classmethod
    def new(cls, address):
        """Create new SPVClient instance"""
        signing_key = ecdsa.SigningKey.generate()
        verifying_key = signing_key.get_verifying_key()
        privkey = signing_key.to_string().hex()
        pubkey = verifying_key.to_string().hex()
        return cls(privkey, pubkey, address)

    @staticmethod
    def _send_message(msg, address):
        """Send transaction to a single node"""
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(address)
            client.sendall(msg.encode())
        finally:
            client.close()

    def _broadcast_message(self, msg):
        """Broadcast the transaction to peers"""
        # Assume that peers are all nodes in the network
        # (of course, not practical IRL since its not scalable)
        with ThreadPoolExecutor(max_workers=len(self._peers)) as executor:
            for peer in self._peers:
                executor.submit(SPVClient._send_message, msg, peer.address)

    def create_transaction(self, receiver, amount, comment=""):
        """Create a new transaction"""
        trans = Transaction.new(sender=self.pubkey, receiver=receiver,
                                amount=amount, privkey=self.privkey,
                                comment=comment)
        trans_json = trans.to_json()
        self.add_transaction(trans_json)
        self._broadcast_message("t" + trans_json)
        return trans

    def add_transaction(self, tx_json):
        """Add transaction to the pool of transactions"""
        converted_tx = Transaction.from_json(tx_json)
        if not converted_tx.verify():
            raise Exception("New transaction failed signature verification.")
        tx_hash = algo.hash1(tx_json)
        self._hash_transactions_map[tx_hash] = tx_json

    def add_block_header(self, block_json):
        """Add block header to dictionary"""
        block = Block.from_json(block_json)
        blk_header_hash = algo.hash1_dic(block.header)
        if blk_header_hash >= Block.TARGET:
            raise Exception("Invalid block header hash.")
        if block.header["prev_hash"] not in self._hash_blkheader_map:
            raise Exception("Previous block does not exist.")
        self._hash_blkheader_map[blk_header_hash] = block.header

    @staticmethod
    def _send_request(req, addr):
        """Send request to a single node"""
        try:
            client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_sock.connect(addr)
            client_sock.sendall(req.encode())
            reply = client_sock.recv(4096).decode()
        finally:
            client_sock.close()
        if reply == "spv":
            return reply
        return json.loads(reply)

    def _broadcast_request(self, req):
        """Broadcast the request to peers"""
        executor = ThreadPoolExecutor(max_workers=len(self._peers))
        futures = [
            executor.submit(SPVClient._send_request, req, peer.address)
            for peer in self._peers
        ]
        executor.shutdown(wait=True)
        replies = [future.result() for future in futures]
        return replies

    def _request_transaction_proof(self, tx_hash):
        """Request transaction proof from peers, get majority reply"""
        replies = self._broadcast_request("r" + tx_hash)
        replies = [rep for rep in replies if rep.lower() != "spv"]
        if not replies:
            raise Exception("No miner replies for transaction proof.")
        # Assume majority reply is not lying
        reply_count = {
            rep: replies.count(rep) for rep in replies
        }
        valid_reply = max(reply_count.keys(),
                          key=lambda rep: reply_count[rep])
        return json.loads(valid_reply)

    def verify_transaction_proof(self, tx_hash):
        """Verify that transaction is in blockchain"""
        reply = self._request_transaction_proof(tx_hash)
        blk_hash = reply["blk_hash"]
        proof = reply["proof"]
        # Assume majority reply is not lying and that two hash checks
        # are sufficient (may not be true IRL)
        if blk_hash not in self._hash_blkheader_map \
                or reply["last_blk_hash"] not in self._hash_blkheader_map:
            raise Exception("Invalid transaction proof reply.")
        tx_json = self._hash_transactions_map[tx_hash]
        blk_header = self._hash_blkheader_map[blk_hash]
        if not verify_proof(tx_json, proof, blk_header["root"]):
            # Majority lied (eclipse attack)
            raise Exception("Transaction proof verification failed.")
        return True

    def add_peer(self, peer):
        """Add miner to peer list"""
        self._peers.append(peer)

    @property
    def privkey(self):
        """Private key"""
        return self._keypair[0]

    @property
    def pubkey(self):
        """Public key"""
        return self._keypair[1]

    @property
    def address(self):
        """Address tuple with IP and port"""
        return self._address

    @property
    def peers(self):
        """List of peers"""
        return self._peers

    @property
    def transactions(self):
        """Copy of list of own transactions"""
        return copy.deepcopy(list(self._hash_transactions_map.values()))

    @property
    def block_headers(self):
        """Copy of list of block headers"""
        return copy.deepcopy(list(self._hash_blkheader_map.values()))


class SPVClientListener:
    """SPV client's Listener class"""
    def __init__(self, server_addr, spv_client):
        self._server_addr = server_addr
        self._spv_client = spv_client
        # TCP socket configuration
        self._tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._tcp_sock.bind(server_addr)
        self._tcp_sock.listen(5)

    def run(self):
        """Start the listener"""
        while True:
            conn, _ = self._tcp_sock.accept()
            # Start new thread to handle client
            new_thread = threading.Thread(target=self.handle_client,
                                          args=[conn])
            new_thread.start()

    def handle_client(self, client_sock):
        """Handle receiving and sending"""
        data = client_sock.recv(4096).decode()
        if data[0].lower() == "b":
            blk_json = data[1:]
            client_sock.close()
            self._spv_client.add_block_header(blk_json)
        elif data[0].lower() == "r":
            client_sock.sendall("spv".encode())
            client_sock.close()

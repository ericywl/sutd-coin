"""SPV Client class declaration file"""
from concurrent.futures import ThreadPoolExecutor
import copy
import json
import socket
import threading
import ecdsa
from monsterurl import get_monster

import algo

from trusted_server import TrustedServer
from block import Block
from merkle_tree import verify_proof
from transaction import Transaction


class SPVClient:
    """SPVClient class"""

    def __init__(self, privkey, pubkey, address):
        self._name = get_monster()
        print("Starting SPV Client - {}".format(self._name))

        self._keypair = (privkey, pubkey)
        self._address = address
        self._hash_transactions_map = {}
        genesis = Block.get_genesis()
        genesis_hash = algo.hash1_dic(genesis.header)
        self._hash_blkheader_map = {genesis_hash: genesis.header}
        self._peers = []
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

    def startup(self):
        """Obtain nodes with TrustedServer"""
        print("Obtaining nodes..")
        SPVClient._send_message("a".encode(), (TrustedServer.HOST, TrustedServer.PORT))
        print("Established connections with {} nodes".format(len(self._peers)))
        SPVClient._send_message("n".encode(), (TrustedServer.HOST, TrustedServer.PORT))

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
        self._broadcast_transaction(msg)
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
        replies = self._broadcast_request(req)
        return int(SPVClient._process_replies(replies))

    def verify_transaction_proof(self, tx_hash):
        """Verify that transaction is in blockchain"""
        req = "r" + json.dumps({"tx_hash": tx_hash})
        replies = self._broadcast_request(req)
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

    def set_peers(self, peers):
        """set peers on first discovery"""
        self._peers = peers

    def add_peer(self, peer):
        """Add miner to peer list"""
        self._peers.append(peer)

    # PRIVATE AND STATIC METHODS

    def _broadcast_request(self, req):
        """Broadcast the request to peers"""
        if not self._peers:
            raise Exception("Not connected to network.")
        executor = ThreadPoolExecutor(max_workers=len(self._peers))
        futures = [
            executor.submit(SPVClient._send_request, req, peer)
            for peer in self._peers
        ]
        executor.shutdown(wait=True)
        replies = [future.result() for future in futures]
        return replies

    def _broadcast_transaction(self, msg):
        """Broadcast the transaction to peers"""
        # Assume that peers are all nodes in the network
        # (of course, not practical IRL since its not scalable)
        if not self._peers:
            raise Exception("Not connected to network.")
        with ThreadPoolExecutor(max_workers=len(self._peers)) as executor:
            for peer in self._peers:
                executor.submit(SPVClient._send_message, msg, peer)

    @staticmethod
    def _send_message(msg, address):
        """Send transaction to a single node"""
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect(address)
            client.sendall(msg.encode())
        finally:
            client.close()

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
        return reply

    @staticmethod
    def _process_replies(replies):
        """Process the replies from sending requests"""
        replies = [rep for rep in replies if rep.lower() != "spv"]
        if not replies:
            raise Exception("No miner replies for request.")
        # Assume majority reply is valid
        valid_reply = max(replies, key=replies.count)
        return json.loads(valid_reply)

class _SPVClientListener:
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
        prot = data[0].lower()
        if prot == "n":
            # sent by the central server when a new node joins
            address = json.loads(data[1:])["address"]
            self._spv_client.add_peer(address)
            client_sock.close()
        elif prot == "a":
            # sent by the central server when requested for a list of addresses
            addresses = json.loads(data[1:])["addresses"]
            self._spv_client.set_peers(addresses)
            client_sock.close()
        elif prot == "h":
            # Receive new block header
            block_header = json.loads(data[1:])
            client_sock.close()
            self._spv_client.add_block_header(block_header)
        elif prot == "t":
            # Receive new transaction
            tx_json = json.loads(data[1:])["tx_json"]
            client_sock.close()
            self._spv_client.add_transaction(tx_json)
        elif prot in "rx":
            # Receive request for transaction proof or balance
            # Send "spv" back so client can exclude this reply
            client_sock.sendall("spv".encode())
            client_sock.close()
        else:
            client_sock.close()

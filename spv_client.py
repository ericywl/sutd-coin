"""SPV Client class declaration file"""
import ecdsa

from transaction import Transaction
from block import Block
import algo


class SPVClient:
    """SPVClient class"""

    def __init__(self, privkey, pubkey):
        self._privkey = privkey
        self._pubkey = pubkey
        self._transactions = []
        self._peers = []
        self._hash_blkheader_map = {}

    @classmethod
    def new(cls):
        """Create new SPVClient instance"""
        signing_key = ecdsa.SigningKey.generate()
        verifying_key = signing_key.get_verifying_key()
        privkey = signing_key.to_string().hex()
        pubkey = verifying_key.to_string().hex()
        return cls(privkey, pubkey)

    def _broadcast_transaction(self, trans_json):
        """Broadcast the transaction to the network"""
        # Assume that peers are all nodes in the network
        # (of course, not practical IRL since its not scalable)
        for peer in self._peers:
            peer.receive_transaction(trans_json)

    def create_transaction(self, receiver, amount, comment=""):
        """Create a new transaction"""
        trans = Transaction.new(sender=self._pubkey, receiver=receiver,
                                amount=amount, privkey=self._privkey,
                                comment=comment)
        trans_json = trans.to_json()
        self._transactions.append(trans_json)
        self._broadcast_transaction(trans_json)
        return trans

    def receive_transaction(self, trans_json):
        """Receive a transaction from the network"""
        trans = Transaction.from_json(trans_json)
        if not trans.verify():
            raise Exception("New transaction failed signature verification.")
        self._transactions.append(trans_json)

    def receive_block(self, block_json):
        """Receive a block header from the network"""
        block = Block.from_json(block_json)
        block_header_hash = algo.hash2_dic(block.header)
        # Store only block headers
        self._hash_blkheader_map[block_header_hash] = block.header

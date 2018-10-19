"""Block class declaration file"""
import copy
import datetime
import json
import os
import ecdsa

from merkle_tree import MerkleTree
from transaction import Transaction
import algo


class Block:
    """Block class"""
    _zeroes = "0000"
    _interm = "1"
    TARGET = _zeroes + _interm + (64 - len(_zeroes) - len(_interm)) * "f"
    REWARD = 100

    def __init__(self, header, transactions=None):
        if transactions is None:
            transactions = []
        self._header = header
        self._transactions = transactions

    @classmethod
    def new(cls, prev_hash, transactions, stop_mine):
        """Create new Block instance"""
        if not transactions:
            raise Exception("No transactions in block creation.")
        root = MerkleTree(transactions).get_root()
        header = {
            "prev_hash": prev_hash,
            "root": root,
            "timestamp": datetime.datetime.utcnow().timestamp(),
            "nonce": os.urandom(algo.NONCE_LEN // 2).hex()
        }
        while not stop_mine.is_set():
            # Compute hash to meet target
            header_hash = algo.hash1_dic(header)
            if header_hash < Block.TARGET:
                return cls(header, transactions)
            header["nonce"] = os.urandom(algo.NONCE_LEN // 2).hex()
        return None

    @classmethod
    def get_genesis(cls):
        """Get the genesis block"""
        header = {
            "prev_hash": algo.HASH_LEN * '0',
            "root": algo.HASH_LEN * 'f',
            "timestamp": 1337.0,
            "nonce": algo.NONCE_LEN * '0'
        }
        return cls(header)

    def to_json(self):
        """Convert Block object into JSON string"""
        return json.dumps({
            "header": self.header,
            "transactions": self._transactions
        })

    @classmethod
    def from_json(cls, json_str):
        """Convert JSON string into Block object"""
        obj = json.loads(json_str)
        fields = ["header", "transactions"]
        if not all(elem in obj.keys() for elem in fields):
            raise Exception("Block JSON string is invalid.")
        header_fields = ["prev_hash", "root", "timestamp", "nonce"]
        if not all(elem in obj["header"].keys() for elem in header_fields):
            raise Exception("Block JSON header is invalid.")
        block = cls(obj["header"], obj["transactions"])
        if not block.validate():
            return None
        return block

    def validate(self):
        """Validate block"""
        # Check block header type
        if not isinstance(self.header, dict):
            raise Exception("Block header not dictionary.")
        # Check previous header hash
        if not isinstance(self.header["prev_hash"], str):
            raise Exception("Previous header hash not string.")
        if len(self.header["prev_hash"]) != algo.HASH_LEN:
            raise Exception("Previous header hash length is invalid.")
        # Check Merkle tree root
        if not isinstance(self.header["root"], str):
            raise Exception("Merkle tree root hash not string.")
        if len(self.header["root"]) != algo.HASH_LEN:
            raise Exception("Merkle tree root hash length is invalid.")
        # Check timestamp
        if not isinstance(self.header["timestamp"], float):
            raise Exception("Timestamp not float.")
        if self.header["timestamp"] <= 0:
            raise Exception("Invalid timestamp value.")
        # Check nonce
        if not isinstance(self.header["nonce"], str):
            raise Exception("Nonce not integer.")
        if len(self.header["nonce"]) != algo.NONCE_LEN:
            raise Exception("Nonce length is invalid.")
        # Check transactions
        if not isinstance(self._transactions, list):
            raise Exception("Transactions not list.")
        return True

    def _check_header_hash(self):
        header_hash = algo.hash1_dic(self.header)
        return header_hash < Block.TARGET

    def _check_root(self):
        """Compare calculated root with stored root"""
        calc_root = MerkleTree(self._transactions).get_root()
        return calc_root == self.header["root"]

    def _verify_transactions(self):
        """Verify all transactions"""
        for i in range(len(self._transactions)):
            t_json = self._transactions[i]
            trans = Transaction.from_json(t_json)
            # Coinbase transaction additional checks
            if i == 0:
                if trans.amount != Block.REWARD:
                    return False
                if trans.sender != trans.receiver:
                    return False
            if not trans.verify():
                return False
        return True

    def _check_duplicate_trans(self):
        """Check if transactions have duplicates"""
        transactions_set = set(self._transactions)
        return len(transactions_set) == len(self._transactions)

    def verify(self):
        """Block verification (self-contained)"""
        if self == Block.get_genesis():
            return True
        # Check header hash meets target
        if not self._check_header_hash():
            raise Exception("Invalid block header hash.")
        # Check Merkle Tree root of block
        if not self._check_root():
            raise Exception("Invalid root in block.")
        # Verify transactions in block
        if not self._verify_transactions():
            raise Exception("Some transactions are invalid.")
        if not self._check_duplicate_trans():
            raise Exception("Duplicate transactions found.")
        return True

    def get_transaction_proof(self, tx_hash):
        """Get proof for transaction given transaction hash"""
        for t_json in self._transactions:
            if tx_hash == algo.hash1(t_json):
                return MerkleTree(self._transactions).get_proof(t_json)
        return None

    def __eq__(self, other):
        return self.to_json() == other.to_json()

    def __str__(self):
        string = "Block Information\n"
        string += "============================\n"
        string += "Previous hash: {}\n".format(self.header["prev_hash"])
        string += "Root: {}\n".format(self.header["root"])
        timestamp = datetime.datetime.utcfromtimestamp(
            self.header["timestamp"])
        string += "Timestamp: {} UTC\n".format(timestamp)
        string += "Nonce: {}\n".format(self.header["nonce"])
        return string

    @property
    def transactions(self):
        """Copy of transactions in block"""
        return copy.deepcopy(self._transactions)

    @property
    def header(self):
        """Copy of block header"""
        return copy.deepcopy(self._header)


def generate_transactions(num):
    """Generate num number of transactions"""
    transactions = []
    for j in range(num):
        sender_sk = ecdsa.SigningKey.generate()
        sender_privkey = sender_sk.to_string().hex()
        sender_pubkey = sender_sk.get_verifying_key().to_string().hex()
        receiver_sk = ecdsa.SigningKey.generate()
        receiver_pubkey = receiver_sk.get_verifying_key().to_string().hex() \
            if j != 0 else sender_pubkey
        amt = Block.REWARD if j == 0 else j
        trans = Transaction.new(sender_pubkey, receiver_pubkey, amt,
                                sender_privkey, str(j))
        transactions.append(trans.to_json())
    return transactions


def main():
    """Main function"""
    import time
    import threading
    print("Generating transactions...")
    transactions = generate_transactions(20)
    start = time.time()
    block_1 = Block.new(os.urandom(algo.HASH_LEN // 2).hex(),
                     transactions, threading.Event())
    elapsed = time.time() - start
    print("Time to make new block: {}s".format(elapsed))
    block_2 = Block.from_json(block_1.to_json())
    print("Testing from_json and to_json: {}".format(block_1 == block_2))


if __name__ == "__main__":
    main()

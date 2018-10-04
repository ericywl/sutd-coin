"""Block class declaration file"""
import datetime
import json
import copy
import ecdsa

from merkle_tree import MerkleTree
from transaction import Transaction
import algo


class Block:
    """Block class"""
    _zeroes = "0000"
    _interm = "55"
    TARGET = _zeroes + _interm + (64 - len(_zeroes) - len(_interm)) * "f"
    REWARD = 100

    def __init__(self, header, transactions=None):
        if transactions is None:
            transactions = []
        self._header = header
        self._transactions = transactions

    @classmethod
    def new(cls, prev_hash, transactions):
        """Create new Block instance"""
        if not transactions:
            raise Exception("No transactions in block creation.")
        root = MerkleTree(transactions).get_root()
        header = {
            "prev_hash": prev_hash,
            "root": root,
            "timestamp": datetime.datetime.utcnow().timestamp(),
            "nonce": 0
        }
        while True:
            # Compute hash to meet target
            header_hash = algo.hash2_dic(header)
            if header_hash < Block.TARGET:
                return cls(header, transactions)
            header["nonce"] += 1

    @classmethod
    def get_genesis(cls):
        """Get the genesis block"""
        header = {
            "prev_hash": algo.HASH_LEN * '0',
            "root": algo.HASH_LEN * 'f',
            "timestamp": 1337.0,
            "nonce": 0
        }
        return cls(header)

    def to_json(self):
        """Convert Block object into JSON string"""
        return json.dumps({
            "header": self._header,
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
        if not isinstance(self._header, dict):
            raise Exception("Block header not dictionary.")
        # Check previous header hash
        if not isinstance(self._header["prev_hash"], str):
            raise Exception("Previous header hash not string.")
        if len(self._header["prev_hash"]) != algo.HASH_LEN:
            raise Exception("Previous header hash length is invalid.")
        # Check Merkle tree root
        if not isinstance(self._header["root"], str):
            raise Exception("Merkle tree root hash not string.")
        if len(self._header["root"]) != algo.HASH_LEN:
            raise Exception("Merkle tree root hash length is invalid.")
        # Check timestamp
        if not isinstance(self._header["timestamp"], float):
            raise Exception("Timestamp not float.")
        if self._header["timestamp"] <= 0:
            raise Exception("Invalid timestamp value.")
        # Check nonce
        if not isinstance(self._header["nonce"], int):
            raise Exception("Nonce not integer.")
        if self._header["nonce"] < 0:
            raise Exception("Nonce cannot be negative.")
        # Check transactions
        if not isinstance(self._transactions, list):
            raise Exception("Transactions not list.")
        return True

    def _check_root(self):
        """Compare calculated root with stored root"""
        calc_root = MerkleTree(self._transactions).get_root()
        return calc_root == self._header["root"]

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
        # Check Merkle Tree root of block
        if not self._check_root():
            raise Exception("Invalid root in block.")
        # Verify transactions in block
        if not self._verify_transactions():
            raise Exception("Some transactions are invalid.")
        if not self._check_duplicate_trans():
            raise Exception("Duplicate transactions found.")
        return True

    def __eq__(self, other):
        json1 = self.to_json()
        json2 = other.to_json()
        return json1 == json2

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
    import os
    import time
    print("Generating transactions...")
    transactions = generate_transactions(20)
    start = time.time()
    blk1 = Block.new(os.urandom(32).hex(), transactions)
    elapsed = time.time() - start
    print("Time to make new block: {}s".format(elapsed))
    blk2 = Block.from_json(blk1.to_json())
    print("Testing from_json and to_json: {}".format(blk1 == blk2))


if __name__ == "__main__":
    main()

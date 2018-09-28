from merkle_tree import *
from transaction import *
import algo

import datetime, json

class Block:
    _zeroes = "000"
    TARGET = _zeroes + (64 - len(_zeroes)) * "f"

    def __init__(self, header, transactions=[]):
        self._header = header
        self._transactions = transactions

    @classmethod
    def new(cls, prev_hash, transactions=[]):
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

    def to_json(self):
        return json.dumps({
            "header": self._header,
            "transactions": self._transactions
        })

    @classmethod
    def from_json(cls, json_str):
        obj = json.loads(json_str)
        fields = ["header", "transactions"]
        if all(elem in obj.values() for elem in fields):
            raise Exception("Block JSON string is invalid.")
        header_fields = ["prev_hash", "root", "timestamp", "nonce"]
        if all(elem in obj["header"].values() for elem in header_fields):
            raise Exception("Block JSON header is invalid.")
        block = cls(obj["header"], obj["transactions"])
        if block.validate():
            return block

    # Validate block
    def validate(self):
        # Check block header type
        if type(self._header) != dict:
            raise Exception("Block header not dictionary.")
        # Check previous header hash
        if type(self._header["prev_hash"]) != str:
            raise Exception("Previous header hash not string.")
        if len(self._header["prev_hash"]) != algo.HASH_LEN:
            raise Exception("Previous header hash length is invalid.")
        # Check timestamp
        if type(self._header["timestamp"]) != float:
            raise Exception("Timestamp not float.")
        if self._header["timestamp"] <= 0:
            raise Exception("Invalid timestamp value.")
        # Check nonce
        if type(self._header["nonce"]) != int:
            raise Exception("Nonce not integer.")
        if self._header["nonce"] < 0:
            raise Exception("Nonce cannot be negative.")
        # Check transactions
        if type(self._transactions) != list:
            raise Exception("Transactions not list.")
        return True

    # Compare calculated root with stored root
    def _check_root(self):
        calc_root = MerkleTree(self._transactions).get_root()
        return calc_root == self._header["root"]

    # Verify all transactions
    def _verify_transactions(self):
        for t_json in self._transactions:
            t = Transaction.from_json(t_json)
            if not t.verify():
                return False
        return True

    # Check if transactions have duplicates
    def _check_duplicate_trans(self):
        transactions_set = set(self._transactions)
        return len(transactions_set) == len(self._transactions)

    def verify(self):
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
        j1 = self.to_json()
        j2 = other.to_json()
        return j1 == j2

    @property
    def transactions(self):
        return self._transactions

    @property
    def header(self):
        return self._header

if __name__ == "__main__":
    import os
    b1 = Block.new(os.urandom(32).hex())
    b2 = Block.from_json(b1.to_json())
    print(b1 == b2)



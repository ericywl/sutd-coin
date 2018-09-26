from merkle_tree import *
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
        for f in fields:
            if not obj[f]:
                raise Exception("Block JSON string is invalid.")
        header_fields = ["prev_hash", "root", "timestamp", "nonce"]
        for f in header_fields:
            if not obj["header"][f]:
                raise Exception("Block JSON string is invalid.")
        block = cls(obj["header"], obj["transactions"])
        if block.validate():
            return block

    def validate(self):
        # Validate block
        ## Check block header type
        if type(self._header) != dict:
            raise Exception("Block header not dictionary.")
        ## Check previous header hash
        if type(self._header["prev_hash"]) != str:
            raise Exception("Previous header hash not string.")
        if len(self._header["prev_hash"]) != str:
            raise Exception("Previous header hash length is invalid.")
        ## Check timestamp
        if type(self._header["timestamp"]) != int:
            raise Exception("Timestamp not integer.")
        if self._header["timestamp"] <= 0:
            raise Exception("Invalid timestamp value.")
        ## Check nonce
        if type(self._header["nonce"]) != int:
            raise Exception("Nonce not integer.")
        if self._header["nonce"] <= 0:
            raise Exception("Invalid nonce value.")
        ## Check transactions
        if type(self._transactions) != list:
            raise Exception("Transactions not list.")
        return True

    @property
    def transactions(self):
        return self._transactions

    @property
    def header(self):
        return self._header

if __name__ == "__main__":
    b = Block.new("abcd")
    j = json.dumps(b)
    print(j)



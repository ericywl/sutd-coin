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

    @property
    def transactions(self):
        return self._transactions

    @property
    def header(self):
        return self._header



"""Double spending demonstration"""
import time
import json
import queue
import threading

import algo
from trusted_server import TrustedServer
from spv_client import SPVClient
from miner import Miner, _MinerListener
from transaction import Transaction
from block import Block


class DoubleSpendMiner(Miner):
    """DoubleSpendMiner class"""
    INIT_MODE = 0
    FORK_MODE = 1
    FIRE_MODE = 2

    def __init__(self, privkey, pubkey, address):
        super().__init__(privkey, pubkey, address, listen=True)
        self.excluded_transactions = set()
        self.withheld_blocks = []
        self.mode = DoubleSpendMiner.INIT_MODE
        self.pubchain_count = 0
        self.pubchain_count_lock = threading.RLock()

    def _get_tx_pool(self):
        return super()._get_tx_pool() - self.excluded_transactions

    def create_block(self, prev_hash=None):
        if self.mode == DoubleSpendMiner.FORK_MODE and self.withheld_blocks:
            blk = self.withheld_blocks[-1]
            return super().create_block(algo.hash1_dic(blk.header))
        else:
            return super().create_block()

    def _broadcast_block(self, block):
        if self.mode == DoubleSpendMiner.FORK_MODE:
            self.withheld_blocks.append(block)
        elif self.mode == DoubleSpendMiner.FIRE_MODE:
            # Start thinking of firing
            self.withheld_blocks.append(block)
            with self.pubchain_count_lock:
                if len(self.withheld_blocks) > self.pubchain_count:
                    self.push_blocks()
        else:
            super()._broadcast_block(block)

    def push_blocks(self):
        for blk in self.withheld_blocks:
            self._broadcast_block(blk)
        self.withheld_blocks = []
        self.mode = DoubleSpendMiner.INIT_MODE

    def find_peer(self, clsname):
        for peer in self.peers:
            if peer["class"] == clsname:
                return peer
        raise Exception("Fuck")


class _DoubleSpendMinerListener(_MinerListener):
    """DoubleSpendMinerListener class"""

    def handle_client_data(self, data, client_sock):
        prot = data[0].lower()
        if prot == "b":
            if self._worker.mode == DoubleSpendMiner.INIT_MODE:
                # Change to fork mode if badSPV receive coins
                blk_json = json.loads(data[1:])["blk_json"]
                blk = Block.from_json(blk_json)
                bad_spv = self._worker.find_peer("DoubleSpendSPVClient")
                for tx_json in blk.transactions:
                    blk_tx = Transaction.from_json(tx_json)
                    if (blk_tx.sender == self._worker.pubkey and
                            blk_tx.receiver == bad_spv["pubkey"]):
                        self._worker.mode = DoubleSpendMiner.FORK_MODE
                        break
            elif self._worker.mode == DoubleSpendMiner.FORK_MODE:
                with self._worker.pubchain_count_lock:
                    self._worker.pubchain_count += 1
            self._handle_block(data, client_sock)
        elif prot == "t":
            self._ds_handle_transaction(data, client_sock)
        else:
            # Handle as per usual
            super().handle_client_data(data, client_sock)

    def _ds_handle_transaction(self, data, client_sock):
        tx_json = json.loads(data[1:])["tx_json"]
        recv_tx = Transaction.from_json(tx_json)
        bad_spv = self._worker.find_peer("DoubleSpendSPVClient")
        vendor = self._worker.find_peer("Vendor")
        if self._worker.mode == DoubleSpendMiner.FORK_MODE:
            # Receive coins from bad SPV (double spend)
            if (recv_tx.sender == bad_spv["pubkey"]
                    and recv_tx.receiver == self._worker.pubkey):
                self._worker.mode = DoubleSpendMiner.FIRE_MODE
        if (recv_tx.sender == bad_spv["pubkey"]
                and recv_tx.receiver == vendor["pubkey"]):
            # Exclude vendor transaction
            self._worker.excluded_transactions.add(tx_json)
            client_sock.close()
        else:
            self._handle_transaction(data, client_sock)


class DoubleSpendSPVClient(SPVClient):
    """DoubleSpendSPVClient class"""
    # The miner cannot be the one doing the transaction with the vendor
    # because the miner can earn rewards from mining and those earned rewards
    # will be able to compensate for the "cheated" amount


class Vendor(SPVClient):
    """Vendor class"""

    def send_product(self, tx_hash):
        """Simulate delivering the product to a buyer"""
        # Make new protocol prefix so buyer can receive this message?
        # Used by DoubleSpendMiner to determine when to start forking
        print(f"{self.__class__.__name__} sent product for {tx_hash}")


def map_pubkey_to_name(obs):
    """Map pubkey to name in balance"""
    name_balance = {}
    for key, val in obs.balance.items():
        items = [x for x in obs.peers if x["pubkey"] == key]
        if key == obs.pubkey:
            name_balance[obs.name] = val
        elif items:
            item = items[0]
            name_balance[item["name"]] = val
    return name_balance


def test():
    """Test function"""
    TrustedServer()
    time.sleep(3)
    normal_miner = Miner.new(("localhost", 12345))
    vendor = Vendor.new(("localhost", 22345))
    bad_spv = DoubleSpendSPVClient.new(("localhost", 32345))
    bad_miner = DoubleSpendMiner.new(("localhost", 32346))

    normal_miner.startup()
    time.sleep(1)
    vendor.startup()
    time.sleep(1)
    bad_spv.startup()
    time.sleep(1)
    bad_miner.startup()
    time.sleep(3)

    print(len(normal_miner.peers), len(vendor.peers), len(bad_spv.peers),
          len(bad_miner.peers))

    # First block
    bad_miner.create_block()
    time.sleep(1)
    print("Initial:")
    print(map_pubkey_to_name(bad_miner), end="\n\n")

    # Send transaction to bad SPV
    bad_miner.create_transaction(bad_spv.pubkey, 50)
    time.sleep(1)
    bad_miner.create_block()
    time.sleep(1)
    print("Bad Miner gives Bad SPV money to spend:")
    print(map_pubkey_to_name(bad_miner))

    # Bad SPV spend on vendor
    vendor_tx = bad_spv.create_transaction(vendor.pubkey, 50, "Buy")
    vtx_hash = algo.hash1(vendor_tx.to_json())
    time.sleep(1)
    blk = normal_miner.create_block()
    time.sleep(1)
    print("\nBad SPV use all coins to buy from Vendor:")
    print(map_pubkey_to_name(normal_miner))

    # Vendor verify transaction
    result = vendor.verify_transaction_proof(vtx_hash)
    print(f"\nVendor verify transaction: {result}")
    vendor.send_product(bad_spv.name)
    print(f"Current blockchain:\n{normal_miner.blockchain.endhash_clen_map}")

    # Bad Miner should mine faster at fork and reverse the transaction
    print(f"Bad SPV create double spend transaction to Bad Miner\n")
    bad_spv.create_transaction(bad_miner.pubkey, 50)

    # Exclude vendor transaction from bad Miner pool
    # bad_miner.exclude_transaction(vtx_hash)
    blk = bad_miner.create_block(blk.header["prev_hash"])
    print("Bad Miner creating fork (exclude vendor transaction):")
    print(normal_miner.blockchain.endhash_clen_map)

    # Extend fork such that vendor transaction is reversed
    bad_miner.create_block(algo.hash1_dic(blk.header))
    print("\nBad Miner further extend fork:")
    print(normal_miner.blockchain.endhash_clen_map)

    # Vendor try to verify again
    result = vendor.verify_transaction_proof(vtx_hash)
    print(f"\nVendor verify transaction: {result}")


if __name__ == "__main__":
    test()

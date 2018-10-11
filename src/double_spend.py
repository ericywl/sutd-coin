"""Double spending demonstration"""
import time

import algo
from trusted_server import TrustedServer
from spv_client import SPVClient
from miner import Miner


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


def main():
    """Main function"""
    TrustedServer()
    time.sleep(3)
    normal_miner = Miner.new(("localhost", 12345))
    vendor = SPVClient.new(("localhost", 22345))
    bad_spv = SPVClient.new(("localhost", 32345))
    bad_miner = Miner.new(("localhost", 32346))

    normal_miner.startup()
    vendor.startup()
    bad_spv.startup()
    bad_miner.startup()
    time.sleep(3)

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
    print("Bad Miner gives bad SPV money:")
    print(map_pubkey_to_name(bad_miner), end="\n\n")

    # Bad SPV spend on vendor
    vendor_tx = bad_spv.create_transaction(vendor.pubkey, 50)
    vtx_hash = algo.hash1(vendor_tx.to_json())
    time.sleep(1)
    normal_miner.create_block()
    time.sleep(1)
    print("Bad SPV spent all on vendor:")
    print(map_pubkey_to_name(normal_miner), end="\n\n")

    # Vendor verify transaction
    result = vendor.verify_transaction_proof(vtx_hash)
    print(f"Vendor verify transaction: {result}")
    print(f"Vendor send bad SPV product")

    # Bad Miner should mine faster at fork and reverse the transaction


if __name__ == "__main__":
    main()

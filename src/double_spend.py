"""Double spending demonstration"""
import time

import algo
from trusted_server import TrustedServer
from spv_client import SPVClient
from miner import Miner


class DoubleSpendMiner(Miner):
    """DoubleSpendMiner class"""



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
    print("Bad Miner gives bad SPV money:")
    print(map_pubkey_to_name(bad_miner))

    # Bad SPV spend on vendor
    vendor_tx = bad_spv.create_transaction(vendor.pubkey, 50, "Buy")
    vtx_hash = algo.hash1(vendor_tx.to_json())
    time.sleep(1)
    blk = normal_miner.create_block()
    time.sleep(1)
    print("\nBad SPV spent all on vendor:")
    print(map_pubkey_to_name(normal_miner))

    # Vendor verify transaction
    result = vendor.verify_transaction_proof(vtx_hash)
    print(f"\nVendor verify transaction: {result}")
    print(f"Vendor send bad SPV product\n")
    print(f"Current blockchain:\n{normal_miner.blockchain.endhash_clen_map}")

    # Bad Miner should mine faster at fork and reverse the transaction
    print(f"Bad SPV send supposedly spent money to bad Miner\n")
    bad_spv.create_transaction(bad_miner.pubkey, 50)

    # Remove vendor transaction from bad Miner pool (only temporary solution)
    bad_miner._all_transactions.remove(vendor_tx.to_json())
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
    main()

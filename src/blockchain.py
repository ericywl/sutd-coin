"""Blockchain class declaration file"""
import copy

from block import Block, generate_transactions
from transaction import Transaction
import algo


class Blockchain:
    """Blockchain class"""

    def __init__(self, hash_block_map, endhash_clen_map):
        # Dictionary of block hash to block
        self._hash_block_map = hash_block_map
        # Dictionary of last block hash to chain length
        self._endhash_clen_map = endhash_clen_map

    @classmethod
    def new(cls):
        """Create new Blockchain instance"""
        genesis = Block.get_genesis()
        genesis_hash = algo.hash1_dic(genesis.header)
        hash_block_map = {genesis_hash: genesis}
        # Keep track of end blocks and chain length
        endhash_clen_map = {genesis_hash: 0}
        return cls(hash_block_map, endhash_clen_map)

    def _get_chain_length(self, block):
        """Compute chain length from block (not including genesis)"""
        prev_hash = block.header["prev_hash"]
        chain_len = 0
        while prev_hash != Block.get_genesis().header["prev_hash"]:
            for blk in self._hash_block_map.values():
                if prev_hash == algo.hash1_dic(blk.header):
                    prev_hash = blk.header["prev_hash"]
                    chain_len += 1
                    break
        return chain_len

    def _get_chain_pow(self, block):
        """Compute proof of work of chain from last block"""
        prev_hash = block.header["prev_hash"]
        chain_pow = int(algo.hash1_dic(block.header), 16)
        while prev_hash != Block.get_genesis().header["prev_hash"]:
            for blk in self._hash_block_map.values():
                if prev_hash == algo.hash1_dic(blk.header):
                    prev_hash = blk.header["prev_hash"]
                    chain_pow += int(algo.hash1_dic(blk.header), 16)
                    break
        return chain_pow

    def add(self, block):
        """Add new block to chain"""
        # Verify block
        self.verify(block)
        curr_hash = algo.hash1_dic(block.header)
        prev_hash = block.header["prev_hash"]
        self._hash_block_map[curr_hash] = block
        # If the previous block is one of the last blocks,
        # replace the previous hash out with the current one
        # ie. make the current block be one of the last blocks,
        # and increment its chain length
        if prev_hash in self._endhash_clen_map.keys():
            chain_len = self._endhash_clen_map.pop(prev_hash)
            self._endhash_clen_map[curr_hash] = chain_len + 1
        # Else, compute the chain length by traversing backwards
        # and add the current block hash into dictionary
        else:
            self._endhash_clen_map[curr_hash] = self._get_chain_length(block)

    def _check_prev_exist(self, prev_hash):
        """Check block with prev_hash exist in list"""
        try:
            self._hash_block_map[prev_hash]
        except KeyError:
            return False
        else:
            return True

    def _check_prev_valid(self, prev_hash):
        """Check if previous block is valid"""
        prev_block = self._hash_block_map[prev_hash]
        return prev_block.validate() and prev_block.verify()

    def _check_timestamp(self, block):
        """Check timestamp larger than previous block timestamp"""
        prev_hash = block.header["prev_hash"]
        prev_block = self._hash_block_map[prev_hash]
        return block.header["timestamp"] > prev_block.header["timestamp"]

    def _check_trans_in_chain(self, block):
        """Check if block contains transactions that are already in chain"""
        prev_hash = block.header["prev_hash"]
        prev_block = self._hash_block_map[prev_hash]
        trans_set = set(self.get_transactions_by_fork(prev_block))
        blk_trans_set = set(block.transactions)
        num_b_transactions = len(blk_trans_set)
        remaining_transactions = blk_trans_set - trans_set
        return len(remaining_transactions) == num_b_transactions

    def verify(self, block):
        """Verify the block"""
        # Check previous block exist in blocks list
        if not self._check_prev_exist(block.header["prev_hash"]):
            raise Exception("Previous block does not exist.")
        # Check that previous block is valid
        if not self._check_prev_valid(block.header["prev_hash"]):
            raise Exception("Previous block is invalid.")
        # Check timestamp in block header
        if not self._check_timestamp(block):
            raise Exception("Invalid timestamp in block.")
        # Verify and validate block (self-contained)
        block.validate()
        block.verify()
        # Check transactions in blockchain not reused in block
        if not self._check_trans_in_chain(block):
            raise Exception("Transaction is already in the blockchain.")
        # Check nonce is not reused
        return True

    def _pow(self, block_hash):
        """Convenience function for lambda in resolve()"""
        return self._get_chain_pow(self._hash_block_map[block_hash])

    def _remove_fork_blocks(self, resolved_block_hash):
        """Remove all blocks in forks after resolving"""
        # Currently not used
        resolved_block = self._hash_block_map[resolved_block_hash]
        new_hash_block_map = {resolved_block_hash: resolved_block}
        prev_hash = resolved_block.header["prev_hash"]
        while prev_hash != Block.get_genesis().header["prev_hash"]:
            temp_blk = self._hash_block_map[prev_hash]
            new_hash_block_map[prev_hash] = temp_blk
            prev_hash = temp_blk.header["prev_hash"]
        self._endhash_clen_map = {
            resolved_block_hash: self._get_chain_length(resolved_block)
        }
        self._hash_block_map = new_hash_block_map

    def resolve(self):
        """Resolve potential forks in block and return last block"""
        # No forks case
        if len(self._endhash_clen_map) == 1:
            blk_hash = list(self._endhash_clen_map.keys())[0]
            return self._hash_block_map[blk_hash]
        # Get hashes of end-blocks with longest chain length
        longest_clen = max(self._endhash_clen_map.values())
        block_hashes = [
            k for k, v in self._endhash_clen_map.items() if v == longest_clen
        ]
        # Multiple chain with same length exist, use PoW to decide
        if len(block_hashes) != 1:
            block_hashes = [max(block_hashes, key=self._pow)]
        blk_hash = block_hashes[0]
        blk = self._hash_block_map[blk_hash]
        # Remove all blocks beloging to forks
        # self._remove_fork_blocks(blk)
        return blk

    def get_blocks_by_fork(self, last_block):
        """Obtain all blocks in a fork"""
        curr_block = last_block
        blocks = []
        while curr_block != Block.get_genesis():
            blocks.append(curr_block)
            prev_hash = curr_block.header["prev_hash"]
            curr_block = self._hash_block_map[prev_hash]
        return copy.deepcopy(list(blocks))

    def get_transactions_by_fork(self, last_block):
        """Obtain all transactions in a fork"""
        transaction_list = []
        for blk in self.get_blocks_by_fork(last_block):
            for t_json in blk.transactions:
                transaction_list.append(t_json)
        return transaction_list

    def get_balance_by_fork(self, last_block):
        """Obtain dictionary of balance in a fork"""
        balance = {}
        for blk in self.get_blocks_by_fork(last_block):
            for i in range(len(blk.transactions)):
                t_json = blk.transactions[i]
                converted_tx = Transaction.from_json(t_json)
                # Create accounts in balance if not exist
                if converted_tx.sender not in balance:
                    balance[converted_tx.sender] = 0
                if converted_tx.receiver not in balance:
                    balance[converted_tx.receiver] = 0
                # Coinbase transaction
                if i == 0 and converted_tx.sender == converted_tx.receiver:
                    balance[converted_tx.receiver] += converted_tx.amount
                # Normal transaction
                else:
                    balance[converted_tx.sender] -= converted_tx.amount
                    balance[converted_tx.receiver] += converted_tx.amount
        for _, amt in balance.items():
            if amt < 0:
                # If this happens it means that something is wrong with the
                # blockchain and should be discarded immediately
                raise Exception("Negative amount when computing balance.")
        return balance

    def get_transaction_proof_in_fork(self, tx_hash, last_block):
        """Get proof of transaction in a fork given transaction hash"""
        for blk in self.get_blocks_by_fork(last_block):
            proof = blk.get_transaction_proof(tx_hash)
            if proof is not None:
                return algo.hash1_dic(blk.header), proof
        return None

    @property
    def hash_block_map(self):
        """Return copy of block hash to block dictionary"""
        return copy.deepcopy(self._hash_block_map)

    @property
    def endhash_clen_map(self):
        """Return copy of last block hash to chain length dictionary"""
        return copy.deepcopy(self._endhash_clen_map)


def main():
    """Main function"""
    import threading
    blockchain = Blockchain.new()
    hashes = []
    # Generate 10 blocks with 10 transactions per block
    for i in range(7):
        print("Creating block {}...".format(i))
        b_transactions = generate_transactions(10)
        prev_block = blockchain.resolve()
        prev_hash = algo.hash1_dic(prev_block.header)
        new_block = Block.new(prev_hash, b_transactions, threading.Event())
        hashes.append(algo.hash1_dic(new_block.header))
        blockchain.add(new_block)
    # Introduce fork
    prev_hash = hashes[2]
    for i in range(4):
        print("Creating fork block {}...".format(i))
        f_transactions = generate_transactions(10)
        fork_block = Block.new(prev_hash, f_transactions, threading.Event())
        blockchain.add(fork_block)
        prev_hash = algo.hash1_dic(fork_block.header)
    # Try to resolve
    print("Blockchain last blocks: {}".format(blockchain.endhash_clen_map))
    # print("Pre-resolve: " + str(blockchain.endhash_clen_map))
    last_blk = blockchain.resolve()
    # print("Post-resolve: " + str(blockchain.endhash_clen_map))
    print("Last block hash: {}".format(algo.hash1_dic(last_blk.header)))


if __name__ == "__main__":
    main()

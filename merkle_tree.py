import algo

import math, hashlib
import time, random, string
from collections import deque

class MerkleTree:
    class Node:
        def __init__(self, id_no, left, right, hash_val):
            self.id = id_no
            self.left = left
            self.right = right
            self.hash_val = hash_val
            self.parent = None
            self.height = left.height + 1 if left != None else 0

        # Return id string for test purposes
        def __str__(self):
            return str(self.id)

    def __init__(self, items=[]):
        self.is_built = False
        self.leaves_map = self._hash_items(items)
        self.tree_height \
            = math.ceil(math.log(len(items), 2)) if len(items) > 0 else 0
        self.root = None
        self.build()

    # Create hash table from list of items
    def _hash_items(self, items):
        # Items should be JSON strings
        res = {}
        for i in range(len(items)):
            item = items[i]
            item_hash = algo.hash1(item)
            item_node = self.Node(i + 1, None, None, item_hash)
            res[item] = item_node
        return res

    # Hash the concatenation of hashes in left and right node
    def _concat_hash(self, left, right):
        return algo.hash1(left.hash_val + right.hash_val)

    # Add entries to tree
    def add(self, entry):
        entry_hash = algo.hash1(entry)
        entry_node = self.Node(len(self.leaves_map) + 1, None, None, entry_hash)
        self.leaves_map[entry] = entry_node
        self.tree_height = math.ceil(math.log(len(self.leaves_map), 2))
        self.root = None
        self.is_built = False

    # Build tree computing new root
    def build(self):
        leaves = list(self.leaves_map.values())
        leaves_len = len(leaves)
        if leaves_len <= 0:
            self.is_built = True
            return
        for n in leaves:
            n.parent = None
            n.height = 0
        dq = deque(leaves)
        index = leaves_len + 1
        if len(dq) == 1:
            self.root = dq[0]
        while self.root == None:
            if len(dq) >= 2 and dq[0].height == dq[1].height:
                # Pop first two nodes 
                left = dq.popleft()
                right = dq.popleft()
                # Create parent node
                node_hash = self._concat_hash(left, right)
                node = self.Node(index, left, right, node_hash)
                index += 1
                left.parent = node
                right.parent = node
                if node.height == self.tree_height:
                    self.root = node
                dq.append(node)
            else:
                # Elevate node in tree and move node to back of deque
                node = dq.popleft()
                node.height += 1
                dq.append(node)
        self.is_built = True

    # Get membership proof for entry
    def get_proof(self, entry):
        if not self.is_built:
            self.build()
        proof = []
        node = self.leaves_map[entry]
        while node != self.root:
            parent = node.parent
            if parent.left == node:
                proof.append((parent.right.hash_val, "right"))
            else:
                proof.append((parent.left.hash_val, "left"))
            node = parent
        return proof

    # Return the current root
    def get_root(self):
        if not self.is_built:
            self.build()
        return self.root.hash_val if self.root else None


# Verifies proof for entry and given root. Returns boolean.
def verify_proof(entry, proof, root):
    temp = algo.hash1(entry)
    for p, d in proof:
        if d == "right":
            inp = temp + p
        elif d == "left":
            inp = p + temp
        else:
            raise Exception("Invalid direction in proofs.")
        temp = algo.hash1(inp)
    return temp == root


if __name__ == "__main__":
    from transaction import *
    from block import generate_transactions
    chars = string.ascii_letters + string.digits
    items = []
    tree = MerkleTree()
    transactions = generate_transactions(random.randint(10, 100))
    for t_json in transactions:
        tree.add(t_json)
        items.append(t_json)
    root = tree.get_root()
    entry = items[random.randint(0, len(items)-1)]
    proof = tree.get_proof(entry)
    print("Root: " + root)
    print("Proof: " + str(proof))
    ver = verify_proof(entry, proof, root)
    print("Verify: " + ("Success" if ver else "Failure"))

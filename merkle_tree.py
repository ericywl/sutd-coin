import math, hashlib
import time, random, string
from collections import deque
from transaction import *

class MerkleTree:
    class Node:
        def __init__(self, id_no, left, right, hash_val):
            self.id = id_no
            self.left = left
            self.right = right
            self.hash_val = hash_val
            self.parent = None
            self.height = left.height + 1 if left != None else 0

        def __str__(self):
            # Return id string for test purposes
            return str(self.id)

    def __init__(self, items=[]):
        if items == None or len(items) <= 0:
            self.is_built = True
            self.leaves_map = {}
            self.tree_height = 0
            self.root = None
        else:
            self.is_built = False
            self.leaves_map = self._hash_items(items)
            self.tree_height = math.ceil(math.log(len(items), 2))
            self.root = None
            self.build()

    def _hash_items(self, items):
        # Create hash table from list of items
        # Items should be JSON strings
        res = {}
        for i in range(len(items)):
            item = items[i]
            item_hash = hashlib.sha256(item.encode()).hexdigest()
            item_node = self.Node(i + 1, None, None, item_hash)
            res[item] = item_node
        return res

    def _concat_hash(self, left, right):
        # Hash the concatenation of hashes in left and right node
        return hashlib.sha256((left.hash_val + right.hash_val).encode()).hexdigest()

    def add(self, entry):
        # Add entries to tree
        entry_hash = hashlib.sha256(entry.encode()).hexdigest()
        entry_node = self.Node(len(self.leaves_map) + 1, None, None, entry_hash)
        self.leaves_map[entry] = entry_node
        self.tree_height = math.ceil(math.log(len(self.leaves_map), 2))
        self.root = None
        self.is_built = False

    def build(self):
        # Build tree computing new root
        leaves = list(self.leaves_map.values())
        for n in leaves:
            n.parent = None
            n.height = 0
        dq = deque(leaves)
        index = len(leaves) + 1
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

    def get_proof(self, entry):
        # Get membership proof for entry
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

    def get_root(self):
        # Return the current root
        if not self.is_built:
            self.build()
        return self.root.hash_val if self.root else None


def verify_proof(entry, proof, root):
    # Verifies proof for entry and given root. Returns boolean.
    temp = hashlib.sha256(entry.encode()).hexdigest()
    for p, d in proof:
        if d == "right":
            inp = temp + p
        elif d == "left":
            inp = p + temp
        else:
            raise Exception("Invalid direction in proofs.")
        temp = hashlib.sha256(inp.encode()).hexdigest()
    return temp == root


if __name__ == "__main__":
    chars = string.ascii_letters + string.digits
    items = []
    tree = MerkleTree()
    for i in range(random.randint(100, 1000)):
        sender_sk = ecdsa.SigningKey.generate()
        sender_vk = sender_sk.get_verifying_key()
        receiver_sk = ecdsa.SigningKey.generate()
        receiver_vk = receiver_sk.get_verifying_key()
        t = Transaction.new(sender_vk, receiver_vk, i, sender_sk, "hello world")
        tree.add(t.to_json())
        items.append(t.to_json())
    root = tree.get_root()
    entry = items[random.randint(0, len(items)-1)]
    proof = tree.get_proof(entry)
    print("Root: " + root)
    print("Proof: " + str(proof))
    ver = verify_proof(entry, proof, root)
    print("Verify: " + ("Success" if ver else "Failure"))

import hashlib, time, random, os
STR_LIM = 100

def trunc_hash(n, inp):
    # Hash and truncate
    h = hashlib.sha512(inp).digest()
    i = n // 8
    return h[0:i]

def collision(n):
    # Brute force hash collision
    # Use dictionary to store hashes
    print("Computing collision for {0} bits: ".format(n), end="")
    dic = {}
    start = time.time()
    while True:
        # Generate random binary
        b = os.urandom(random.randint(1, STR_LIM))
        if b not in dic.values():
            h = trunc_hash(n, b)
            if h not in dic.keys():
                dic[h] = b
            else:
                elapsed = time.time() - start
                # print("{0} and {1} collide.".format(b, dic[h]))
                print("{0}s.".format(elapsed))
                return

def pre_image(n):
    num = n // 8
    print("Computing pre-image for {0}: ".format("\\x00" * num), end="")
    # Get binary of zeroes
    prem = b"\x00" * num
    start = time.time()
    while True:
        # Generate random binary
        b = os.urandom(random.randint(1, STR_LIM))
        if trunc_hash(n, b) == prem:
            elapsed = time.time() - start
            # print("{0} produces collision".format(b))
            print("{0}s.".format(elapsed))
            return


if __name__ == "__main__":
    for i in range(8, 41, 8):
        collision(i)
    for i in range(8, 41, 8):
        pre_image(i)


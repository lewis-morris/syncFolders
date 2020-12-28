import random
import secrets
import os
import time
def write_files(path):

    for i in range(10):
        new_dir = path + str(random.randint(0,1000))
        os.makedirs(new_dir)
        for y in range(random.randint(0,10)):
            create_file(new_dir)
            time.sleep(0.1)
def create_file(path):

    with open(path + "/" + str(random.randint(0,10000)) + ".txt", "w") as f:
        f.writelines(secrets.token_hex(128))


if __name__ == "__main__":
    write_files("source/")
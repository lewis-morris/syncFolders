import hashlib
import os
import secrets

def create_text_file(path,length=128,append=False):
    with open(path , "w" if append else "a+") as f:
        f.writelines(secrets.token_hex(length))

def hash_file(path):
    # BUF_SIZE is totally arbitrary, change for your app!
    BUF_SIZE = 65536  # lets read stuff in 64kb chunks!
    md5 = hashlib.md5()
    with open(path, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            md5.update(data)

    return md5.hexdigest()


def add_metadata_to_file(path, data):
    os.setxattr(path, 'user.data', bytes(data, 'utf-8'))


def get_metadata(path):
    try:
        os.getxattr(path, 'user.data').decode("utf-8")
    except OSError:
        return None

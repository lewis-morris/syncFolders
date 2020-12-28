import datetime
import pathlib
import sys
import hashlib
import os
from shutil import copyfile


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


def list_dir_files_with_hash(path, file_listing=None, recursive_folders=True):

    #if no file listing dic then create
    if not file_listing:
        file_listing = {}

    #walk all files/dirs in path
    for file in os.listdir(path):
        #loop files
        rel_path = os.path.relpath(path + "/" + file)

        #get extra details
        fl = pathlib.Path(rel_path)
        date_modified = datetime.datetime.fromtimestamp(fl.stat().st_mtime)
        file_size = fl.stat().st_size

        # add file to listing
        if os.path.isdir(rel_path):
            type = "folder"
            hash = None
        else:
            type = "files"
            hash = hash_file(rel_path)

        #add to listing
        file_listing[rel_path] = [hash, date_modified, file_size, type]

        #if folders recursively loop contents
        if type == "folder":
            file_listing = list_dir_files_with_hash(rel_path, file_listing, recursive_folders)

    return file_listing

def sync_folders(source, dest):

    source_files = list_dir_files_with_hash(source)
    source_files = {k.replace(source,""):v for k,v in source_files.items()}
    dest_files = list_dir_files_with_hash(dest)
    dest_files = {k.replace(dest, ""): v for k, v in dest_files.items()}

    pass


#     check_missing(source_files, dest_files,source,dest )
#     check_needs_deleting(source_files, dest_files,source,dest)
#
# def check_missing(source_items,dest_items,source_dir,dest_dir):
#
#     missing = {k:v for k,v in source_items.items() if k not in dest_items.keys()}
#
#     folders = [k for k,v in missing.items() if v[1] == "folder"]
#     files = [k for k, v in missing.items() if not v[1] in folders]
#
#     _ = [os.mkdir(dest_dir + folder) for folder in folders]
#     _ = [copyfile(source_dir + file , dest_dir + file) for file in files]
#
#
# def check_needs_deleting(source_items, dest_items, source_dir, dest_dir):
#
#     deleting = {k: v for k, v in dest_items.items() if k not in source_items.keys()}
#     _ = [os.remove(dest_dir + "/" + fl) for fl in deleting]
#

if __name__ == "__main__":

    while True:
        sync_folders("source/","dest/")

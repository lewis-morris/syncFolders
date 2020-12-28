import copy
import datetime
import pathlib
import shutil
import sys
import hashlib
import os
import time
from shutil import copy2

from dirhash import dirhash


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


class Syncer:

    def __init__(self, sourcePath, destPath):

        self.first_run = False

        self.sourcePath = sourcePath
        self.destPath = destPath

        self.dest_files = None
        self.last_dest_files = None

        self.source_files = None
        self.last_source_files = None

    def _list_dir_files_with_hash(self, path, file_listing=None, recursive_folders=True):

        # if no file listing dic then create
        if not file_listing:
            file_listing = []

        # walk all files/dirs in path
        for file in os.listdir(path):

            try:
                # loop files
                rel_path = os.path.relpath(path + "/" + file)

                # add file to listing
                if os.path.isdir(rel_path):
                    type = "folder"
                    try:
                        hash = dirhash(rel_path, "md5")
                    except:
                        hash = None
                else:
                    type = "files"
                    hash = hash_file(rel_path)

                # add to listing
                file_listing.append([rel_path, hash, type])

                # if folders recursively loop contents
                if type == "folder":
                    file_listing = self._list_dir_files_with_hash(rel_path, file_listing, recursive_folders)

            except FileNotFoundError:
                pass

        return file_listing

    def _get_files(self):

        self.last_source_files = copy.deepcopy(self.source_files)
        source_files = self._list_dir_files_with_hash(self.sourcePath)
        self.source_files = sorted([[v[0].replace(self.sourcePath, "")] + v[1:] for v in source_files], key= lambda x:x[2], reverse=True)

        self.last_dest_files = copy.deepcopy(self.dest_files)
        dest_files = self._list_dir_files_with_hash(self.destPath)
        self.dest_files = sorted([[v[0].replace(self.destPath, "")] + v[1:] for v in dest_files], key= lambda x:x[2], reverse=True)


    def copy_file_or_dir(self, fl):

        if fl[2] == "folder":
            if not os.path.isdir(self.destPath + fl[0]):
                os.mkdir(self.destPath + fl[0])
        else:
            try:
                copy2(self.sourcePath + fl[0], self.destPath + fl[0])
            except FileNotFoundError:
                #fixes temp files being tried to copy
                pass

    def check_dates(self, fl):

        if fl[2] != "folder":
            source_fl = pathlib.Path(self.sourcePath + fl[0])
            dest_fl = pathlib.Path(self.sourcePath + fl[0])
            dest_fl_lst = self.dest_files[self.dest_files.index(fl)]
            hash_match = fl[1] == dest_fl_lst[1]
            if not hash_match:
                if source_fl.stat().st_mtime > dest_fl.stat().st_mtime:
                    copy2(self.sourcePath + fl[0], self.destPath + fl[0])
                elif source_fl.stat().st_mtime < dest_fl.stat().st_mtime:
                    copy2(self.destPath + fl[0], self.sourcePath + fl[0])

    def rename_hash(self,fl,hashed):

        os.rename(self.destPath + hashed[0], self.destPath + fl[0])

    def check_changes(self):

        for fl in self.source_files:
            if not fl in self.dest_files:
                # if exists but not same file name
                hashed = self._find_hash(fl[1])
                if hashed and hashed[1] != None:
                    self.rename_hash(fl, hashed)
                # else copy file over as it doesnt exist
                else:
                    self.copy_file_or_dir(fl)
            if fl in self.dest_files:
                self.check_dates(fl)

    def reverse_folders(self):

        self.source_files, self.dest_files = self.dest_files, self.source_files
        self.last_dest_files, self.last_source_files = self.last_source_files, self.last_dest_files
        self.sourcePath, self.destPath = self.destPath, self.sourcePath

    def check_deleted(self):

        for fl in self.last_source_files:
            if not fl[0] in [x[0] for x in self.source_files] and not self._find_hash(fl[1], False):
                try:
                    self.dest_files.remove(fl)
                except ValueError:
                    pass

                try:
                    os.remove(self.destPath + fl[0])
                except FileNotFoundError:
                    #fixes temp files being removed that no longer exist
                    pass


    def _init_sync(self):

        self._get_files()

        for x in range(2):
            self.check_changes()
            self.reverse_folders()

        self.first_run = True

    def sync(self):

        if not self.first_run:
            self._init_sync()

        self._get_files()

        if self.source_files != self.last_source_files:
            self.check_changes()
            self.check_deleted()

        if self.dest_files != self.last_dest_files:
            self.reverse_folders()
            self.check_changes()
            self.check_deleted()

    def _find_hash(self, hash, dest=True):
        if dest:
            files = self.dest_files
        else:
            files = self.source_files

        for file in files:
            if file[1] == hash:
                return file


if __name__ == "__main__":

    sync = Syncer("source/", "dest/")

    while True:
        sync.sync()

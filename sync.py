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
import logging

logging.basicConfig(filename="log.log")

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

class File:

    def __init__(self,path,source):
        self.path = path
        self.source = source
        self.type = "folder" if os.path.isdir(self.source + self.path) else "file"
        self.full_path = self.source + self.path
        if self.type == "folder":
            try:
                self.hash = dirhash(self.full_path, "md5")
            except:
                self.hash = None
        else:
            self.hash = hash_file(self.full_path)

        fl = pathlib.Path(self.full_path)
        self.modified = datetime.datetime.fromtimestamp(fl.stat().st_mtime)

    def __eq__(self,other):
        return self.path == other.path and self.hash == other.hash

    def __gt__(self,other):
        return self.modified > other.modified

    def is_hash_match(self,other):
        return self.hash == other.hash

    def __hash__(self):
        return hash(self.full_path + self.hash)

    def exists(self):
        return os.path.isfile(self.full_path) if self.type == "file" else os.path.isdir(self.fullpath)

    def delete_self(self):
        try:
            os.remove(self.full_path)
        except:
            #some reason
            pass

    def make_changes(self,other):
        pass

    def rename(self, fl):
        """ used to rename file """
        if self.exists():
            os.rename(self.full_path, self.source + fl.path)
            self.path = fl.path
            self.full_path = self.source + self.path

    def copy(self, locaiton, fl=None):
        """ used self to  missing file location / over older version """
        if self.exists():
            if fl:
                location = fl.full_path
            else:
                location = locaiton + self.path
            shutil.copyfile(self.full_path, location)

class Syncer:

    def __init__(self, sourcePath, destPath):

        self.first_run = False

        self.sourcePath = sourcePath
        self.destPath = destPath

        self.dest_files = None
        self.last_dest_files = None

        self.source_files = None
        self.last_source_files = None

        self.logger = logging.getLogger("log")
        self.logger.setLevel(logging.DEBUG)
        self._fh = logging.FileHandler("spam.log")
        self._ch = logging.StreamHandler()
        self._fh.setLevel(logging.DEBUG)
        self._ch.setLevel(logging.DEBUG)
        self._formatter = logging.Formatter('%(asctime)s - %(message)s')
        self._fh.setFormatter(self._formatter )
        self._ch.setFormatter(self._formatter )
        self.logger.addHandler(self._fh)
        self.logger.addHandler(self._ch)

        self.file_list = []

    def _list_dir_files_with_hash(self, path, file_listing=None, recursive_folders=True,source=""):

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
                self.file_list.append(File(rel_path.replace(source,""), source))
                # if folders recursively loop contents
                if type == "folder":
                    file_listing = self._list_dir_files_with_hash(rel_path, file_listing, recursive_folders, source)

            except FileNotFoundError:
                pass

        return file_listing

    def _get_files(self):

        self.last_source_files = copy.deepcopy(self.source_files)
        source_files = self._list_dir_files_with_hash(self.sourcePath,source=self.sourcePath)
        self.source_files = sorted([[v[0].replace(self.sourcePath, "")] + v[1:] for v in source_files], key= lambda x:x[2], reverse=True)

        self.last_dest_files = copy.deepcopy(self.dest_files)
        dest_files = self._list_dir_files_with_hash(self.destPath,source=self.destPath)
        self.dest_files = sorted([[v[0].replace(self.destPath, "")] + v[1:] for v in dest_files], key= lambda x:x[2], reverse=True)


    def copy_file_or_dir(self, fl):

        if fl[2] == "folder":
            if not os.path.isdir(self.destPath + fl[0]):
                self.logger.info(f"Making missing directory (copy) to {self.destPath + fl[0]} found in {self.sourcePath + fl[0]} ")
                os.mkdir(self.destPath + fl[0])
        else:
            try:
                self.check_newer_and_copy(fl)
            except FileNotFoundError:
                #fixes temp files being tried to copy
                pass

    def check_newer_and_copy(self,fl):

        #todo make this steamlined
        source_fl = pathlib.Path(self.sourcePath + fl[0])
        dest_fl = pathlib.Path(self.destPath + fl[0])
        if dest_fl.is_file():
            if source_fl.stat().st_mtime > dest_fl.stat().st_mtime:
                self.logger.info(
                    f"Copying file (as origin is newer) to {self.destPath + fl[0]} from {self.sourcePath + fl[0]} ")
                copy2(self.sourcePath + fl[0], self.destPath + fl[0])
            elif source_fl.stat().st_mtime < dest_fl.stat().st_mtime:
                self.logger.info(
                    f"Copying file (as origin is newer) to {self.sourcePath + fl[0]} from {self.destPath + fl[0]} ")
                copy2(self.destPath + fl[0], self.sourcePath + fl[0])
        else:
            self.logger.info(
                f"Copying file (as dest is missing) to {self.sourcePath + fl[0]} from {self.destPath + fl[0]} ")
            copy2(self.sourcePath + fl[0], self.destPath + fl[0])

    def check_dates(self, fl):
        #todo does this need to be here. If the dates are different but the hash matches when its the same file.
        # if it doesnt match then it should be picked up elsewhere.
        if fl[2] != "folder":
            source_fl = pathlib.Path(self.sourcePath + fl[0])
            dest_fl = pathlib.Path(self.destPath + fl[0])
            dest_fl_lst = self.dest_files[self.dest_files.index(fl)]
            hash_match = fl[1] == dest_fl_lst[1]
            if not hash_match:


                if source_fl.stat().st_mtime > dest_fl.stat().st_mtime:
                    self.logger.info(
                        f"Copying file to {self.destPath + fl[0]} from {self.sourcePath + fl[0]} as file is newer ")
                    copy2(self.sourcePath + fl[0], self.destPath + fl[0])
                elif source_fl.stat().st_mtime < dest_fl.stat().st_mtime:
                    self.logger.info(
                        f"Copying file to {self.sourcePath + fl[0]} from {self.destPath + fl[0]} as file is newer ")
                    copy2(self.destPath + fl[0], self.sourcePath + fl[0])
            else:
                pass


    def rename_hash(self,fl,hashed):
        #rename file

        self.logger.info(
            f"Renaming file as hashes match renamedFile {self.sourcePath + fl[0]}  old file {self.destPath + hashed[0]} new renamed {self.destPath + fl[0]}")

        os.rename(self.destPath + hashed[0], self.destPath + fl[0])
        #update the destination list file name
        hashed[0] = fl[0]

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
            elif fl in self.dest_files:
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
                    self.logger.info(
                        f"Removing file from dest folder as no longer exists in source {self.destPath + fl[0]}")
                    os.remove(self.destPath + fl[0])
                except FileNotFoundError:
                    #fixes temp files being removed that no longer exist
                    pass
                except IsADirectoryError:
                    #not sure yet
                    pass
                finally:
                    self.logger.error(
                        f"Removing file error {self.destPath + fl[0]}")



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

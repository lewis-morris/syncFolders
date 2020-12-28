import copy
import datetime
import pathlib
import shutil
import sys
import hashlib
import os
import time
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

                # get extra details
#                
#                
##                date_modified = fl.stat().st_mtime
#                file_size = fl.stat().st_size

                #add file to listing
                if os.path.isdir(rel_path):
                    type = "folder"
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

        source_files = self._list_dir_files_with_hash(self.sourcePath)
        self.source_files = [[v[0].replace(self.sourcePath, "")] + v[1:] for v in source_files]
        self.last_source_files = copy.deepcopy(self.source_files)

        dest_files = self._list_dir_files_with_hash(self.destPath)
        self.dest_files = [[v[0].replace(self.destPath, "")] + v[1:] for v in dest_files]
        self.last_dest_files = copy.deepcopy(self.dest_files)
    
    def copy_file_or_dir(self,fl):
        
        if fl[2] == "folder":
            os.mkdir(self.destPath + fl[0])
        else:
            copyfile(self.sourcePath + fl[0], self.destPath + fl[0])
            
    def check_dates(self,fl):
        
        if fl[2] != "folder":
            source_fl = pathlib.Path(self.sourcePath + fl[0])
            dest_fl = pathlib.Path(self.sourcePath + fl[0])
            dest_fl_lst = self.dest_files[self.dest_files.index(fl)]
            hash_match = fl[1] == dest_fl_lst[1]
            if not hash_match:
                if source_fl.stat().st_mtime > dest_fl.stat().st_mtime :
                    copyfile(copyfile(self.sourcePath + fl[0], self.destPath + fl[0]))
                elif source_fl.stat().st_mtime < dest_fl.stat().st_mtime:
                    copyfile(copyfile(self.destPath + fl[0], self.sourcePath + fl[0]))
                        
            
    def check_changes(self):
        
        for fl in self.source_files:
            if not fl in self.dest_files:
                # if exists but not same file name
                if self._find_hash(fl[1]):
                    pass
                #else copy file over as it doesnt exist 
                else:
                    self.copy_file_or_dir(fl)
            if fl in self.dest_files:
                self.check_dates(fl, )
                
                
#    def _equlibiem_check(self):
#        
#        self._get_files()
#        
#        missing_dest = sorted([x for x in self.source_files if x not in self.dest_files], key=lambda x:x[4], reverse=True)
#        missing_source = sorted([x for x in self.dest_files if x not in self.source_files], key=lambda x:x[4], reverse=True)
#        self._equlibirem_fix(missing_dest, missing_source)
#    
#    def _equlibirem_fix(self, source_list, dest_list):
#        
#        
#        dest = [self.destPath, self.sourcePath]
#        file_list = [[self.dest_files,self.last_dest_files],[self.source_files,self.last_source_files]]
#        for folder in [dest_list, source_list]:#
#            
#            dest = dest[::-1]
#            file_list = file_list[::-1]
#            
#            for file in folder:
#                if file[4] == "folder":
#                    os.mkdir(dest[1] + file[0])
#                else:
#                    copyfile(dest[0] + file[0], dest[1] + file[0])
#                file_list[1][0].append(file)
#                file_list[1][1].append(file)
                
    def reverse_folders(self):
        self.source_files, self.dest_files = self.dest_files, self.source_files
        self.last_dest_files, self.last_source_files = self.last_source_files, self.last_dest_files
        self.sourcePath, self.destPath = self.destPath, self.sourcePath
    def sync(self):
        
        self._get_files()
        self.check_changes()
        self.reverse_folders()
        self.check_changes()
        
#    def _check_removes(self):
#        # check if a file existed in the last run but not this one (i.e its been deleted)
#
#        for k, v in self.old_source_files.items():
#            # if key doesnt exist and there is no hash thats the same its been deleted
#            if k not in self.last_source_files.keys() and not self._find_hash(v[0]):
#                # if its in the opposite folder then remove from that folder
#                if k in self.dest_files:
#                    del self.dest_files[k]
#                if k in self.source_files:
#                    del self.source_files[k]
#                if os.path.isfile(self.destPath + k):
#                    os.remove(self.destPath + k)
#                if os.path.isfile(self.sourcePath + k):
#                    os.remove(self.sourcePath + k)
#
#    def _sync_same_files(self):
#        """sync same file name changes to opposite folder"""
#        done = set()
#        for k, v in self.source_files.items():
#
#            # if file found
#            if k in self.dest_files:
#                dest_file = self.dest_files[k]
#                # if date modified greater in dest or file size
#                if dest_file[1] > v[1] and dest_file[3] != "folder" and not self._find_hash(v[0]):
#                    #self.log += "\n" + f"{k} updated in {self.sourcePath}"
#                    copyfile(self.destPath + k, self.sourcePath + k)
#                    done.add(k)
#                    del self.dest_files[k]
#                # if date modified less in dest or file size
#                elif dest_file[1] < v[1] and dest_file[3] != "folder" and not self._find_hash(v[0]):
#                    #self.log += "\n" + f"{k} updated in {self.destPath}"
#                    copyfile(self.sourcePath + k, self.destPath + k)
#                    done.add(k)
#                    del self.dest_files[k]
#                # remove done from the dictionary
#
#        # rmeove done items.
#        self._remove_done(done)

    def _find_hash(self, hash):

        for file in self.dest_files:
            if file[1] == hash:
                return file
    #
#    def _remove_done(self, done, source=True):
#        if source == True:
#            for itm in done:
#                del self.source_files[itm]
#
#    def _sync_deleted(self):
#
#        if self.old_source_files:
#            self._check_removes()
#
#    def _sync_missing(self):
#
#        self._do_missing()
#
#    def _do_missing(self):
#        """sync files that are missing"""
#        done = set()
#        for k, v in self.source_files.items():
#            if k not in self.dest_files.keys():
#                same_hash = self._find_hash(v[0])
#                if same_hash:
#                    os.rename(self.destPath + same_hash[0], self.destPath + k)
#                else:
#                    if v[3] == "folder":
#                        os.mkdir(self.destPath + k)
#                    else:
#                        copyfile(self.sourcePath + k, self.destPath + k)
#                    done.add(k)
#
#        self._remove_done(done)
#
#    def _switch_direction(self):
#
#        self.source_files, self.dest_files = self.dest_files, self.source_files
#        self.destPath, self.sourcePath = self.sourcePath, self.destPath
#        self.old_source_files, self.old_dest_files = self.old_dest_files, self.old_source_files
#        self.last_source_files, self.last_dest_files = self.last_dest_files, self.last_source_files
#
#    def reset_old_and_last(self):
#
#        self.old_source_files = copy.deepcopy(self.last_source_files)
#        self.old_dest_files = copy.deepcopy(self.last_dest_files)
#
#    def _are_dictionaries_the_same(self,dic,dic_second):
#        if not dic is None:
#            return {k: dic[k] for k in set(dic) - set(dic_second)} == {}
#        else:
#            return True
#
#    def init_sync(self):
#
#        self._get_files()
#        self.sync(False)
#        self._switch_direction()
#        self.sync(False)
#        self._get_files()
#
#    def sync(self, get_files=True):
#
#        if get_files:
#            self.reset_old_and_last()
#            self._get_files()
#
#        run = False
#
#        #if there is a change in the source files then run
#        if self.old_source_files != self.last_source_files:
#            run = True
#        #if there is a change in the dest files switch and run
#        elif self.old_dest_files != self.last_dest_files:
#            self._switch_direction()
#            run = True
#
#        if run:
#            self.first_run = True
#            self._sync_deleted()
#            self._sync_missing()
#            self._sync_same_files()
#
#        run = False

if __name__ == "__main__":

    sync = Syncer("source/", "dest/")

    while True:
        sync.sync()
        time.sleep(0.2)
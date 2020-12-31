import copy
import datetime
import pathlib
import secrets
import shutil
import os
import string
import time
from dataclasses import dataclass
from dirhash import dirhash

from functions import hash_file

class _BaseFile:

    def __init__(self, file_name, folder):

        self._file_name = file_name
        self.parent_folder = folder
        self._fl = pathlib.Path(self.full_path)

        if self.metadata is None:
            self.add_metadata(self)

    @staticmethod
    def add_metadata(cls, data=None):
        """ add meta data to file"""
        if data is None:
            #generate random key to file if not supplied
            alphabet = string.ascii_letters + string.digits
            data = ''.join(secrets.choice(alphabet) for i in range(15))
        if type(cls) is not str:
            cls = cls.full_path

        os.setxattr(cls, 'user.data', bytes(data, 'utf-8'))

    @property
    def metadata(self):
        """ get met"""
        try:
            return os.getxattr(self.full_path, 'user.data').decode("utf-8")
        except OSError:
            return None

    def exists(self):
        """ does this file actually exist """
        return os.path.isfile(self.full_path) if type(self) == File else os.path.isdir(self.full_path)

    def delete_self(self):
        """ used to delete the file from store """
        try:
            if type(self) is File:
                os.remove(self.full_path)
            else:
                os.rmdir(self.full_path)
        except:
            # some reason
            pass

    def __eq__(self, other):
        """ files match if their metadata, path and hash match"""
        meta_ok = self.metadata == other.metadata
        path_ok = self.path == other.path

        if not self.hash is None:
            hash_ok = self.hash == other.hash
        else:
            return path_ok

        return meta_ok and path_ok and hash_ok

    def __gt__(self, other):
        return self.modified > other.modified

    def __hash__(self):
        return hash(self.full_path + self.hash)

    @property
    def file_name(self):
        return self._file_name

    @file_name.setter
    def file_name(self,name):
        self._file_name = name

    @property
    def full_path(self):
        path = self.source + "/" + self.file_name
        if path[0] == "/":
            path = path[1:]
        return path

    @property
    def path(self):

        path = self.full_path
        root = self._get_root()
        find_root = path.find(root)
        return path[find_root+len(root):]

    @property
    def source_no_root(self):

        path = self.full_path
        root = self._get_root()
        find_root = path.find(root)
        return self.source[find_root+len(root):]

    @property
    def source(self):
        if not self.parent_folder:
            return ""
        else:
            lst = self._get_source_list()
            lst.reverse()
            return "/".join(lst)

    def _get_root(self):
        if self.parent_folder:
            ans = self.parent_folder._get_root()
        else:
            return self.file_name
        return ans

    def _get_source_list(self, lst=None):
        """ used to recursively get the parent folder names"""
        if lst == None:
            lst = []
        if self.parent_folder:
            lst.append(self.parent_folder._file_name.replace("/",""))
            lst = self.parent_folder._get_source_list(lst)

        return lst

    @property
    def modified(self):
        return datetime.datetime.fromtimestamp(self._fl.stat().st_mtime)

    @property
    def accessed(self):
        return datetime.datetime.fromtimestamp(self._fl.stat().st_atime)

    @property
    def size(self):
        #get file size and convert to human readable

        size = self._fl.stat().st_size

        gb = format(round(size  / 1024 / 1024 / 1024, 3),".2f")

        if gb[0] != "0":
            return gb + " gb"

        mb = format(round(size  / 1024 / 1024 , 3),".2f")
        if mb[0] != "0":
            return mb + " mb"

        kb = format(round(size  / 1024 , 3),".2f")
        if kb[0] != "0":
            return kb + " kb"

        else:
            return f"{size} bytes"


        return f"{(round(self._fl.stat().st_size / 1e+6,3)):.2f} MB"

    def is_hash_match(self, other):
        """ used to check if another file is a hash match """
        return self.hash == other.hash

    def rename_self_as_input(self, fl):
        """ used to rename file """
        if self.exists():
            os.rename(self.full_path, self.source + "/" + fl.file_name)
            self.file_name = fl.file_name
            self.hash = fl.hash

    def copy(self, location=None, fl=None):
        """ used self to  missing file location / over older version """
        if self.exists():
            if fl:
                # if passed file is not newer then overwrite
                if self.modified > fl.modified:
                    location = fl.full_path
                    fl.file_name = self.file_name
                    fl.hash = self.hash
                    self.do_copy(location, fl)
                elif self.modified < fl.modified:
                    # if not then do the other way around
                    fl.copy(fl=self)
                else:
                    pass
            else:
                location = location + self.path
                self.do_copy(location)

            # do copy

class File(_BaseFile):

    def __init__(self, path, folder):

        super().__init__(path, folder)

        self.folder: Folder = folder
        self.hash = self._get_hash()

    def _get_hash(self):
        return hash_file(self.full_path)

    def do_copy(self, location=None, fl=None):
        """ copy file, if the destination path is already a file, then its an overwrite (modified file) and
            needs to have the hash of the source file added to the destination file
        """
        #check if needs hash
        add_hash = False
        if os.path.isfile(location):
            add_hash = True

        #copy file
        shutil.copy2(self.full_path, location)

        #add hash if needed
        if add_hash:
            self.add_metadata_to_file(location, self.metadata)



class Folder(_BaseFile):

    def __init__(self, path, folder=None):

        self.hash = self._get_hash()
        self._files: list = []
        self.old_files: list = None
        self.old_hashes: set = None
        self.old_paths: set = None

        super().__init__(path, folder)

    @property
    def files(self):
        return self._get_files()

    @files.setter
    def files(self,files):
        self._files = files

    @property
    def hashes(self):
        return self._get_hashes()

    @property
    def paths(self):
        return set(self._get_paths())

    @property
    def paths_no_root(self):
        """ get the paths with no root directory"""
        return self._get_paths(no_root=True)

    @property
    def filenames(self):
        return [fl.file_name for fl in self.files]

    @property
    def metadatas(self):
        return [fl.metadata for fl in self.files]


    def _get_paths(self, path_list=None,no_root=False):
        """ get all paths from current files"""
        path = []
        for fl in self.files:
            path.append(fl.full_path if no_root else fl.path)
        return path

    def _get_hashes(self, hash_list=None):
        """ get all hashes from current files"""
        hashes = set()
        for fl in self.files:
            if fl.hash is not None:
                hashes.add(fl.hash)
        return hashes

    def _get_files(self, files=None):
        """ recursively get all files in folder"""
        if files == None:
            files = []

        if self._files is not None:
            for fl in self._files:
                if type(fl) is Folder:
                    files = fl._get_files(files)
                files.append(fl)

        return files

    def _get_hash(self):
        """ get hash of this folder"""
        try:
            return dirhash(self.full_path, "md5")
        except:
            return None


    def do_copy(self, location=None, fl=None):
        """ folder method for copying"""
        if not fl is None:
            location = fl.source + self.path

        if not os.path.isdir(location):
            os.mkdir(location)

    def load_files(self) -> None:
        """ load all files in the directory into this folder """

        # copy old files
        self.old_files = copy.copy(self.files)
        # copy old hashes
        self.old_hashes = copy.copy(self.hashes)
        # copy old paths
        self.old_paths = copy.copy(self.paths)

        base_path = self.full_path

        for fl in os.listdir(base_path):
            if os.path.isfile(base_path + "/" + fl):
                fl = File(fl, self)
                self.add_file(fl)
            else:
                fldr = Folder(fl, self)
                self.add_file(fldr)
                fldr.load_files()

    def get_differences(self):
        """ used to get the local changes to the last run"""
        if self.has_changes():
            new, renamed, modified = self._get_new()
            deleted = self._get_missing()
            return new, renamed, modified, deleted
        else:
            return [],[],[],[]

    def _get_new(self):
        """ get the new """
        new = []
        renamed = []
        modified = []
        files = self.files

        for fl in files:
            if fl not in self.old_files:
                if fl.hash in self.old_hashes and type(fl) is File:
                    renamed.append(fl)
                elif fl.hash not in self.old_hashes and type(fl) is Folder:
                    # if a folders contents change then do nothing
                    pass
                elif fl.path in self.old_paths and type(fl) is File:
                    modified.append(fl)
                else:
                    new.append(fl)

        return new, renamed, modified

    def _get_missing(self):
        deleted = []
        files = self.files
        for fl in self.old_files:
            if fl not in files:
                if type(fl) is File and fl.path not in self.paths and not fl.hash in self.get_folder(fl.source + "/")[0].hashes:
                    deleted.append(fl)
        return deleted

    def pop_fl(self,find_fl):

        for fl in self._files:
            if fl == find_fl:
                return self._files.pop(self._files.index(fl))
            elif type(fl) == Folder:
                found_fl = fl.pop_fl(find_fl)
                if found_fl and found_fl == find_fl:
                    return found_fl

    def get_folder(self,path):
        """ returns the folder at the path"""
        ans = [fldr for fldr in self.files if type(fldr) is Folder and fldr.full_path == path]
        if ans == [] and path in self._get_root():
            return [self]
        else:
            return ans

    def get_file(self,path=None,source_no_root=None, hash=None):
        """ returns the folder at the path"""
        for file in self.files:
            if type(file) is File:
                path_match = True if not path else True if file.path == path else False
                source_no_root_match = True if not source_no_root else True if file.source_no_root == source_no_root else False
                hash_match = True if not hash else True if file.hash == hash else False
                if path_match and source_no_root_match and hash_match:
                    return file
        return

    def has_changes(self):
        """ does this folder have changes since the last run"""
        return self.files != self.old_files

    def add_file(self, fl):
        """ add file to file list """
        self._files.append(fl)

    def move_file_to_folder(self,fl):

        """ moves the files to this folder"""
        os.rename(fl.full_path, self.full_path + "/" + fl.file_name)
        self._files.append(fl)

        #rehash the current folder as changes may be made
        self.hash = self._get_hash()

    def _clear_arrays(self):
        """
        :param self:
        """
        self.files = []

class Syncer:

    def __init__(self, sourcePath, destPath):

        # load folders
        self.first_run: bool = False
        self.source_folder: Folder = Folder(sourcePath)
        self.dest_folder: Folder = Folder(destPath)

    def _get_files(self):
        # get files
        self.source_folder.load_files()
        self.dest_folder.load_files()

    def reverse_folders(self):
        # used to switch the running order
        self.source_folder, self.dest_folder = self.dest_folder, self.source_folder

    def _copy_new(self, new):
        for fl in new:
            if fl.path not in self.dest_folder.paths:
                #work out if file or folder
                if type(fl) is File:
                    File_Type = File
                else:
                    File_Type = Folder

                #copy file over to new location
                fl.copy(self.dest_folder.full_path)

                #get folder in dest directory
                fldr = self.dest_folder.get_folder(self.dest_folder.full_path + fl.source_no_root)
                if len(fldr) == 0:
                    fldr = self.dest_folder
                else:
                    fldr = fldr[0]
                #add the file
                fldr.add_file(File_Type(fl.file_name, fldr))

    def _rename(self, renamed):
        for fl in renamed:
            dest_fl = self.dest_folder.get_file(source_no_root=fl.source_no_root, hash=fl.hash)
            dest_fl.rename_self_as_input(fl)



    def _do_modified(self, modified):
        for fl in modified:
            dest_fl = self.dest_folder.get_file(fl.path)
            if dest_fl:
                fl.copy(fl=dest_fl[0])

    def _delete(self, deleted):
        for fl in deleted:
            if fl in self.dest_folder.files:
                del_file = self.dest_folder.pop_fl(fl)
                if del_file:
                    del_file.delete_self()


    def _action_differences(self, *args):
        new, renamed, modified, deleted = args
        if new != []:
            self._copy_new(new)
        if renamed != []:
            self._rename(renamed)
        if modified != []:
            self._do_modified(modified)
        if deleted != []:
            self._delete(deleted)

    def init_sync(self):
        self._get_files()
        self.source_folder.files[6].size
        self._action_differences(*self.source_folder.get_differences())

    def sync(self):

        if not self.first_run:
            self.first_run = True
            self.init_sync()

        self._get_files()

        for x in range(2):
            if self.source_folder.has_changes():
                self._action_differences(*self.source_folder.get_differences())
            self.reverse_folders()

if __name__ == "__main__":

    sync = Syncer("source/", "dest/")

    while True:
        sync.sync()
        time.sleep(0.2)

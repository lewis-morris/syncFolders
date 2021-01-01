import copy
import datetime
import pathlib
import secrets
import shutil
import os
import string
import time

import colored
from dirhash import dirhash
from typing import List

from functions import hash_file
from colored import stylize


class _BaseFile:

    def __init__(self, file_name, folder):

        self._file_name = file_name

        # set parent folder and add file
        self.parent_folder = folder

        self._fl = pathlib.Path(self.full_path)
        self._ignore = False
        self._stored_metadata = None
        self.hash = None

        if self.metadata is None:
            # this self.metadata polls the file on request and will always be correct.
            self.add_metadata(self)

        elif self._stored_metadata is None:
            # this can be incorrect to the file metadata but it used for checking local changes to the folder.
            self._stored_metadata = self.metadata

    @staticmethod
    def add_metadata(cls, data=None):
        """ add meta data to file"""
        if data is None:
            # generate random key to file if not supplied
            alphabet = string.ascii_letters + string.digits
            data = ''.join(secrets.choice(alphabet) for i in range(15))

        if type(cls) is not str:
            path = cls.full_path
            cls._stored_metadata = data
        else:
            path = cls
        try:
            os.setxattr(path, 'user.data', bytes(data, 'utf-8'))

        except PermissionError:
            # print(f"Permission error with file {path} unable to rectify, file to be ignored")
            # if passed in file is file not str then ignore it
            if type(cls) == _BaseFile:
                cls._ignore = True
        except FileNotFoundError:
            # not found error
            pass

    def __eq__(self, other):
        """ files match if their metadata, path and hash match"""
        meta_ok = self.metadata == other.metadata
        path_ok = self.path == other.path

        if self.hash is not None:
            hash_ok = self.hash == other.hash
        else:
            return path_ok

        return meta_ok and path_ok and hash_ok

    def __gt__(self, other):
        return self.modified > other.modified

    def __hash__(self):
        return hash(self.full_path + self.hash)

    def exists(self):
        """ does this file actually exist """
        return os.path.isfile(self.full_path) if type(self) == File else os.path.isdir(self.full_path)

    # FILE INFORMATION
    def is_hash_match(self, other):
        """ used to check if another file is a hash match """
        return self.hash == other.hash

    def is_metadata_match(self, other):
        """ used to check if another file is a hash match """
        return self.metadata == other.metadata

    # FILE ACTIONS
    def do_copy(self, fl=None, fldr=None):
        """ not needed in base class """
        pass

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

    def rename_self_as_input(self, fl):
        """ used to rename file """
        if self.exists():
            os.rename(self.full_path, self.source + "/" + fl.file_name)
            self.file_name = fl.file_name
            self.hash = fl.hash

    def copy_over_oldest_file(self, fl=None, fldr=None):
        """ used self to  missing file location / over older version
        location: path excluding the file names
        file: [File] above ignored if file passed
        fldr: [Folder] file added to folder if supplied
        """
        if self.exists():
            if fl:
                if fl > self:
                    fl.copy_over_oldest_file(self, self.parent_folder)
                else:
                    self.do_copy(fl=fl, fldr=fldr)
            else:
                self.do_copy(fl, fldr)

    # PROPERTIES

    @property
    def root_folder_path(self):
        """ recursively get the root folders path """
        if self.parent_folder:
            ans = self.parent_folder.root_folder_path
        else:
            return self.file_name
        return ans

    @property
    def root_folder(self):
        """ recursively get the root folders path """
        if self.parent_folder:
            ans = self.parent_folder.root_folder
        else:
            return self
        return ans

    @property
    def file_name(self):
        """ returns the file name """
        return self._file_name

    @file_name.setter
    def file_name(self, name):
        """ sets the file name of this file"""
        self._file_name = name

    @property
    def full_path(self):
        """ returns the path of this file including the file name """
        path = self.file_name if self.source == "" else self.source + "/" + self.file_name
        return path

    @property
    def metadata(self):
        """ returns the metadata of this file"""
        try:
            return os.getxattr(self.full_path, 'user.data').decode("utf-8")
        except OSError:
            return None

    @property
    def path(self):
        """ returns the path of this file minus the file name """
        path = self.full_path
        root = self.root_folder_path
        find_root = path.find(root)
        return path[find_root + len(root):]

    @property
    def source_no_root(self):
        """ retuns the source path of this file minus the root folder path"""
        path = self.full_path
        root = self.root_folder_path
        find_root = path.find(root)
        return self.source[find_root + len(root):]

    @property
    def source(self):
        """ retuns the souce path of this file"""
        if not self.parent_folder:
            return ""
        else:
            lst = self._get_source_list()
            lst.reverse()
            return "/".join(lst)

    @property
    def modified(self):
        """ Returns date last modified"""
        return datetime.datetime.fromtimestamp(self._fl.stat().st_mtime)

    @property
    def accessed(self):
        """ Returns date last accessed """
        return datetime.datetime.fromtimestamp(self._fl.stat().st_atime)

    @property
    def size(self):
        """

        :return:
        """
        # get file size and convert to human readable

        size = self._fl.stat().st_size

        gb = format(round(size / 1024 / 1024 / 1024, 3), ".2f")

        if gb[0] != "0":
            return gb + " gb"

        mb = format(round(size / 1024 / 1024, 3), ".2f")
        if mb[0] != "0":
            return mb + " mb"

        kb = format(round(size / 1024, 3), ".2f")
        if kb[0] != "0":
            return kb + " kb"

        else:
            return f"{size} bytes"


    def _get_source_list(self, lst=None):
        """ used to recursively get the parent folder names"""
        if lst is None:
            lst = []

        if self.parent_folder:
            name = self.parent_folder.file_name
            if name[-1] == "/":
                name = name[:-1]
            lst.append(name)
            # removed this as it appears to have been casuing an issue with root paths that are not relative - and
            # added above
            # lst.append(self.parent_folder._file_name.replace("/",""))
            lst = self.parent_folder._get_source_list(lst)

        return lst

class File(_BaseFile):
    """

    """

    def __init__(self, path, folder):
        super().__init__(path, folder)
        self.hash = self._get_hash()

    def _get_hash(self) -> str:
        return hash_file(self.full_path)

    def do_copy(self, fl=None, fldr=None) -> None:
        """ copy file, if the destination path is already a file, then its an overwrite (modified file) and
            needs to have the hash of the source file added to the destination file
        """
        # copy file

        if fl:
            copy_path = fl.full_path
            file_name = fl.file_name
            shutil.copy2(self.full_path, fl.full_path)

        else:
            copy_path = fldr.full_path + ("/" if fldr.full_path[-1] != "/" else "") + self.file_name
            file_name = self.file_name
            shutil.copy2(self.full_path, copy_path)

        self.add_metadata(copy_path, self.metadata)

        file = File(file_name, fldr)
        if file not in fldr.files:
            fldr.add_file(File(file_name, fldr))


class Folder(_BaseFile):
    """

    """

    def __init__(self, path, folder=None):

        self.hash = self._get_hash()
        self._files: list = []
        self.old_files: list = None
        self.old_hashes: set = None
        self.old_paths: set = None

        super().__init__(path, folder)

    # FOLDER INFORMATION

    def has_changes(self) -> bool:
        """ does this folder have changes since the last run"""
        return self.files != self.old_files

    def get_changes(self) -> tuple:
        """

        :return:
        """
        modified_files = []
        new_files = []
        removed_files = []

        # self.files has to recursively get the files, so for speed store output in variable
        current_files = self.files

        # check for changes between this run and the last
        for fl in current_files:
            if fl in self.old_files:
                self.old_files.remove(fl)
            else:
                match = [x for x in self.old_files if x._stored_metadata == fl.metadata]
                if match:
                    # file exists but there is a change
                    modified_files.append(match[0])
                else:
                    # new file
                    new_files.append(fl)

        # check for deleted items
        for fl in self.old_files:
            if fl not in current_files:
                removed_files.append(fl)

        return modified_files, new_files, removed_files

    def _action_changes(self, *args) -> None:
        modified_files, new_files, removed_files = args
        self._add_new_files(new_files)

    def _add_new_files(self, new) -> None:
        for fl in new:
            folder = self.get_folder_that_contains(fl)
            fl.copy_over_oldest_file(fldr=folder)

    def _remove_deleted_files(self, removed) -> None:
        pass

    def _ammend_modified_files(self, modified) -> None:
        pass

    # FOLDER ACTIONS

    def do_copy(self, fl=None, fldr=None) -> None:
        """ folder method for copying"""
        if fl is not None:
            location = fldr.full_path + ("/" if fldr.full_path[-1] != "/" else '') + fl.file_name
        else:
            location = fldr.full_path + ("/" if fldr.full_path[-1] != "/" else '') + self.file_name

        if not os.path.isdir(location):
            os.mkdir(location)

        if fldr:
            fldr.add_file(Folder(self.file_name, fldr))

    def load_files(self) -> None:

        """ load all files in the directory into this folder. Only needs to run on the root folder
         and all subsequent sub folders / directories will be created/ populated
         """

        # copy old files
        self.old_files = copy.copy(self.files)
        # copy old hashes
        self.old_hashes = copy.copy(self.hashes)
        # copy old paths
        self.old_paths = copy.copy(self.paths)

        # clear the file array
        self._clear_arrays()

        base_path = self.full_path

        for fl in os.listdir(base_path):
            if os.path.isfile(base_path + "/" + fl):
                fl = File(fl, self)
                self.add_file(fl)
            else:
                fldr = Folder(fl, self)
                self.add_file(fldr)
                fldr.load_files()

    def add_file(self, fl: object) -> None:
        """ add file to file list """
        self._files.append(fl)

    def move_file_to_folder(self, fl) -> None:
        """ moves the passed in file/folder to have this folder as the parent"""
        os.rename(fl.full_path, self.full_path + "/" + fl.file_name)
        self._files.append(fl)
        # rehash the current folder as changes may be made
        self.hash = self._get_hash()

    # FOLDER SEARCHES
    def get_folder_by_path(self, path) -> _BaseFile:
        """ returns the folder at the path and creates if missing"""

        for file in self.files:
            if file.path == path:
                return file

    def get_folder_that_contains(self, fl) -> Folder:
        """ returns the folder at the path and creates if missing"""

        parent = None
        for file in self.files:
            if type(file) is Folder:
                if fl == file:
                    parent = fl.parent_folder
                    break
                elif file.path == fl.source_no_root:
                    parent = file
                    break

        if parent is not None:
            return parent
        elif fl.source_no_root == "":
            return self.root_folder
        else:
            print(fl.path)
            return self._create_and_add_missing_folders(fl.path, True if type(fl) is Folder else False).parent_folder

    def get_file(self, path=None, source_no_root=None, hash_val=None) -> File:

        """returns the folder at the path

        path: will search for the path of the file
        source_no_root: will search for a file with this parent directory path. (to be used with hash to find modified
        filed)
        hash: searches for a file with this hash

        """
        for file in self.files:
            if type(file) is File:
                path_match = True if not path else True if file.path == path else False
                source_no_root_match = True if not source_no_root else True if file.source_no_root == source_no_root \
                    else False
                hash_match = True if not hash_val else True if file.hash == hash_val else False
                if path_match and source_no_root_match and hash_match:
                    return file
        return

    def pop_fl(self, find_fl) -> File:
        """ accepts File type. Pops from list (for removing/deleting the file """
        for fl in self._files:
            if fl == find_fl:
                return self._files.pop(self._files.index(fl))
            elif type(fl) == Folder:
                found_fl = fl.pop_fl(find_fl)
                if found_fl and found_fl == find_fl:
                    return found_fl

    # FOLDER FUNCTIONS

    def print_tree(self, lengths=None, first=True) -> str:

        """ used to print the directory tree structure of the current folder"""

        if lengths is None:
            lengths = []

        if self._files is not None:
            output = ""
            # get print makeup prior to file
            for leng in lengths:
                output += "|" + " " * int(leng * .3)

            for fl in sorted(self._files, key=lambda x: x.file_name.lower()):

                size = "- [" + stylize(f"{fl.size}", colored.fg("dark_sea_green_4a")) + "]"
                file_name = stylize(f"{fl.file_name}", colored.fg("medium_purple_1")) if type(
                    fl) == Folder else stylize(f"{fl.file_name}", colored.fg("misty_rose1"))
                files = " - (" + stylize(f"{len(fl._files)}", colored.fg("deep_pink_1b")) + ")" if type(
                    fl) == Folder else ""
                sync_error = ("- [" + stylize(" unable to sync", colored.fg("red_1")) + "]") if fl._ignore is True \
                    else ""

                fl_name = f"{file_name} {files} {size} {sync_error}"

                if type(fl) is Folder:
                    # if folder print info and then go in a layer#
                    print(f"{output}├── {fl_name}")
                    lengths.append(len(fl_name) / 3)
                    fl.print_tree(lengths)
                    lengths.pop()
                else:
                    print(f"{output}{'└──' if first is True and len(lengths) != 0 else '├──'} {fl_name}")
                    first = False

    # FOLDER PROPERTIES

    @property
    def core_files(self) -> List[_BaseFile]:
        """ returns  _Base_Files/Files/Folders of all files stored in this folder"""
        return self._get_files(core=True)

    @property
    def files(self) -> List[_BaseFile] :
        """ returns  _Base_Files/Files/Folders of all files stored in this folder and all sub folders"""
        return self._get_files()

    @files.setter
    def files(self, files:List[_BaseFile]):
        """ sets the files in this directory"""
        self._files = files

    @property
    def hashes(self) -> List[str]:
        """ returns the hashes of all files in this folder and sub folders"""
        return self._get_hashes()

    @property
    def core_hashes(self) -> List[str]:
        """ returns the hashes of all files in this folder"""
        return self._get_hashes(core=True)

    @property
    def paths(self) -> List[str]:
        """ returns the paths of all files in this folder and sub folders"""
        return set(self._get_paths())

    @property
    def core_paths(self) -> List[str]:
        """ returns the paths of all files in this folder"""
        return set(self._get_paths(core=True))

    @property
    def paths_no_root(self) -> List[str]:
        """ returns the paths_with_no_root of all files in this folder and sub folders"""
        return self._get_paths(no_root=True)

    @property
    def core_paths_no_root(self) -> List[str]:
        """ returns the paths_with_no_root of all files in this folder"""
        return self._get_paths(no_root=True, core=True)

    @property
    def file_names(self) -> List[str]:
        """ returns the file names of all files in this folder and sub folders"""
        return [fl.file_name for fl in self.files]

    @property
    def core_file_names(self) -> List[str]:
        """ returns the file names of all files in this folder"""
        return [fl.file_name for fl in self._files]

    @property
    def metadatas(self) -> List[str]:
        """ returns the metadata of all files in this folder and sub folders"""
        return [fl.metadata for fl in self.files]

    @property
    def core_metadatas(self) -> List[str]:
        """ returns the metadata of all files in this folder"""
        return [fl.metadata for fl in self._files]

    # HIDDEN METHODS

    def _get_paths(self, no_root=False, core=False) -> List[str]:
        """ get all paths from current files"""
        path = []
        for fl in self._files if core else self.files:
            path.append(fl.full_path if no_root else fl.path)
        return path

    def _get_hashes(self, hash_list=None, core=False) -> List[str]:
        """ get all hashes from current files"""
        hashes = set()
        for fl in self._files if core else self.files:
            if fl.hash is not None:
                hashes.add(fl.hash)
        return hashes

    def _get_files(self, files=None, core=False) -> List[str]:
        """ recursively get all files in folder"""
        if files is None:
            files = []

        if self._files is not None:
            for fl in self._files:
                if type(fl) is Folder and not core:
                    files = fl._get_files(files)
                files.append(fl)

        return files

    def _get_hash(self) -> str:
        """ get hash of this folder"""
        try:
            return dirhash(self.full_path, "md5")
        except:
            return None

    def _create_and_add_missing_folders(self, path, folder=True) -> Folder:

        """ if you ask for a folder ans its missing, this create all missing folders

         i.e if you want 'test/test/test/test' but only 'test/test/' exists

         it will create 'test/test/test' and 'test/test/test/test'

         """
        split_paths = path.split("/")
        if not folder:
            split_paths = split_paths[:-1]

        new_folders = []
        for i in range(1, len(split_paths) + 1):
            dir_path = "/".join(split_paths[:i])
            if dir_path not in self.paths:
                new_folder_path = self.root_folder_path + dir_path
                os.mkdir(new_folder_path)

                if len(new_folders) == 0:
                    new_folders.append(Folder(split_paths[i - 1], self))
                    self.add_file(new_folders[-1])
                else:
                    folder = Folder(split_paths[i - 1], new_folders[-1])
                    new_folders.append(folder)
                    new_folders[-2].add_file(folder)

            else:
                new_folders.append(self.get_folder_by_path(dir_path))

        return new_folders[-1]

    def _clear_arrays(self):
        """
        :param self:
        """
        self.files = []


class Syncer:
    """

    """

    def __init__(self, source_path: str, dest_path: str):

        # load folders
        self.first_run: bool = False
        self.source_folder: Folder = Folder(source_path)
        self.dest_folder: Folder = Folder(dest_path)

    def _get_files(self):
        """
        load add files in each directory (source and destination)
        """
        self.source_folder.load_files()
        self.dest_folder.load_files()

    def reverse_folders(self):
        """
        used to switch the running order
        """
        self.source_folder, self.dest_folder = self.dest_folder, self.source_folder

    def init_equilibrium(self) -> None:
        """
        Run this to initially sync both the source and destination folder. On the first run it is unlikely that files
        will contain matching metadata.
        """
        source = self.source_folder
        dest = self.dest_folder
        dest_files = dest.files

        for fl in sorted(source.files, key=lambda x: str(type(x)), reverse=True):
            if fl not in dest_files:

                # get the destination folder and if it doesnt exist create and all parent folders until correct
                # structure
                # has been created
                print(fl.path)
                dest_folder = dest.get_folder_that_contains(fl)

                # metadata update - this keeps the same files in each folder having the same hash
                if fl.path in dest_folder.core_paths and fl.hash in dest_folder.core_hashes and fl.metadata not in \
                        dest_folder.core_metadatas:
                    dest_fl = dest_folder.get_file(source_no_root=fl.source_no_root, hash_val=fl.hash)
                    File.add_metadata(dest_fl, fl.metadata)

                # renamed files need changing
                elif fl.hash in dest_folder.core_hashes and fl.file_name not in dest_folder.core_file_names:
                    dest_fl = dest_folder.get_file(hash_val=fl.hash)

                    # update the newest file with the new name
                    if fl > dest_fl:
                        dest_fl.rename_self_as_input(fl)
                    else:
                        fl.rename_self_as_input(dest_fl)

                # modified files
                elif fl.hash not in dest_folder.core_hashes and fl.path in dest_folder.core_paths:
                    if type(fl) == File:
                        dest_fl = dest_folder.get_file(path=fl.path)
                        fl.copy_over_oldest_file(fl=dest_fl, fldr=dest_folder)

                # new file straight copy (doesn't already exist)
                elif fl.hash not in dest_folder.core_hashes and fl.file_name not in dest_folder.core_file_names:
                    fl.copy_over_oldest_file(fldr=dest_folder)
                else:
                    pass

    def init_sync(self):
        """ used to initially sync the folders to a state of equilibrium """
        self._get_files()
        self.init_equilibrium()
        self.reverse_folders()
        self._get_files()
        self.init_equilibrium()

    def sync(self):
        """

        """
        # the first run will sync folders to match
        if not self.first_run:
            self.first_run = True
            self.init_sync()

        # loop both source and destination, switch folders after each iteration.
        self._get_files()
        for x in range(2):
            if self.source_folder.files != self.source_folder.old_files and \
                    self.source_folder.files != self.dest_folder.files:
                # if there is a difference in the current and old folders. Then find what they are and react.
                self.dest_folder._action_changes(*self.source_folder.get_changes())
            self.reverse_folders()


if __name__ == "__main__":

    sync = Syncer("/home/lewis/PycharmProjects/syncFolders/source/", "/home/lewis/PycharmProjects/syncFolders/dest/")

    while True:
        sync.sync()
        time.sleep(0.2)

import shutil
import time
import unittest
from functions import create_text_file
from sync import Folder
import os
from shutil import copy2


class my_tests(unittest.TestCase):

    def setUp(self):
        try:
            shutil.rmtree("test/")
        except:
            pass
        os.mkdir("test/")

        try:
            shutil.rmtree("test1/")
        except:
            pass
        os.mkdir("test1/")

    def test_folder_picks_up_files(self):
        create_text_file("test/file1.txt", 10000)
        create_text_file("test/file2.txt", 10000)
        os.mkdir("test/test1")
        folder = Folder("test/")
        folder.load_files()
        self.assertTrue(len(folder.files) == 3)

    def test_folder_stores_old_files(self):

        create_text_file("test/file1.txt", 10000)
        create_text_file("test/file2.txt", 10000)
        os.mkdir("test/test1")
        folder = Folder("test/")
        folder.load_files()
        folder.load_files()

        for fl in folder.files:
            self.assertTrue(fl in folder.old_files)
        for hash in folder.hashes:
            self.assertTrue(hash in folder.old_hashes)
        for name in folder.names:
            self.assertTrue(name in folder.old_names)

    def tearDown(self):
        shutil.rmtree("test/")
        shutil.rmtree("test1/")


if __name__ == '__main__':
    unittest.main()


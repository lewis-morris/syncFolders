import datetime
import random
import secrets
import shutil
import time
import unittest
from sync import Syncer, hash_file
import os
from shutil import copyfile
import pytest
import nose2

class my_tests(unittest.TestCase):

    def setUp(self):

        os.mkdir("test/")
        os.mkdir("test1/")
        self.sync = Syncer("test/", "test1/")

    def test_update_changes_to_file_contents_in_source(self):

        #create radom file
        with open("test/file1.txt", "w") as f:
            f.writelines(secrets.token_hex(128))

        #move to test dir
        copyfile("test/file1.txt","test1/file1.txt")

        #write new data to file
        with open("test/file1.txt", "a+") as f:
            f.write("\n Test"*1000)

        date = datetime.datetime.utcnow() + datetime.timedelta(seconds=1)
        mod = time.mktime(date.timetuple())
        os.utime("test/file1.txt", (mod, mod))

        self.sync.sync()

        self.assertEqual(hash_file("test/file1.txt"),hash_file("test1/file1.txt"))


    def test_update_changes_to_file_contents_in_dest(self):
        # create radom file
        with open("test1/file1.txt", "w") as f:
            f.writelines(secrets.token_hex(128))

        # move to test dir
        copyfile("test1/file1.txt", "test/file1.txt")

        # write new data to file
        with open("test1/file1.txt", "a+") as f:
            f.write("\n Test" * 1000)

        date = datetime.datetime.utcnow() + datetime.timedelta(seconds=1)
        mod = time.mktime(date.timetuple())
        os.utime("test1/file1.txt", (mod, mod))

        self.sync.sync()

        self.assertEqual(hash_file("test/file1.txt"), hash_file("test1/file1.txt"))

    def test_update_changes_to_file_contents_in_dest_and_one_in_source(self):
        # create radom file
        with open("test1/file1.txt", "w") as f:
            f.writelines(secrets.token_hex(128))

        # move to test dir
        copyfile("test1/file1.txt", "test/file1.txt")

        # write new data to file
        with open("test1/file1.txt", "a+") as f:
            f.write("\n Test" * 1000)

        date = datetime.datetime.utcnow() + datetime.timedelta(seconds=1)
        mod = time.mktime(date.timetuple())
        os.utime("test1/file1.txt", (mod, mod))


        # create radom file
        with open("test/file2.txt", "w") as f:
            f.writelines(secrets.token_hex(128))

        # move to test dir
        copyfile("test/file2.txt", "test1/file2.txt")

        # write new data to file
        with open("test/file2.txt", "a+") as f:
            f.write("\n Test" * 1000)

        date = datetime.datetime.utcnow() + datetime.timedelta(seconds=1)
        mod = time.mktime(date.timetuple())
        os.utime("test/file2.txt", (mod, mod))


        self.sync.sync()

        self.assertEqual(hash_file("test/file1.txt"), hash_file("test1/file1.txt"))
        self.assertEqual(hash_file("test/file2.txt"), hash_file("test1/file2.txt"))

    def test_file_missing_one_in_source_one_in_dest(self):

        #create radom file
        with open("test/file1.txt", "w") as f:
            f.writelines(secrets.token_hex(128))

        with open("test1/file2.txt", "w") as f:
            f.writelines(secrets.token_hex(128))

        self.sync.sync()

        self.assertEqual(hash_file("test/file1.txt"), hash_file("test1/file1.txt"))
        self.assertEqual(hash_file("test/file2.txt"), hash_file("test1/file2.txt"))

    def test_file_missing_in_source(self):

        #create radom file
        with open("test/file1.txt", "w") as f:
            f.writelines(secrets.token_hex(128))

        self.sync.sync()

        self.assertEqual(hash_file("test/file1.txt"), hash_file("test1/file1.txt"))

    def test_file_missing_in_dest(self):

        #create radom file
        with open("test1/file1.txt", "w") as f:
            f.writelines(secrets.token_hex(128))

        self.sync.sync()
        self.assertEqual(hash_file("test/file1.txt"), hash_file("test1/file1.txt"))

    def test_folder_missing_in_source(self):
        # create radom file

        os.mkdir("test/test")
        self.sync.sync()
        self.assertTrue(os.path.isdir("test1/test"))

    def test_folder_missing_in_dest(self):
        # create radom file
        os.mkdir("test1/test")
        self.sync.sync()
        self.assertTrue(os.path.isdir("test/test"))

    def test_folder_missing_in_source_and_another_in_dest(self):
        # create radom file

        os.mkdir("test/test")
        os.mkdir("test1/test1")
        self.sync.sync()
        self.assertTrue(os.path.isdir("test1/test"))
        self.assertTrue(os.path.isdir("test/test1"))


    def test_subfolder_with_contents_missing_from_one_folder(self):
        # create radom file

        os.mkdir("test/sub")
        with open("test/sub/file1.txt", "w") as f:
            f.writelines(secrets.token_hex(128))

        self.sync.sync()
        self.assertTrue(os.path.isdir("test1/sub"))
        self.assertEqual(hash_file("test/sub/file1.txt"), hash_file("test1/sub/file1.txt"))

    def test_rename_folder_in_dest(self):
        os.mkdir("test/sub")
        self.sync.sync()
        self.assertTrue(os.path.isdir("test1/sub"))
        self.assertTrue(os.path.isdir("test/sub"))
        os.rename("test/sub","test/sub1")
        self.sync.sync()
        self.assertTrue(os.path.isdir("test1/sub1"))

    def test_rename_folder_in_source(self):
        os.mkdir("test1/sub")
        self.sync.sync()
        self.assertTrue(os.path.isdir("test/sub"))
        self.assertTrue(os.path.isdir("test1/sub"))
        os.rename("test1/sub", "test1/sub1")
        self.sync.sync()
        self.assertTrue(os.path.isdir("test/sub1"))

    def test_file_rename_in_dest(self):
        # create radom file
        with open("test/file1.txt", "w") as f:
            f.writelines(secrets.token_hex(128))
        self.sync.sync()
        self.assertTrue(os.path.isfile("test/file1.txt"))
        self.assertTrue(os.path.isfile("test1/file1.txt"))

        os.rename("test/file1.txt", "test/file11.txt")

        self.sync.sync()

        self.assertTrue(os.path.isfile("test/file11.txt"))
        self.assertTrue(os.path.isfile("test1/file11.txt"))
        self.assertTrue((hash_file("test/file11.txt"), hash_file("test1/file11.txt")))

    def test_file_rename_in_source(self):

        # create radom file
        with open("test1/file1.txt", "w") as f:
            f.writelines(secrets.token_hex(128))
        self.sync.sync()
        self.assertTrue(os.path.isfile("test1/file1.txt"))
        self.assertTrue(os.path.isfile("test/file1.txt"))

        os.rename("test1/file1.txt", "test1/file11.txt")

        self.sync.sync()

        self.assertTrue(os.path.isfile("test1/file11.txt"))
        self.assertTrue(os.path.isfile("test/file11.txt"))
        self.assertTrue((hash_file("test1/file11.txt"), hash_file("test/file11.txt")))

    def test_file_rename_in_subfolder_in_source(self):

        os.mkdir("test/sub")
        # create radom file
        with open("test/sub/file1.txt", "w") as f:
            f.writelines(secrets.token_hex(128))

        self.sync.sync()
        self.assertTrue(os.path.isfile("test/sub/file1.txt"))
        self.assertTrue(os.path.isfile("test1/sub/file1.txt"))

        os.rename("test/sub/file1.txt", "test/sub/file11.txt")

        self.sync.sync()

        self.assertTrue(os.path.isfile("test1/sub/file11.txt"))
        self.assertTrue(os.path.isfile("test/sub/file11.txt"))

        self.assertTrue((hash_file("test1/sub/file11.txt"), hash_file("test/sub/file11.txt")))

    def tearDown(self):
        shutil.rmtree("test/")
        shutil.rmtree("test1/")

if __name__ == '__main__':
    unittest.main()


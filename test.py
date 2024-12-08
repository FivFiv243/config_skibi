import json
import unittest
import os
import tempfile
import zipfile
import shutil
import xml.etree.ElementTree as ET
from main import read_config, VirtualFileSystem, log_action, ls, cd, cat, rmdir, head

class TestShellEmulator(unittest.TestCase):
    def setUp(self):
        # Создание временного каталога для тестов
        self.test_dir = tempfile.mkdtemp()
        self.test_zip = os.path.join(self.test_dir, "test.zip")
        self.log_path = os.path.join(self.test_dir, "log.xml")
        self.config_path = os.path.join(self.test_dir, "config.json")

        # Создание тестового ZIP-файла
        with zipfile.ZipFile(self.test_zip, 'w') as zipf:
            zipf.writestr('file1.txt', 'Hello, World!')
            zipf.writestr('dir1/file2.txt', 'Another file')
            zipf.writestr('dir2/file3.log', 'Log file content')

        # Создание тестового конфигурационного файла
        config_data = {
            "hostname": "TestHost",
            "vfs_path": self.test_zip,
            "log_path": self.log_path
        }
        with open(self.config_path, 'w') as f:
            json.dump(config_data, f)

    def tearDown(self):
        # Удаление временного каталога
        shutil.rmtree(self.test_dir)

    def test_read_config(self):
        hostname, vfs_path, log_path = read_config(self.config_path)
        self.assertEqual(hostname, "TestHost")
        self.assertEqual(vfs_path, self.test_zip)
        self.assertEqual(log_path, self.log_path)

    def test_vfs_extraction(self):
        vfs = VirtualFileSystem(self.test_zip)
        self.assertTrue(os.path.isdir(vfs.root))
        self.assertTrue(os.path.isfile(os.path.join(vfs.root, 'file1.txt')))
        self.assertTrue(os.path.isfile(os.path.join(vfs.root, 'dir1', 'file2.txt')))

    def test_ls_command(self):
        vfs = VirtualFileSystem(self.test_zip)
        output = ls(vfs)
        self.assertIn("file1.txt", output)
        self.assertIn("dir1", output)

    def test_cd_command(self):
        vfs = VirtualFileSystem(self.test_zip)
        output = cd(vfs, 'dir1')
        self.assertEqual(vfs.get_relative_path(), 'dir1')
        self.assertIn("Changed directory", output)

        output = cd(vfs, '..')
        self.assertEqual(vfs.get_relative_path(), '.')
        self.assertIn("Changed directory", output)

        output = cd(vfs, 'nonexistent')
        self.assertIn("Directory not found", output)

    def test_cat_command(self):
        vfs = VirtualFileSystem(self.test_zip)
        output = cat(vfs, 'file1.txt')
        self.assertEqual(output, 'Hello, World!')

        output = cat(vfs, 'nonexistent.txt')
        self.assertIn("File not found", output)

    def test_rmdir_command(self):
        vfs = VirtualFileSystem(self.test_zip)
        os.mkdir(os.path.join(vfs.current_path, 'empty_dir'))
        output = rmdir(vfs, 'empty_dir')
        self.assertIn("Directory 'empty_dir' removed.", output)

        output = rmdir(vfs, 'nonexistent_dir')
        self.assertIn("Directory 'nonexistent_dir' not found.", output)

    def test_head_command(self):
        vfs = VirtualFileSystem(self.test_zip)
        output = head(vfs, 'file1.txt', 1)
        self.assertEqual(output.strip(), "Hello, World!")

        output = head(vfs, 'nonexistent.txt')
        self.assertIn("File 'nonexistent.txt' not found.", output)

    def test_log_action(self):
        log_action(self.log_path, "Test Command")
        self.assertTrue(os.path.exists(self.log_path))

        tree = ET.parse(self.log_path)
        root = tree.getroot()
        events = root.findall('event')
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].find('action').text, "Test Command")

if __name__ == "__main__":
    unittest.main()
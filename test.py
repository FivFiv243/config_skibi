import json
import unittest
import os
import tempfile
import zipfile
import shutil
import xml.etree.ElementTree as ET
from main import read_config, Shell


class TestShellEmulator(unittest.TestCase):
    def setUp(self):
        # Создание временного каталога для тестов
        self.test_dir = tempfile.mkdtemp()
        self.test_zip = os.path.join(self.test_dir, "test.zip")
        self.config_path = os.path.join(self.test_dir, "config.json")

        # Создание тестового ZIP-файла
        with zipfile.ZipFile(self.test_zip, 'w') as zipf:
            zipf.writestr('file1.txt', 'Hello, World!')
            zipf.writestr('dir1/file2.txt', 'Another file')
            zipf.writestr('dir2/file3.log', 'Log file content')

        # Создание тестового конфигурационного файла
        config_data = {
            "vfs_path": self.test_zip
        }
        with open(self.config_path, 'w') as f:
            json.dump(config_data, f)

    def tearDown(self):
        # Удаление временного каталога
        shutil.rmtree(self.test_dir)

    def test_read_config(self):
        vfs_path = read_config(self.config_path)
        self.assertEqual(vfs_path, self.test_zip)

    def test_ls_command(self):
        shell = Shell(self.test_zip)
        output = shell.ls([])
        self.assertIn("file1.txt", output)
        self.assertIn("dir1", output)

    def test_cd_command(self):
        shell = Shell(self.test_zip)
        output = shell.cd('dir1')
        self.assertEqual(shell.get_current_path(), "/dir1")

        output = shell.cd('..')
        self.assertEqual(shell.get_current_path(), "/")

        output = shell.cd('nonexistent')
        self.assertIn("No such directory", output)

    def test_cat_command(self):
        shell = Shell(self.test_zip)
        output = shell.cat(['file1.txt'])
        self.assertEqual(output, 'Hello, World!')

        output = shell.cat(['nonexistent.txt'])
        self.assertIn("File not found", output)

    def test_rmdir_command(self):
        shell = Shell(self.test_zip)
        output = shell.rmdir(['dir1'])
        self.assertIn("Directory removed", output)

        output = shell.rmdir(['nonexistent_dir'])
        self.assertIn("Directory not found", output)

    def test_head_command(self):
        shell = Shell(self.test_zip)
        output = shell.head(['file1.txt'])
        self.assertTrue(output.startswith("Hello, World!"))

        output = shell.head(['nonexistent.txt'])
        self.assertIn("File not found", output)


if __name__ == "__main__":
    unittest.main()

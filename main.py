import json
import os
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
import tkinter as tk
from tkinter import scrolledtext

# Чтение конфигурационного файла JSON
def read_config(config_path):
    with open(config_path, 'r') as file:
        config = json.load(file)
    return config['hostname'], config['vfs_path'], config['log_path']

# Логирование действий в XML
def log_action(log_path, action):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if os.path.exists(log_path) and os.path.getsize(log_path) > 0:
        try:
            tree = ET.parse(log_path)
            root = tree.getroot()
        except ET.ParseError:
            root = ET.Element("log")
    else:
        root = ET.Element("log")

    event = ET.SubElement(root, "event")
    ET.SubElement(event, "action").text = action
    ET.SubElement(event, "timestamp").text = now

    tree = ET.ElementTree(root)
    tree.write(log_path)

# Класс для работы с виртуальной файловой системой
class VirtualFileSystem:
    def __init__(self, zip_path):
        self.root = "MyVirtualMachine"
        self.current_path = self.root
        if os.path.exists(zip_path):
            self.extract_zip(zip_path)
        else:
            raise FileNotFoundError(f"ZIP file not found: {zip_path}")

    def extract_zip(self, zip_path):
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(self.root)

    def list_directory(self):
        items = []
        for item in os.listdir(self.current_path):
            item_path = os.path.join(self.current_path, item)
            stats = os.stat(item_path)
            size = stats.st_size
            modified_time = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            item_type = 'Directory' if os.path.isdir(item_path) else 'File'
            items.append(f"{item_type: <10} {size: <10} {modified_time} {item}")
        return "\n".join(items)

    def change_directory(self, path):
        if path == '..':
            if self.current_path != self.root:
                self.current_path = os.path.dirname(self.current_path)
            else:
                raise FileNotFoundError("You are already at the root directory")
        else:
            new_path = os.path.join(self.current_path, path)
            if os.path.isdir(new_path):
                self.current_path = new_path
            else:
                raise FileNotFoundError("Directory not found")

    def get_relative_path(self):
        return os.path.relpath(self.current_path, self.root).replace('\\', '/')

    def read_file(self, file_name):
        file_path = os.path.join(self.current_path, file_name)
        if os.path.isfile(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    return file.read()
            except UnicodeDecodeError:
                return "Error reading file: unsupported characters"
        else:
            raise FileNotFoundError("File not found")

    def remove_directory(self, dirname):
        dir_path = os.path.join(self.current_path, dirname)
        if os.path.isdir(dir_path):
            os.rmdir(dir_path)
            return f"Directory '{dirname}' removed."
        else:
            raise FileNotFoundError(f"Directory '{dirname}' not found.")

    def read_head(self, filename, n=10):
        file_path = os.path.join(self.current_path, filename)
        if os.path.isfile(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                return "".join(file.readlines()[:n])
        raise FileNotFoundError(f"File '{filename}' not found.")

# Обработчики команд
def ls(vfs):
    try:
        return vfs.list_directory()
    except Exception as e:
        return str(e)

def cd(vfs, path):
    if path.startswith('...') or '...' in path:
        return "Error: More than two consecutive dots are not allowed in the directory path."
    try:
        vfs.change_directory(path)
        return f"Changed directory to {vfs.get_relative_path()}"
    except Exception as e:
        return str(e)

def cat(vfs, file_name):
    try:
        return vfs.read_file(file_name)
    except Exception as e:
        return str(e)

def rmdir(vfs, dirname):
    try:
        return vfs.remove_directory(dirname)
    except Exception as e:
        return str(e)

def head(vfs, filename, n=10):
    try:
        return vfs.read_head(filename, n)
    except Exception as e:
        return str(e)

# Основной цикл Shell
def run_shell(hostname, vfs_path, log_path):
    vfs = VirtualFileSystem(vfs_path)

    def get_prompt():
        relative_path = vfs.get_relative_path()
        return f"PS {hostname}/{relative_path}> " if relative_path != '.' else f"PS {hostname}> "

    def handle_command(event=None):
        full_text = terminal_output.get("end-1l linestart", "end-1c").strip()
        command = full_text.replace(get_prompt(), "").strip()

        if command:
            log_action(log_path, command)
            output = ""

            if command == "ls":
                output = ls(vfs)
            elif command.startswith("cd"):
                parts = command.split(maxsplit=1)
                output = cd(vfs, parts[1]) if len(parts) > 1 else "Please specify a directory."
            elif command.startswith("cat"):
                parts = command.split(maxsplit=1)
                output = cat(vfs, parts[1]) if len(parts) > 1 else "Please specify a file."
            elif command.startswith("rmdir"):
                parts = command.split(maxsplit=1)
                output = rmdir(vfs, parts[1]) if len(parts) > 1 else "Please specify a directory to remove."
            elif command.startswith("head"):
                parts = command.split(maxsplit=2)
                file_name = parts[1] if len(parts) > 1 else ""
                n = int(parts[2]) if len(parts) > 2 else 10
                output = head(vfs, file_name, n)
            elif command == "exit":
                window.quit()
                return
            else:
                output = "Unknown command"

            terminal_output.insert(tk.END, f"\n{output}\n{get_prompt()}")
            terminal_output.see(tk.END)

    window = tk.Tk()
    window.title(f"{hostname} Shell Emulator")

    terminal_output = scrolledtext.ScrolledText(window, width=80, height=20, bg='black', fg='white',
                                                font=('Courier', 10), wrap=tk.WORD)
    terminal_output.grid(row=0, column=0, padx=10, pady=10)
    terminal_output.insert(tk.END, get_prompt())
    terminal_output.bind('<Return>', handle_command)

    window.mainloop()

if __name__ == "__main__":
    hostname, vfs_path, log_path = read_config('config.json')
    run_shell(hostname, vfs_path, log_path)
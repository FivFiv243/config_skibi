import configparser
import os
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime
import tkinter as tk
from tkinter import scrolledtext

# Чтение конфигурационного файла
def read_config(config_path):
    config = configparser.ConfigParser()
    config.read(config_path)
    return config['DEFAULT']['hostname'], config['DEFAULT']['vfs_path'], config['DEFAULT']['log_path']

# Логирование действий в XML
def log_action(log_path, action):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Проверка на существование файла и его содержимого
    if os.path.exists(log_path) and os.path.getsize(log_path) > 0:
        try:
            tree = ET.parse(log_path)
            root = tree.getroot()
        except ET.ParseError:
            # Если файл поврежден, создаем новое дерево
            root = ET.Element("log")
    else:
        # Создаем новое дерево, если файл не существует или пуст
        root = ET.Element("log")

    # Логирование действия
    event = ET.SubElement(root, "event")
    ET.SubElement(event, "action").text = action
    ET.SubElement(event, "timestamp").text = now

    # Сохранение изменений в XML-файл
    tree = ET.ElementTree(root)
    tree.write(log_path)

# Класс для работы с виртуальной файловой системой
class VirtualFileSystem:
    def __init__(self, zip_path):
        self.root = "MyVirtualMachine"
        self.current_path = self.root
        self.extract_zip(zip_path)

    def extract_zip(self, zip_path):
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(self.root)

    def list_directory(self):
        items = []
        for item in os.listdir(self.current_path):
            item_path = os.path.join(self.current_path, item)
            # Получаем информацию о файле
            stats = os.stat(item_path)
            size = stats.st_size  # Размер в байтах
            modified_time = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')  # Время изменения
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

# Основные команды (ls, cd, cat, chown, date)
def ls(vfs):
    try:
        return vfs.list_directory()
    except Exception as e:
        return str(e)

def cd(vfs, path):
    # Проверка на использование более чем двух точек подряд
    if path.startswith('...') or '...' in path:
        return "Error: More than two consecutive dots are not allowed in the directory path."

    try:
        vfs.change_directory(path)
        return f"Changed directory to {vfs.current_path}"
    except Exception as e:
        return str(e)

def run_shell(hostname, vfs_path, log_path):
    vfs = VirtualFileSystem(vfs_path)

    def get_prompt():
        relative_path = vfs.get_relative_path()
        if relative_path == '.':
            relative_path = ''
        return f"PS {hostname}/{relative_path}> " if relative_path else f"PS {hostname}> "

    def handle_command(event=None):
        # Получаем команду без приглашения
        full_text = terminal_output.get("end-1l linestart", "end-1c").strip()
        command = full_text.replace(get_prompt(), "").strip()  # Извлекаем команду без "PS MyVirtualMachine>"

        if command:
            log_action(log_path, command)
            output = ""

            if command.startswith('ls'):
                output = ls(vfs)
            elif command.startswith('cd'):
                try:
                    _, path = command.split(maxsplit=1)
                    output = cd(vfs, path)
                except ValueError:
                    output = "Please specify a directory."
            elif command.startswith('cat'):
                try:
                    _, file_name = command.split(maxsplit=1)
                    output = cat(vfs, file_name)
                except ValueError:
                    output = "Please specify a file."
            elif command.startswith('chown'):
                try:
                    _, file_name, new_owner = command.split(maxsplit=2)
                    output = chown(vfs, file_name, new_owner)
                except ValueError:
                    output = "Usage: chown <file> <new_owner>"
            elif command == 'date':
                output = date()
            elif command == 'exit':
                window.quit()
            else:
                output = "Unknown command"

            terminal_output.insert(tk.END, f"\n{output}\n{get_prompt()}")
            terminal_output.see(tk.END)  # Прокрутка вниз

    window = tk.Tk()
    window.title(f"{hostname} Shell Emulator")

    terminal_output = scrolledtext.ScrolledText(window, width=80, height=20, bg='black', fg='white',
                                                font=('Courier', 10), wrap=tk.WORD)
    terminal_output.grid(row=0, column=0, padx=10, pady=10)
    terminal_output.insert(tk.END, get_prompt())
    terminal_output.bind('<Return>', handle_command)  # Привязка нажатия Enter к выполнению команды

    window.mainloop()

if __name__ == "__main__":
    hostname, vfs_path, log_path = read_config('config.ini')
    run_shell(hostname, vfs_path, log_path)
import os
import zipfile
import json
import tkinter as tk
from tkinter import scrolledtext
from tempfile import TemporaryDirectory


def read_config(path):
    try:
        with open(path, 'r') as f:
            config = json.load(f)
        return config['vfs_path']
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {path}")
    except KeyError as e:
        raise ValueError(f"Missing key in configuration file: {e}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Error parsing configuration file: {e}")


class Shell:
    def __init__(self, zip_path):
        self.temp_dir = TemporaryDirectory()
        self.zip_path = zip_path
        self.cwd = "/"  # Root of the virtual file system
        self.archive = zipfile.ZipFile(zip_path, 'a')  # Open ZIP archive

    def get_relative_path(self):
        return self.cwd

    def __del__(self):
        self.archive.close()
        self.temp_dir.cleanup()

    def run_command(self, command):
        parts = command.split()
        if not parts:
            return "No command entered"

        cmd = parts[0]
        args = parts[1:]

        if cmd == "ls":
            return self.ls(args)
        elif cmd == "cd":
            return self.cd(args[0] if args else "/")
        elif cmd == "cat":
            return self.cat(args)
        elif cmd == "rmdir":
            return self.rmdir(args)
        elif cmd == "head":
            return self.head(args)
        elif cmd == "exit":
            return self.exit()
        else:
            return "Command not found"

    def ls(self, args):
        detailed = "-l" in args
        entries = self.archive.namelist()

        dirs = set()
        files = set()

        for entry in entries:
            if entry.startswith(self.cwd.strip("/")):
                rel_path = entry[len(self.cwd.strip("/")):].strip("/")
                if "/" in rel_path:
                    dirs.add(rel_path.split("/")[0])
                elif rel_path:
                    files.add(rel_path)

        if detailed:
            result = []
            for entry in sorted(dirs | files):
                if entry in dirs:
                    result.append(f"drwxr-xr-x 0 {entry}")
                else:
                    info = next((i for i in self.archive.infolist() if i.filename == f"{self.cwd.strip('/')}/{entry}"), None)
                    size = info.file_size if info else 0
                    result.append(f"-rw-r--r-- {size} {entry}")
            return "\n".join(result)
        else:
            return "\n".join(sorted(dirs | files))

    def cd(self, path):
        if not path:
            path = "/"

        if path == "..":
            if self.cwd == "/":
                return "Already at root directory"
            new_path = '/'.join(self.cwd.strip('/').split('/')[:-1])
            if new_path == "":
                new_path = "/"
            self.cwd = "/" + new_path.lstrip("/")
            return ""

        new_path = os.path.normpath(os.path.join(self.cwd.strip("/"), path)).replace("\\", "/")

        entries = self.archive.namelist()
        matched_dirs = [entry for entry in entries if entry.startswith(new_path + "/")]

        if matched_dirs:
            self.cwd = "/" + new_path.lstrip("/")
            return ""
        else:
            return f"No such directory: {path}"

    def cat(self, args):
        if not args:
            return "Usage: cat <file>"

        file_path = os.path.normpath(os.path.join(self.cwd.strip("/"), args[0])).replace("\\", "/")

        try:
            with self.archive.open(file_path) as f:
                return f.read().decode("utf-8")
        except KeyError:
            return f"File not found: {args[0]}"

    def rmdir(self, args):
        if not args:
            return "Usage: rmdir <directory>"

        dir_path = os.path.normpath(os.path.join(self.cwd.strip("/"), args[0])).replace("\\", "/")

        entries = [entry for entry in self.archive.namelist() if entry.startswith(dir_path + "/")]

        if not entries:
            return f"Directory not found or not empty: {args[0]}"

        with TemporaryDirectory() as temp_dir:
            temp_zip_path = os.path.join(temp_dir, "temp.zip")
            with zipfile.ZipFile(temp_zip_path, 'w') as temp_zip:
                for item in self.archive.infolist():
                    if not item.filename.startswith(dir_path + "/"):
                        with self.archive.open(item.filename) as source:
                            temp_zip.writestr(item, source.read())

            self.archive.close()
            os.replace(temp_zip_path, self.zip_path)
            self.archive = zipfile.ZipFile(self.zip_path, 'a')

        return f"Directory removed: {args[0]}"

    def head(self, args):
        if not args:
            return "Usage: head <file>"

        file_path = os.path.normpath(os.path.join(self.cwd.strip("/"), args[0])).replace("\\", "/")

        try:
            with self.archive.open(file_path) as f:
                lines = f.readlines()
                return "".join(line.decode("utf-8") for line in lines[:10])
        except KeyError:
            return f"File not found: {args[0]}"

    def exit(self):
        return "Exiting shell..."

    def get_current_path(self):
        return self.cwd


def run_shell(vfs_path):
    vfs = Shell(vfs_path)

    def get_prompt():
        relative_path = vfs.get_relative_path()
        return f"VFS {relative_path}> " if relative_path != "/" else "beresta_home/> "

    def handle_command(event=None):
        full_text = terminal_output.get("end-1l linestart", "end-1c").strip()
        command = full_text.replace(get_prompt(), "").strip()
        if command == "exit":
            window.quit()
        output = vfs.run_command(command)
        terminal_output.insert(tk.END, f"\n{output}\n{get_prompt()}")
        terminal_output.see(tk.END)

    window = tk.Tk()
    window.title(f"beresta Shell")

    terminal_output = scrolledtext.ScrolledText(window,
                                   width=80,
                                   height=20,
                                   bg='#8B4513',
                                   fg='#F5DEB3',
                                   font=('Courier', 10, 'bold'),
                                   wrap=tk.WORD)
    terminal_output.grid(row=0, column=0, padx=10, pady=10)
    terminal_output.config(relief='ridge', bd=5, insertbackground='#F5DEB3')
    terminal_output.insert(tk.INSERT, get_prompt())
    terminal_output.bind('<Return>', handle_command)

    window.mainloop()


if __name__ == "__main__":
    try:
        vfs_path = read_config('config.json')
        run_shell(vfs_path)
    except Exception as e:
        print(f"Error: {e}")

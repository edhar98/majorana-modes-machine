from pathlib import Path
import tkinter as tk
from tkinter import ttk


ROOT = Path(__file__).resolve().parent


class FileInspector:
    def __init__(self, window: tk.Tk) -> None:
        self.window: tk.Tk = window
        self.paths: list[Path] = []
        self.window.title(f"Report File Inspector — {ROOT.name}")
        self.window.geometry("1200x760")
        self.window.minsize(760, 480)

        toolbar = ttk.Frame(window, padding=8)
        toolbar.pack(fill=tk.X)
        ttk.Label(toolbar, text=str(ROOT)).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(toolbar, text="Refresh", command=self.refresh).pack(side=tk.RIGHT)

        panes = ttk.Panedwindow(window, orient=tk.HORIZONTAL)
        panes.pack(fill=tk.BOTH, expand=True, padx=8)

        navigation = ttk.Frame(panes)
        preview = ttk.Frame(panes)
        panes.add(navigation, weight=1)
        panes.add(preview, weight=4)

        self.file_list = tk.Listbox(
            navigation,
            activestyle="none",
            exportselection=False,
            font=("TkFixedFont", 10),
        )
        list_scroll = ttk.Scrollbar(
            navigation,
            orient=tk.VERTICAL,
            command=self.file_list.yview,
        )
        self.file_list.configure(yscrollcommand=list_scroll.set)
        self.file_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.text = tk.Text(
            preview,
            wrap=tk.NONE,
            font=("TkFixedFont", 11),
            padx=10,
            pady=8,
            state=tk.DISABLED,
        )
        text_y_scroll = ttk.Scrollbar(
            preview,
            orient=tk.VERTICAL,
            command=self.text.yview,
        )
        text_x_scroll = ttk.Scrollbar(
            preview,
            orient=tk.HORIZONTAL,
            command=self.text.xview,
        )
        self.text.configure(
            yscrollcommand=text_y_scroll.set,
            xscrollcommand=text_x_scroll.set,
        )
        self.text.grid(row=0, column=0, sticky="nsew")
        text_y_scroll.grid(row=0, column=1, sticky="ns")
        text_x_scroll.grid(row=1, column=0, sticky="ew")
        preview.rowconfigure(0, weight=1)
        preview.columnconfigure(0, weight=1)

        self.status = ttk.Label(window, anchor=tk.W, padding=8)
        self.status.pack(fill=tk.X)

        self.file_list.bind("<<ListboxSelect>>", self.show_selected)
        self.window.bind("<Control-r>", self.refresh_event)
        self.refresh()

    def refresh_event(self, _: tk.Event) -> None:
        self.refresh()

    def refresh(self) -> None:
        selected = self.selected_path()
        self.paths = sorted(
            path
            for path in ROOT.rglob("*")
            if path.is_file() and not any(part.startswith(".") for part in path.relative_to(ROOT).parts)
        )
        self.file_list.delete(0, tk.END)
        for path in self.paths:
            self.file_list.insert(tk.END, path.relative_to(ROOT).as_posix())
        if not self.paths:
            self.render("No files found.")
            self.status.configure(text="0 files")
            return
        index = self.paths.index(selected) if selected in self.paths else 0
        self.file_list.selection_set(index)
        self.file_list.activate(index)
        self.file_list.see(index)
        self.show_path(self.paths[index])

    def selected_path(self) -> Path | None:
        selected = self.file_list.curselection()
        return self.paths[selected[0]] if selected else None

    def show_selected(self, _: tk.Event) -> None:
        path = self.selected_path()
        if path is not None:
            self.show_path(path)

    def show_path(self, path: Path) -> None:
        try:
            data = path.read_bytes()
        except OSError as error:
            self.render(f"Unable to read {path.name}\n\n{error}")
            self.status.configure(text=str(error))
            return
        relative = path.relative_to(ROOT).as_posix()
        if b"\0" in data:
            self.render(f"{relative}\n\nBinary file\n{len(data):,} bytes")
            self.status.configure(text=f"{relative} — binary — {len(data):,} bytes")
            return
        try:
            content = data.decode("utf-8")
        except UnicodeDecodeError:
            self.render(f"{relative}\n\nNon-UTF-8 file\n{len(data):,} bytes")
            self.status.configure(text=f"{relative} — non-UTF-8 — {len(data):,} bytes")
            return
        lines = content.splitlines()
        width = max(1, len(str(len(lines))))
        numbered = "\n".join(
            f"{number:>{width}}  {line}"
            for number, line in enumerate(lines, start=1)
        )
        self.render(numbered)
        self.status.configure(
            text=f"{relative} — {len(lines):,} lines — {len(data):,} bytes"
        )

    def render(self, content: str) -> None:
        self.text.configure(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", content)
        self.text.configure(state=tk.DISABLED)


def main() -> None:
    window = tk.Tk()
    FileInspector(window)
    window.mainloop()


if __name__ == "__main__":
    main()

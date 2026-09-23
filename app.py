import json
import os
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk


class PythonLiteIDE(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Python Lite IDE")
        self.geometry("1280x820")
        self.minsize(980, 640)
        self.configure(bg="#0a1030")

        self.workspace_root = Path.cwd()
        self.tree_visible = True
        self.live_mode = tk.BooleanVar(value=False)
        self.expand_all_notes = tk.BooleanVar(value=False)
        self.bg_mode = tk.StringVar(value="dark")

        self.process = None
        self.process_thread = None
        self.current_process_temp_file = None

        self.tabs = []
        self.current_tab_index = None

        self.notes_path = Path("notes.json")
        self.notes_data = self._load_notes()

        self.wallpaper_path = None
        self.wallpaper_image = None
        self.wallpaper_label = None

        self._setup_style()
        self._build_ui()
        self._create_new_tab()
        self._refresh_file_tree()

    def _setup_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Glass.Treeview", background="#152446", foreground="#d5e4ff", fieldbackground="#152446", borderwidth=0)
        style.configure("Glass.Treeview.Heading", background="#1a2a55", foreground="#b8d2ff", relief="flat")

    def _build_ui(self):
        self.top_bar = tk.Frame(self, bg="#0f1b42", height=56, highlightbackground="#4f7dff", highlightthickness=1)
        self.top_bar.pack(fill="x", padx=14, pady=(14, 8))

        self.menu_btn = self._icon_btn(self.top_bar, "☰", self._show_main_menu)
        self.menu_btn.pack(side="left", padx=8, pady=8)

        self.tabs_bar = tk.Frame(self.top_bar, bg="#0f1b42")
        self.tabs_bar.pack(side="left", fill="x", expand=True, padx=8)

        controls = tk.Frame(self.top_bar, bg="#0f1b42")
        controls.pack(side="right", padx=8)

        self.run_btn = self._icon_btn(controls, "▶", self.run_active_file)
        self.run_btn.pack(side="left", padx=4, pady=8)

        self.stop_btn = self._icon_btn(controls, "■", self.stop_execution)
        self.stop_btn.pack(side="left", padx=4, pady=8)

        self.live_badge = tk.Label(
            controls,
            text="LIVE",
            fg="#6de6ff",
            bg="#1a2e52",
            font=("Helvetica", 11, "bold"),
            padx=10,
            pady=7,
            cursor="hand2",
        )
        self.live_badge.pack(side="left", padx=(4, 4), pady=8)
        self.live_badge.bind("<Button-1>", lambda _: self.toggle_live_mode())

        self.live_dot = tk.Canvas(controls, width=22, height=22, bg="#0f1b42", highlightthickness=0)
        self.live_dot.pack(side="left", padx=(0, 2), pady=8)

        self.note_btn = self._icon_btn(controls, "📝", self.toggle_notes_drawer)
        self.note_btn.pack(side="left", padx=(4, 0), pady=8)

        self.main_area = tk.Frame(self, bg="#0a1030")
        self.main_area.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        self.paned = tk.PanedWindow(self.main_area, orient="horizontal", sashwidth=5, bg="#0a1030")
        self.paned.pack(fill="both", expand=True)

        self.left_panel = tk.Frame(self.paned, bg="#132142", highlightbackground="#4f7dff", highlightthickness=1)
        self.paned.add(self.left_panel, minsize=200, width=260)

        self.tree = ttk.Treeview(self.left_panel, style="Glass.Treeview")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree.bind("<Double-1>", self._on_tree_open)

        self.right_panel = tk.Frame(self.paned, bg="#0a1030")
        self.paned.add(self.right_panel)

        self.editor_wrap = tk.Frame(self.right_panel, bg="#152446", highlightbackground="#4f7dff", highlightthickness=1)
        self.editor_wrap.pack(fill="both", expand=True)

        self.editor = tk.Text(
            self.editor_wrap,
            bg="#1a204f",
            fg="#d5e4ff",
            insertbackground="#c9f1ff",
            relief="flat",
            padx=16,
            pady=16,
            undo=True,
            font=("Menlo", 13),
            selectbackground="#3a5aa8",
            wrap="none",
        )
        self.editor.pack(fill="both", expand=True)
        self.editor.bind("<Button-3>", self._show_editor_context)
        self.editor.bind("<KeyRelease>", self._on_editor_key_release)

        self.output_wrap = tk.Frame(self.right_panel, bg="#152446", highlightbackground="#4f7dff", highlightthickness=1, height=190)
        self.output_wrap.pack(fill="x", pady=(8, 0))
        self.output_wrap.pack_propagate(False)

        self.output_title = tk.Label(self.output_wrap, text="OUTPUT", bg="#152446", fg="#7bc6ff", font=("Helvetica", 12, "bold"), anchor="w")
        self.output_title.pack(fill="x", padx=12, pady=(8, 2))

        self.output = tk.Text(
            self.output_wrap,
            bg="#201650",
            fg="#9ff5dd",
            relief="flat",
            height=7,
            state="disabled",
            padx=12,
            pady=6,
            font=("Menlo", 12),
        )
        self.output.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._build_notes_drawer()
        self._refresh_live_state()

    def _icon_btn(self, parent, symbol, command):
        return tk.Button(
            parent,
            text=symbol,
            command=command,
            bg="#1f315f",
            fg="#8be9ff",
            activebackground="#2d4a82",
            activeforeground="#d9f8ff",
            relief="flat",
            bd=0,
            padx=12,
            pady=8,
            font=("Helvetica", 13, "bold"),
            cursor="hand2",
        )

    def _build_notes_drawer(self):
        self.notes_open = False
        self.notes_target_x = self.winfo_width()
        self.notes_drawer = tk.Frame(self, bg="#131c45", highlightbackground="#6da4ff", highlightthickness=1)
        self.notes_drawer.place(x=self.winfo_width(), y=70, width=370, height=self.winfo_height() - 84)

        top = tk.Frame(self.notes_drawer, bg="#131c45")
        top.pack(fill="x", padx=10, pady=10)

        tk.Label(top, text="DSA Notebook", bg="#131c45", fg="#c8e6ff", font=("Helvetica", 13, "bold")).pack(side="left")
        tk.Checkbutton(
            top,
            text="Expand All",
            variable=self.expand_all_notes,
            command=self._render_notes_tree,
            bg="#131c45",
            fg="#9dc6ff",
            activebackground="#131c45",
            activeforeground="#9dc6ff",
            selectcolor="#22315f",
        ).pack(side="right")

        add_row = tk.Frame(self.notes_drawer, bg="#131c45")
        add_row.pack(fill="x", padx=10)
        tk.Button(add_row, text="+ Category", command=self._add_category, bg="#21386c", fg="#cce8ff", relief="flat").pack(side="left", padx=(0, 6))
        tk.Button(add_row, text="+ Note", command=self._add_note, bg="#21386c", fg="#cce8ff", relief="flat").pack(side="left")

        self.notes_tree = ttk.Treeview(self.notes_drawer, style="Glass.Treeview")
        self.notes_tree.pack(fill="x", padx=10, pady=(10, 8), ipady=40)
        self.notes_tree.bind("<<TreeviewSelect>>", self._on_note_select)

        self.note_editor = tk.Text(self.notes_drawer, bg="#1a204f", fg="#d5e4ff", relief="flat", height=10, padx=10, pady=10, font=("Menlo", 11))
        self.note_editor.pack(fill="both", expand=True, padx=10, pady=(0, 8))

        actions = tk.Frame(self.notes_drawer, bg="#131c45")
        actions.pack(fill="x", padx=10, pady=(0, 10))
        tk.Button(actions, text="Save Note", command=self._save_selected_note, bg="#244478", fg="#d8ecff", relief="flat").pack(side="left", padx=(0, 5))
        tk.Button(actions, text="Run Note", command=self._run_selected_note, bg="#244478", fg="#d8ecff", relief="flat").pack(side="left", padx=5)
        tk.Button(actions, text="Insert to Editor", command=self._insert_note_to_editor, bg="#244478", fg="#d8ecff", relief="flat").pack(side="left", padx=5)

        self._render_notes_tree()

    def _show_main_menu(self):
        menu = tk.Menu(self, tearoff=0, bg="#182a52", fg="#d9ebff", activebackground="#294b87", activeforeground="#ffffff")
        menu.add_command(label="Toggle File Tree", command=self.toggle_file_tree)
        menu.add_command(label="Open Folder", command=self.open_folder)
        menu.add_command(label="Open Python File", command=self.open_python_file)
        menu.add_command(label="New Python Tab", command=self._create_new_tab)
        menu.add_separator()
        menu.add_command(label="Save", command=self.save_active_file)
        menu.add_command(label="Run", command=self.run_active_file)
        menu.add_command(label="Stop", command=self.stop_execution)
        menu.add_command(label="Toggle Live Mode", command=self.toggle_live_mode)
        menu.add_separator()
        menu.add_command(label="Background: Solid Dark", command=lambda: self.set_background_mode("dark"))
        menu.add_command(label="Background: Wallpaper", command=self.enable_wallpaper_mode)
        menu.tk_popup(self.menu_btn.winfo_rootx(), self.menu_btn.winfo_rooty() + self.menu_btn.winfo_height())

    def set_background_mode(self, mode):
        self.bg_mode.set(mode)
        if mode == "dark":
            if self.wallpaper_label:
                self.wallpaper_label.place_forget()
        else:
            self.enable_wallpaper_mode()

    def enable_wallpaper_mode(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.png")])
        if not path:
            return
        self.wallpaper_path = path
        self.bg_mode.set("wallpaper")
        try:
            self.wallpaper_image = tk.PhotoImage(file=path)
        except Exception:
            messagebox.showerror("Wallpaper", "Only PNG wallpaper is supported in this lightweight build.")
            return

        if self.wallpaper_label is None:
            self.wallpaper_label = tk.Label(self, image=self.wallpaper_image)
        else:
            self.wallpaper_label.configure(image=self.wallpaper_image)
        self.wallpaper_label.image = self.wallpaper_image
        self.wallpaper_label.place(x=0, y=0, relwidth=1, relheight=1)
        self.wallpaper_label.lower()

    def _create_new_tab(self, file_path=None, content=""):
        if file_path and not str(file_path).endswith(".py"):
            messagebox.showinfo("Python only", "Only Python files are supported.")
            return

        self._persist_current_tab_text()
        tab = {
            "path": Path(file_path) if file_path else None,
            "title": Path(file_path).name if file_path else "untitled.py",
            "content": content,
        }
        self.tabs.append(tab)
        self.current_tab_index = len(self.tabs) - 1
        self._render_tabs()
        self._load_current_tab_text()

    def _render_tabs(self):
        for child in self.tabs_bar.winfo_children():
            child.destroy()

        for idx, tab in enumerate(self.tabs):
            active = idx == self.current_tab_index
            wrap = tk.Frame(self.tabs_bar, bg="#5ba4ff" if active else "#1e325f", padx=1, pady=1)
            wrap.pack(side="left", padx=4, pady=8)

            btn = tk.Button(
                wrap,
                text=tab["title"],
                command=lambda i=idx: self._switch_tab(i),
                relief="flat",
                bg="#2f4f86" if active else "#223b6d",
                fg="#dff2ff",
                padx=10,
                pady=4,
            )
            btn.pack(side="left")

            close_btn = tk.Button(
                wrap,
                text="×",
                command=lambda i=idx: self._close_tab(i),
                relief="flat",
                bg="#2f4f86" if active else "#223b6d",
                fg="#b9d8ff",
                padx=5,
                pady=4,
            )
            close_btn.pack(side="left")

    def _switch_tab(self, index):
        self._persist_current_tab_text()
        self.current_tab_index = index
        self._render_tabs()
        self._load_current_tab_text()

    def _close_tab(self, index):
        if len(self.tabs) == 1:
            self.tabs[0] = {"path": None, "title": "untitled.py", "content": ""}
            self.current_tab_index = 0
            self._render_tabs()
            self._load_current_tab_text()
            return

        del self.tabs[index]
        if self.current_tab_index >= len(self.tabs):
            self.current_tab_index = len(self.tabs) - 1
        self._render_tabs()
        self._load_current_tab_text()

    def _persist_current_tab_text(self):
        if self.current_tab_index is None:
            return
        self.tabs[self.current_tab_index]["content"] = self.editor.get("1.0", "end-1c")

    def _load_current_tab_text(self):
        if self.current_tab_index is None:
            return
        tab = self.tabs[self.current_tab_index]
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", tab["content"])
        self._update_window_title()

    def _update_window_title(self):
        if self.current_tab_index is None:
            return
        name = self.tabs[self.current_tab_index]["title"]
        self.title(f"Python Lite IDE - {name}")

    def toggle_file_tree(self):
        if self.tree_visible:
            self.paned.forget(self.left_panel)
        else:
            self.paned.insert(0, self.left_panel)
        self.tree_visible = not self.tree_visible

    def open_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return
        self.workspace_root = Path(folder)
        self._refresh_file_tree()

    def _refresh_file_tree(self):
        self.tree.delete(*self.tree.get_children())
        root_id = self.tree.insert("", "end", text=f"📁 {self.workspace_root.name}", values=[str(self.workspace_root)])
        self._insert_tree_nodes(root_id, self.workspace_root)

    def _insert_tree_nodes(self, parent, path):
        try:
            entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except Exception:
            return

        for entry in entries:
            if entry.name.startswith("."):
                continue
            if entry.is_dir():
                node = self.tree.insert(parent, "end", text=f"📂 {entry.name}", values=[str(entry)])
                self._insert_tree_nodes(node, entry)
            elif entry.suffix == ".py":
                self.tree.insert(parent, "end", text=f"🐍 {entry.name}", values=[str(entry)])

    def _on_tree_open(self, _event):
        selected = self.tree.selection()
        if not selected:
            return
        path_str = self.tree.item(selected[0], "values")
        if not path_str:
            return

        path = Path(path_str[0])
        if path.is_file() and path.suffix == ".py":
            content = path.read_text(encoding="utf-8", errors="ignore")
            for idx, tab in enumerate(self.tabs):
                if tab["path"] == path:
                    self._switch_tab(idx)
                    return
            self._create_new_tab(path, content)

    def open_python_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Python", "*.py")])
        if not file_path:
            return
        path = Path(file_path)
        content = path.read_text(encoding="utf-8", errors="ignore")
        self._create_new_tab(path, content)

    def save_active_file(self):
        if self.current_tab_index is None:
            return

        self._persist_current_tab_text()
        tab = self.tabs[self.current_tab_index]
        if tab["path"] is None:
            save_path = filedialog.asksaveasfilename(defaultextension=".py", filetypes=[("Python", "*.py")])
            if not save_path:
                return
            if not save_path.endswith(".py"):
                messagebox.showinfo("Python only", "Only .py files are allowed.")
                return
            tab["path"] = Path(save_path)
            tab["title"] = tab["path"].name

        tab["path"].write_text(tab["content"], encoding="utf-8")
        self._render_tabs()
        self._append_output(f"Saved: {tab['title']}\n")

        if self.live_mode.get():
            if tab["content"].strip():
                self.run_active_file()
            else:
                self.stop_execution(clear_output=True)

    def run_active_file(self):
        if self.current_tab_index is None:
            return

        self._persist_current_tab_text()
        tab = self.tabs[self.current_tab_index]
        code = tab["content"]

        if not code.strip():
            self.stop_execution(clear_output=True)
            return

        if tab["path"] and tab["path"].exists():
            run_path = str(tab["path"])
            self._append_output("Running saved file...\n", clear=True)
            self._start_process([sys.executable, "-u", run_path])
        else:
            self._append_output("Running unsaved code...\n", clear=True)
            self._run_code_snippet(code)

    def _run_code_snippet(self, code):
        if self.process and self.process.poll() is None:
            self.stop_execution()

        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tmp:
            tmp.write(code)
            temp_path = tmp.name

        self.current_process_temp_file = temp_path
        self._start_process([sys.executable, "-u", temp_path])

    def _start_process(self, command):
        if self.process and self.process.poll() is None:
            self.stop_execution()

        try:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=str(self.workspace_root),
            )
        except Exception as ex:
            self._append_output(f"Failed to run: {ex}\n")
            return

        def stream_output():
            if not self.process or not self.process.stdout:
                return
            for line in self.process.stdout:
                self.after(0, lambda l=line: self._append_output(l))
            rc = self.process.wait()
            self.after(0, lambda: self._append_output(f"Run completed: {'Success' if rc == 0 else 'Failed'}\n"))
            if self.current_process_temp_file:
                try:
                    os.remove(self.current_process_temp_file)
                except OSError:
                    pass
                self.current_process_temp_file = None

        self.process_thread = threading.Thread(target=stream_output, daemon=True)
        self.process_thread.start()

    def stop_execution(self, clear_output=False):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self._append_output("Process stopped.\n")
        self.process = None

        if self.current_process_temp_file:
            try:
                os.remove(self.current_process_temp_file)
            except OSError:
                pass
            self.current_process_temp_file = None

        if clear_output:
            self._append_output("", clear=True)

    def _append_output(self, text, clear=False):
        self.output.configure(state="normal")
        if clear:
            self.output.delete("1.0", "end")
        self.output.insert("end", text)
        self.output.see("end")
        self.output.configure(state="disabled")

    def toggle_live_mode(self):
        self.live_mode.set(not self.live_mode.get())
        self._refresh_live_state()

    def _refresh_live_state(self):
        color = "#47f28a" if self.live_mode.get() else "#6b7ca6"
        self.live_dot.delete("all")
        self.live_dot.create_oval(5, 5, 17, 17, fill=color, outline="")
        self.output_title.configure(text="OUTPUT  • LIVE" if self.live_mode.get() else "OUTPUT")

    def _on_editor_key_release(self, _event):
        if self.current_tab_index is None:
            return
        self._persist_current_tab_text()
        if not self.tabs[self.current_tab_index]["content"].strip():
            self.stop_execution(clear_output=True)

    def _show_editor_context(self, event):
        menu = tk.Menu(self, tearoff=0, bg="#182a52", fg="#d9ebff", activebackground="#294b87", activeforeground="#ffffff")
        menu.add_command(label="Run Selection", command=self.run_selection)
        menu.add_command(label="Save as Note", command=self.save_selection_as_note)
        menu.add_command(label="Stop", command=self.stop_execution)
        menu.add_command(label="Toggle Live Mode", command=self.toggle_live_mode)
        menu.tk_popup(event.x_root, event.y_root)

    def run_selection(self):
        try:
            code = self.editor.get("sel.first", "sel.last")
        except tk.TclError:
            messagebox.showinfo("Run Selection", "Select Python code first.")
            return
        self._append_output("Running selection...\n", clear=True)
        self._run_code_snippet(code)

    def save_selection_as_note(self):
        try:
            code = self.editor.get("sel.first", "sel.last")
        except tk.TclError:
            messagebox.showinfo("Save as Note", "Select code first.")
            return

        categories = list(self.notes_data.keys())
        if not categories:
            categories = ["General"]
            self.notes_data["General"] = []

        category = simpledialog.askstring("Category", f"Enter category ({', '.join(categories)}):")
        if not category:
            return
        title = simpledialog.askstring("Note Title", "Enter note title:")
        if not title:
            return

        self.notes_data.setdefault(category, []).append({"title": title, "code": code, "output": ""})
        self._save_notes()
        self._render_notes_tree()

    def _load_notes(self):
        if not self.notes_path.exists():
            return {
                "Sorting Algorithms": [],
                "Trees & Graphs": [],
                "Dynamic Programming": [],
            }
        try:
            return json.loads(self.notes_path.read_text(encoding="utf-8"))
        except Exception:
            return {"General": []}

    def _save_notes(self):
        self.notes_path.write_text(json.dumps(self.notes_data, indent=2), encoding="utf-8")

    def _render_notes_tree(self):
        self.notes_tree.delete(*self.notes_tree.get_children())
        for category, notes in self.notes_data.items():
            cat_id = self.notes_tree.insert("", "end", text=f"📚 {category}", values=["category", category])
            for idx, note in enumerate(notes):
                self.notes_tree.insert(cat_id, "end", text=f"📝 {note['title']}", values=["note", category, idx])
            if self.expand_all_notes.get():
                self.notes_tree.item(cat_id, open=True)

    def _on_note_select(self, _event):
        selected = self.notes_tree.selection()
        if not selected:
            return

        data = self.notes_tree.item(selected[0], "values")
        if not data:
            return

        if data[0] == "category" and not self.expand_all_notes.get():
            for item in self.notes_tree.get_children():
                self.notes_tree.item(item, open=False)
            self.notes_tree.item(selected[0], open=True)
            self.note_editor.delete("1.0", "end")
            return

        if data[0] == "note":
            category = data[1]
            idx = int(data[2])
            note = self.notes_data[category][idx]
            body = note["code"]
            if note.get("output"):
                body += "\n\n# Saved Output\n" + note["output"]
            self.note_editor.delete("1.0", "end")
            self.note_editor.insert("1.0", body)

    def _selected_note_ref(self):
        selected = self.notes_tree.selection()
        if not selected:
            return None
        data = self.notes_tree.item(selected[0], "values")
        if not data or data[0] != "note":
            return None
        return data[1], int(data[2])

    def _save_selected_note(self):
        note_ref = self._selected_note_ref()
        if not note_ref:
            messagebox.showinfo("Notebook", "Select a note first.")
            return

        category, idx = note_ref
        text = self.note_editor.get("1.0", "end-1c")
        note = self.notes_data[category][idx]
        note["code"] = text
        self._save_notes()
        self._append_output("Note saved.\n")

    def _run_selected_note(self):
        note_ref = self._selected_note_ref()
        if not note_ref:
            messagebox.showinfo("Notebook", "Select a note first.")
            return

        category, idx = note_ref
        note = self.notes_data[category][idx]
        self._append_output("Running note...\n", clear=True)
        self._run_code_snippet(note["code"])

        def ask_to_save_output():
            out = self.output.get("1.0", "end-1c")
            if out.strip() and messagebox.askyesno("Save Output", "Save output lines in this note?"):
                note["output"] = out
                self._save_notes()

        self.after(1300, ask_to_save_output)

    def _insert_note_to_editor(self):
        note_ref = self._selected_note_ref()
        if not note_ref:
            messagebox.showinfo("Notebook", "Select a note first.")
            return
        category, idx = note_ref
        note = self.notes_data[category][idx]
        self.editor.insert("insert", note["code"])

    def _add_category(self):
        name = simpledialog.askstring("Category", "Category name:")
        if not name:
            return
        if name in self.notes_data:
            messagebox.showinfo("Notebook", "Category already exists.")
            return
        self.notes_data[name] = []
        self._save_notes()
        self._render_notes_tree()

    def _add_note(self):
        if not self.notes_data:
            self.notes_data["General"] = []
        category = simpledialog.askstring("Category", "Category name for note:")
        if not category:
            return
        self.notes_data.setdefault(category, [])
        title = simpledialog.askstring("Note title", "Note title:")
        if not title:
            return
        self.notes_data[category].append({"title": title, "code": "", "output": ""})
        self._save_notes()
        self._render_notes_tree()

    def toggle_notes_drawer(self):
        self.notes_open = not self.notes_open
        self._animate_drawer()

    def _animate_drawer(self):
        self.update_idletasks()
        screen_w = self.winfo_width()
        drawer_w = 370
        current_x = self.notes_drawer.winfo_x()
        target_x = screen_w - drawer_w - 10 if self.notes_open else screen_w + 4

        if self.notes_open:
            self.notes_drawer.lift()

        if abs(current_x - target_x) <= 8:
            self.notes_drawer.place(x=target_x, y=70, width=drawer_w, height=self.winfo_height() - 84)
            if not self.notes_open:
                self.notes_drawer.lower()
            return

        step = 20 if target_x > current_x else -20
        self.notes_drawer.place(x=current_x + step, y=70, width=drawer_w, height=self.winfo_height() - 84)
        self.after(10, self._animate_drawer)


def main():
    app = PythonLiteIDE()
    app.mainloop()


if __name__ == "__main__":
    main()

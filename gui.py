"""Tkinter GUI for converting between bigfart files and L0 backups. (ai gen entire file)"""

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from main import UnsureWhichBigFartLevelToPick, bigfart_to_l0, l0_to_bigfart


class ConverterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("bigfart <-> L0 Converter")
        root.geometry("620x300")
        root.minsize(520, 280)

        # Bottom bar: status text on the left, indeterminate progress on the right.
        bottom = ttk.Frame(root)
        bottom.pack(side="bottom", fill="x")
        bottom.columnconfigure(0, weight=1)

        self.status = tk.StringVar(value="Ready")
        self.status_label = ttk.Label(
            bottom,
            textvariable=self.status,
            anchor="w",
            relief="sunken",
            padding=(6, 3),
        )
        self.status_label.grid(row=0, column=0, sticky="ew")

        self.progress = ttk.Progressbar(bottom, mode="indeterminate", length=160)
        self.progress.grid(row=0, column=1, padx=(6, 6), pady=3)
        self.progress.grid_remove()  # hidden until a conversion starts

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.to_l0_tab = ttk.Frame(notebook, padding=12)
        self.to_bigfart_tab = ttk.Frame(notebook, padding=12)
        notebook.add(self.to_l0_tab, text="bigfart \u2192 L0")
        notebook.add(self.to_bigfart_tab, text="L0 \u2192 bigfart")

        self._build_to_l0_tab()
        self._build_to_bigfart_tab()

    # ------------------------------------------------------------------ UI ---

    def _build_to_l0_tab(self) -> None:
        self.l0_input = tk.StringVar()
        self.l0_output = tk.StringVar()
        self.l0_level_id = tk.StringVar()

        self._file_row(
            self.to_l0_tab, 0, "Input bigfart:", self.l0_input, self._pick_l0_input
        )
        self._file_row(
            self.to_l0_tab, 1, "Output L0:", self.l0_output, self._pick_l0_output
        )

        ttk.Label(self.to_l0_tab, text="Level ID (optional):").grid(
            row=2, column=0, sticky="w", pady=(10, 0)
        )
        ttk.Entry(self.to_l0_tab, textvariable=self.l0_level_id).grid(
            row=2, column=1, columnspan=2, sticky="ew", pady=(10, 0), padx=(6, 0)
        )
        ttk.Label(
            self.to_l0_tab,
            text="Only needed if the bigfart contains multiple levels.",
            foreground="#666666",
        ).grid(row=3, column=1, columnspan=2, sticky="w", padx=(6, 0))

        self.l0_button = ttk.Button(
            self.to_l0_tab, text="Convert to L0", command=self._run_to_l0
        )
        self.l0_button.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(20, 0))

        self.to_l0_tab.columnconfigure(1, weight=1)

    def _build_to_bigfart_tab(self) -> None:
        self.bf_input = tk.StringVar()
        self.bf_output = tk.StringVar()

        self._file_row(
            self.to_bigfart_tab, 0, "Input L0:", self.bf_input, self._pick_bf_input
        )
        self._file_row(
            self.to_bigfart_tab, 1, "Output bigfart:", self.bf_output, self._pick_bf_output
        )

        self.bf_button = ttk.Button(
            self.to_bigfart_tab, text="Convert to bigfart", command=self._run_to_bigfart
        )
        self.bf_button.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(20, 0))

        self.to_bigfart_tab.columnconfigure(1, weight=1)

    def _file_row(self, parent, row, label, var, browse_cmd) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(parent, textvariable=var).grid(
            row=row, column=1, sticky="ew", pady=4, padx=(6, 6)
        )
        ttk.Button(parent, text="Browse\u2026", command=browse_cmd).grid(
            row=row, column=2, pady=4
        )

    # ------------------------------------------------------------- pickers ---

    def _pick_l0_input(self) -> None:
        path = filedialog.askopenfilename(title="Select bigfart file",initialfile="bigfart1337")
        if path:
            self.l0_input.set(path)

    def _pick_l0_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save L0 file", initialfile="L0"
        )
        if path:
            self.l0_output.set(path)

    def _pick_bf_input(self) -> None:
        path = filedialog.askopenfilename(title="Select L0 file",initialfile="L0")
        if path:
            self.bf_input.set(path)

    def _pick_bf_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Save bigfart file", initialfile="bigfart1337"
        )
        if path:
            self.bf_output.set(path)

    # --------------------------------------------------------------- logic ---

    def _validate(self, input_str: str, output_str: str):
        if not input_str:
            messagebox.showerror("Error", "Please choose an input file.")
            return None
        if not output_str:
            messagebox.showerror("Error", "Please choose an output file.")
            return None

        in_path = Path(input_str)
        out_path = Path(output_str)

        if not in_path.is_file():
            messagebox.showerror("Error", f"Input file does not exist:\n{in_path}")
            return None

        if out_path.exists():
            if not messagebox.askyesno(
                "Overwrite?",
                f"Output file already exists:\n{out_path}\n\nOverwrite it?",
            ):
                return None

        return in_path, out_path

    def _run_to_l0(self) -> None:
        paths = self._validate(self.l0_input.get(), self.l0_output.get())
        if paths is None:
            return
        in_path, out_path = paths
        level_id = self.l0_level_id.get().strip() or None

        def work() -> None:
            try:
                result = bigfart_to_l0(in_path, level_id)
                out_path.write_bytes(result.lo_bytes)
                self._after(
                    lambda: self._done(
                        f"Saved L0 file to:\n{out_path}\n\n"
                        f"Is adventure: {result.is_adventure}"
                    )
                )
            except UnsureWhichBigFartLevelToPick as exc:
                self._after(lambda exc=exc: self._show_level_picker(exc))
            except Exception as exc:  # noqa: BLE001 - surface any failure to the user
                self._after(lambda exc=exc: self._error(exc))

        self._start(work)

    def _run_to_bigfart(self) -> None:
        paths = self._validate(self.bf_input.get(), self.bf_output.get())
        if paths is None:
            return
        in_path, out_path = paths

        def work() -> None:
            try:
                l0_bytes = in_path.read_bytes()
                l0_to_bigfart(l0_bytes, out_path)
                self._after(lambda: self._done(f"Saved bigfart file to:\n{out_path}"))
            except Exception as exc:  # noqa: BLE001
                self._after(lambda exc=exc: self._error(exc))

        self._start(work)

    # ------------------------------------------------------ level selection ---

    def _show_level_picker(self, exc: UnsureWhichBigFartLevelToPick) -> None:
        """Show a dialog listing the available levels so the user can pick an ID."""
        self._stop_progress()
        self.status.set("Choose a level")
        self._set_buttons(True)

        win = tk.Toplevel(self.root)
        win.title("Which level?")
        win.geometry("520x380")
        win.minsize(420, 280)
        win.transient(self.root)
        win.grab_set()

        # The message from the exception, with the level list stripped out.
        ttk.Label(
            win,
            text=exc.message_without_level_names_and_ids,
            wraplength=480,
            justify="left",
            padding=(12, 12),
        ).pack(fill="x")

        tree_frame = ttk.Frame(win, padding=(12, 0))
        tree_frame.pack(fill="both", expand=True)

        tree = ttk.Treeview(
            tree_frame,
            columns=("id", "name"),
            show="headings",
            selectmode="browse",
        )
        tree.heading("id", text="Level ID")
        tree.heading("name", text="Level name")
        tree.column("id", width=150, stretch=False)
        tree.column("name", width=320, stretch=True)

        for level in exc.levels_names_and_ids:
            tree.insert("", "end", values=(level.level_id, level.level_name))

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        if exc.levels_names_and_ids:
            first = tree.get_children()[0]
            tree.selection_set(first)
            tree.focus(first)

        feedback = tk.StringVar(value="Select a level, then use its ID.")
        ttk.Label(
            win, textvariable=feedback, padding=(12, 6), foreground="#666666"
        ).pack(fill="x")

        def selected_level_id() -> str | None:
            selection = tree.selection()
            if not selection:
                feedback.set("Select a level first.")
                return None
            return tree.item(selection[0], "values")[0]

        def use_id() -> None:
            level_id = selected_level_id()
            if level_id is None:
                return
            self.l0_level_id.set(level_id)
            win.destroy()
            self.status.set("Ready")

        def close() -> None:
            win.destroy()
            self.status.set("Ready")

        # Double-click a row to apply it directly.
        tree.bind("<Double-1>", lambda _event: use_id())

        button_row = ttk.Frame(win, padding=(12, 0, 12, 12))
        button_row.pack(fill="x")
        ttk.Button(button_row, text="Use this ID", command=use_id).pack(
            side="left"
        )
        ttk.Button(button_row, text="Close", command=close).pack(side="right")

        win.protocol("WM_DELETE_WINDOW", close)
        win.wait_window()

    # ------------------------------------------------------------ threading ---

    def _start(self, work) -> None:
        self.status.set("Working\u2026")
        self._set_buttons(False)
        self.progress.grid()
        self.progress.start(15)  # 15 ms per animation step
        threading.Thread(target=work, daemon=True).start()

    def _after(self, fn) -> None:
        self.root.after(0, fn)

    def _done(self, message: str) -> None:
        self._stop_progress()
        self.status.set("Done")
        self._set_buttons(True)
        messagebox.showinfo("Success", message)

    def _error(self, exc: Exception) -> None:
        self._stop_progress()
        self.status.set("Error")
        self._set_buttons(True)
        messagebox.showerror("Conversion failed", str(exc) or repr(exc))

    def _set_buttons(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.l0_button.configure(state=state)
        self.bf_button.configure(state=state)

    def _stop_progress(self) -> None:
        self.progress.stop()
        self.progress.grid_remove()


def main() -> None:
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista" if "vista" in ttk.Style().theme_names() else "clam")
    except tk.TclError:
        pass
    ConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
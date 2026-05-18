import keyboard
import mouse
import threading
import time
import win32gui
import win32process
import psutil
import tkinter as tk
from tkinter import font as tkfont
import json
import os

INTERVAL   = 0.5
HOLD       = 0.08
TARGET_EXE = "pxgme.exe"
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_TOGGLE = {"type": "mouse", "button": "middle", "label": "Scroll (meio)"}

script_enabled  = False
running         = False
key1            = ""
key2            = ""
current         = 1
lock            = threading.Lock()
wake            = threading.Event()
wasd_hooks      = []
toggle_hook_ref  = None
toggle_hook_type = None
toggle_key_info  = dict(DEFAULT_TOGGLE)
capturing       = False

gui_queue = []
gui_lock  = threading.Lock()


def push_event(event: dict):
    with gui_lock:
        gui_queue.append(event)


# --- Config ---

def load_config():
    global toggle_key_info
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
            toggle_key_info = data.get("toggle_key", dict(DEFAULT_TOGGLE))
        except Exception:
            toggle_key_info = dict(DEFAULT_TOGGLE)


def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump({"toggle_key": toggle_key_info}, f, indent=2)


# --- Window check ---

def get_foreground_exe():
    try:
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return psutil.Process(pid).name().lower()
    except Exception:
        return ""


def is_game_active():
    return get_foreground_exe() == TARGET_EXE


# --- Toggle hook ---

def register_toggle_hook():
    global toggle_hook_ref, toggle_hook_type

    unregister_toggle_hook()

    if toggle_key_info["type"] == "mouse":
        btn = toggle_key_info["button"]

        def on_mouse_event(event):
            if isinstance(event, mouse.ButtonEvent) and event.event_type == mouse.DOWN:
                if event.button == btn:
                    toggle_script()

        toggle_hook_ref  = on_mouse_event
        toggle_hook_type = "mouse"
        mouse.hook(on_mouse_event)

    else:
        toggle_hook_ref  = keyboard.on_press_key(
            toggle_key_info["button"],
            lambda _: toggle_script(),
            suppress=False
        )
        toggle_hook_type = "keyboard"


def unregister_toggle_hook():
    global toggle_hook_ref, toggle_hook_type
    if toggle_hook_ref is None:
        return
    try:
        if toggle_hook_type == "mouse":
            mouse.unhook(toggle_hook_ref)
        else:
            keyboard.unhook(toggle_hook_ref)
    except Exception:
        pass
    toggle_hook_ref  = None
    toggle_hook_type = None


# --- Key capture ---

def start_capture():
    """Aguarda o próximo input (teclado ou mouse) e define como nova tecla de controle."""
    global capturing
    if capturing:
        return
    capturing = True
    push_event({"type": "capture_start"})

    capture_kb_hook  = None
    capture_ms_hook  = None

    def finish(info: dict):
        global capturing, toggle_key_info
        nonlocal capture_kb_hook, capture_ms_hook

        try:
            keyboard.unhook(capture_kb_hook)
        except Exception:
            pass
        try:
            mouse.unhook(capture_ms_hook)
        except Exception:
            pass

        toggle_key_info = info
        save_config()
        register_toggle_hook()
        capturing = False
        push_event({"type": "capture_done", "label": info["label"]})

    def on_kb(event):
        if event.event_type != keyboard.KEY_DOWN:
            return
        # ignora modificadores sozinhos
        if event.name in ("shift", "ctrl", "alt", "caps lock", "win"):
            return
        finish({"type": "keyboard", "button": event.name, "label": event.name.upper()})

    def on_ms(event):
        if not isinstance(event, mouse.ButtonEvent):
            return
        if event.event_type != mouse.DOWN:
            return
        labels = {"left": "Mouse Esquerdo", "right": "Mouse Direito",
                  "middle": "Scroll (meio)", "x": "Mouse X1", "x2": "Mouse X2"}
        label = labels.get(event.button, event.button)
        finish({"type": "mouse", "button": event.button, "label": label})

    # pequeno delay para não capturar o próprio clique no botão "Alterar"
    def delayed_register():
        nonlocal capture_kb_hook, capture_ms_hook
        time.sleep(0.3)
        capture_kb_hook = keyboard.hook(on_kb, suppress=False)
        capture_ms_hook = mouse.hook(on_ms)

    threading.Thread(target=delayed_register, daemon=True).start()


# --- Loop ---

def move_loop():
    global current, running
    while True:
        wake.wait()
        wake.clear()

        while True:
            with lock:
                if not running:
                    break
                k = key1 if current == 1 else key2
                current = 2 if current == 1 else 1

            keyboard.press(k)
            time.sleep(HOLD)
            keyboard.release(k)
            push_event({"type": "key", "key": k})

            interrupted = wake.wait(timeout=INTERVAL - HOLD)
            if interrupted:
                break


# --- Script control ---

def register_wasd_hooks():
    global wasd_hooks
    wasd_hooks.append(keyboard.on_press_key("w", lambda _: activate("w", "s", "Cima → Baixo"),        suppress=True))
    wasd_hooks.append(keyboard.on_press_key("s", lambda _: activate("s", "w", "Baixo → Cima"),        suppress=True))
    wasd_hooks.append(keyboard.on_press_key("d", lambda _: activate("d", "a", "Direita → Esquerda"),  suppress=True))
    wasd_hooks.append(keyboard.on_press_key("a", lambda _: activate("a", "d", "Esquerda → Direita"),  suppress=True))


def unregister_wasd_hooks():
    global wasd_hooks
    for h in wasd_hooks:
        keyboard.unhook(h)
    wasd_hooks.clear()


def toggle_script():
    global script_enabled, running

    if not is_game_active() or capturing:
        return

    script_enabled = not script_enabled

    if script_enabled:
        register_wasd_hooks()
        push_event({"type": "enabled"})
    else:
        unregister_wasd_hooks()
        with lock:
            running = False
        wake.set()
        push_event({"type": "disabled"})


def stop_loop():
    global running
    with lock:
        if not running:
            return
        running = False
    wake.set()
    push_event({"type": "loop_stopped"})


def on_any_key(event):
    if not script_enabled or not running or capturing:
        return
    if event.event_type != keyboard.KEY_DOWN:
        return
    if event.name not in ("w", "a", "s", "d"):
        stop_loop()


def activate(k1, k2, label):
    global running, key1, key2, current

    if not is_game_active() or not script_enabled:
        return

    with lock:
        running = True
        key1 = k1
        key2 = k2
        current = 1

    push_event({"type": "status", "label": label})
    wake.set()


# --- GUI ---

BG      = "#1e1e2e"
SURFACE = "#2a2a3e"
ACCENT  = "#89b4fa"
GREEN   = "#a6e3a1"
RED     = "#f38ba8"
YELLOW  = "#f9e2af"
TEXT    = "#cdd6f4"
SUBTEXT = "#6c7086"
KEY_OFF = "#313244"
KEY_ON  = "#89b4fa"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Mamaragan")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.attributes("-topmost", True)

        mono = tkfont.Font(family="Consolas", size=11)
        big  = tkfont.Font(family="Consolas", size=13, weight="bold")
        tiny = tkfont.Font(family="Consolas", size=9)

        # --- Banner enable/disable ---
        self.banner = tk.Frame(self, bg=SURFACE, pady=10)
        self.banner.pack(fill="x")

        self.enable_dot = tk.Label(self.banner, text="●", font=big, bg=SURFACE, fg=RED)
        self.enable_dot.pack(side="left", padx=(16, 6))

        self.enable_label = tk.Label(self.banner, font=mono, bg=SURFACE, fg=TEXT)
        self.enable_label.pack(side="left")
        self._update_banner_text()

        # --- Tecla de controle ---
        ctrl_frame = tk.Frame(self, bg=BG, pady=8)
        ctrl_frame.pack(fill="x", padx=16)

        tk.Label(ctrl_frame, text="Tecla de controle:", font=tiny, bg=BG, fg=SUBTEXT).pack(side="left")

        self.ctrl_key_label = tk.Label(
            ctrl_frame, text=toggle_key_info["label"],
            font=tiny, bg=BG, fg=ACCENT
        )
        self.ctrl_key_label.pack(side="left", padx=(6, 10))

        self.capture_btn = tk.Button(
            ctrl_frame, text="Alterar", font=tiny,
            bg=SURFACE, fg=TEXT, activebackground=ACCENT, activeforeground=BG,
            relief="flat", bd=0, padx=8, pady=2,
            command=start_capture
        )
        self.capture_btn.pack(side="left")

        # --- Status loop ---
        status_frame = tk.Frame(self, bg=BG, pady=4)
        status_frame.pack(fill="x", padx=16)

        self.dot = tk.Label(status_frame, text="●", font=mono, bg=BG, fg=SUBTEXT)
        self.dot.pack(side="left", padx=(0, 6))

        self.status_label = tk.Label(status_frame, text="—", font=mono, bg=BG, fg=SUBTEXT)
        self.status_label.pack(side="left")

        # --- Visualizador WASD ---
        keys_frame = tk.Frame(self, bg=BG, pady=10)
        keys_frame.pack()

        self.key_labels = {}
        layout = [
            [None, "w", None],
            ["a",  "s", "d"],
        ]
        for r, row in enumerate(layout):
            for c, key in enumerate(row):
                if key is None:
                    tk.Label(keys_frame, text="", width=4, bg=BG).grid(row=r, column=c, padx=4, pady=4)
                    continue
                lbl = tk.Label(
                    keys_frame, text=key.upper(), width=4, height=2,
                    font=big, bg=KEY_OFF, fg=TEXT, relief="flat", bd=0
                )
                lbl.grid(row=r, column=c, padx=4, pady=4)
                self.key_labels[key] = lbl

        self.mode_label = tk.Label(self, text="—", font=mono, bg=BG, fg=SUBTEXT)
        self.mode_label.pack(pady=(0, 8))

        # --- Log ---
        log_frame = tk.Frame(self, bg=SURFACE, pady=8)
        log_frame.pack(fill="x", padx=16, pady=(0, 16))

        tk.Label(log_frame, text="Log", font=tiny, bg=SURFACE, fg=SUBTEXT).pack(anchor="w", padx=8)

        self.log_text = tk.Text(
            log_frame, height=8, width=36,
            font=tiny, bg=SURFACE, fg=TEXT,
            relief="flat", bd=0, state="disabled"
        )
        self.log_text.pack(padx=8, pady=(0, 4))

        self._active_key = None
        self.after(50, self._poll)

    def _update_banner_text(self):
        label = toggle_key_info["label"]
        if script_enabled:
            self.enable_label.configure(text=f"Ativado  ({label} para desativar)")
        else:
            self.enable_label.configure(text=f"Desativado  ({label} para ativar)")

    def _flash_key(self, key):
        if self._active_key and self._active_key in self.key_labels:
            self.key_labels[self._active_key].configure(bg=KEY_OFF, fg=TEXT)
        if key in self.key_labels:
            self.key_labels[key].configure(bg=KEY_ON, fg=BG)
        self._active_key = key

    def _clear_keys(self):
        if self._active_key and self._active_key in self.key_labels:
            self.key_labels[self._active_key].configure(bg=KEY_OFF, fg=TEXT)
        self._active_key = None

    def _log(self, msg):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _poll(self):
        with gui_lock:
            events = list(gui_queue)
            gui_queue.clear()

        for ev in events:
            if ev["type"] == "capture_start":
                self.capture_btn.configure(text="Pressione...", fg=YELLOW, state="disabled")
                self._log("⌨ Aguardando input...")

            elif ev["type"] == "capture_done":
                self.capture_btn.configure(text="Alterar", fg=TEXT, state="normal")
                self.ctrl_key_label.configure(text=ev["label"])
                self._update_banner_text()
                self._log(f"✔ Tecla definida: {ev['label']}")

            elif ev["type"] == "enabled":
                self.enable_dot.configure(fg=GREEN)
                self._update_banner_text()
                self._log("✔ Script ativado")

            elif ev["type"] == "disabled":
                self.enable_dot.configure(fg=RED)
                self._update_banner_text()
                self.dot.configure(fg=SUBTEXT)
                self.status_label.configure(text="—", fg=SUBTEXT)
                self.mode_label.configure(text="—", fg=SUBTEXT)
                self._clear_keys()
                self._log("✖ Script desativado")

            elif ev["type"] == "loop_stopped":
                self.dot.configure(fg=YELLOW)
                self.status_label.configure(text="Interrompido", fg=YELLOW)
                self.mode_label.configure(text="—", fg=SUBTEXT)
                self._clear_keys()
                self._log("⚠ Interrompido por input externo")

            elif ev["type"] == "status":
                self.dot.configure(fg=GREEN)
                self.status_label.configure(text="Rodando", fg=GREEN)
                self.mode_label.configure(text=ev["label"], fg=ACCENT)
                self._log(f"▶ {ev['label']}")

            elif ev["type"] == "key":
                self._flash_key(ev["key"])
                self._log(f"  → {ev['key'].upper()}")

        self.after(50, self._poll)


# --- Bootstrap ---

def main():
    load_config()

    threading.Thread(target=move_loop, daemon=True).start()

    register_toggle_hook()
    keyboard.hook(on_any_key, suppress=False)

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()

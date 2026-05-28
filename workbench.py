"""
Maquinado - Workbench de Timing
================================
Mede a precisão dos intervalos entre teclas enviadas pelo script (AHK ou Python).
Execute este arquivo ANTES de ativar o script a ser medido.

Uso:
  1. Rode: python workbench.py
  2. Ative o script (AHK ou Maquinado.py)
  3. Deixe rodar por ~60 segundos
  4. Pressione ESC para encerrar e ver o relatório
"""

import keyboard
import time
import ctypes
import threading
import tkinter as tk
from tkinter import font as tkfont
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque

ctypes.windll.winmm.timeBeginPeriod(1)

WASD        = {"w", "a", "s", "d"}
MAX_POINTS  = 300  # pontos no gráfico ao vivo

# --- Estado ---
timestamps   = []       # tempo absoluto de cada key_down
intervals    = []       # intervalo entre pressões consecutivas (ms)
lock         = threading.Lock()
collecting   = False
label_source = "?"


# --- Coleta ---

def on_key(event):
    if not collecting:
        return
    if event.event_type != keyboard.KEY_DOWN:
        return
    if event.name not in WASD:
        return

    now = time.perf_counter()
    with lock:
        if timestamps:
            diff = (now - timestamps[-1]) * 1000  # ms
            intervals.append(diff)
        timestamps.append(now)


keyboard.hook(on_key, suppress=False)


# --- GUI ---

BG      = "#1e1e2e"
SURFACE = "#2a2a3e"
ACCENT  = "#89b4fa"
GREEN   = "#a6e3a1"
RED     = "#f38ba8"
YELLOW  = "#f9e2af"
TEXT    = "#cdd6f4"
SUBTEXT = "#6c7086"


class Workbench(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Maquinado — Workbench de Timing")
        self.configure(bg=BG)
        self.resizable(False, False)

        mono = tkfont.Font(family="Consolas", size=11)
        big  = tkfont.Font(family="Consolas", size=13, weight="bold")
        tiny = tkfont.Font(family="Consolas", size=9)

        # --- Cabeçalho ---
        head = tk.Frame(self, bg=SURFACE, pady=12)
        head.pack(fill="x")

        self.status_dot = tk.Label(head, text="●", font=big, bg=SURFACE, fg=SUBTEXT)
        self.status_dot.pack(side="left", padx=(16, 6))

        self.status_lbl = tk.Label(head, text="Aguardando início...", font=big, bg=SURFACE, fg=TEXT)
        self.status_lbl.pack(side="left")

        # --- Identificação da fonte ---
        src_frame = tk.Frame(self, bg=BG, pady=8)
        src_frame.pack(fill="x", padx=16)

        tk.Label(src_frame, text="Fonte:", font=tiny, bg=BG, fg=SUBTEXT).pack(side="left")

        self.src_var = tk.StringVar(value="AHK")
        for label in ("AHK", "Python"):
            tk.Radiobutton(
                src_frame, text=label, variable=self.src_var, value=label,
                font=tiny, bg=BG, fg=TEXT, selectcolor=SURFACE,
                activebackground=BG, activeforeground=TEXT
            ).pack(side="left", padx=(8, 0))

        # --- Botões ---
        btn_frame = tk.Frame(self, bg=BG, pady=6)
        btn_frame.pack(fill="x", padx=16)

        self.start_btn = tk.Button(
            btn_frame, text="▶  Iniciar coleta", font=mono,
            bg=GREEN, fg=BG, activebackground=ACCENT, activeforeground=BG,
            relief="flat", bd=0, padx=14, pady=6,
            command=self._start
        )
        self.start_btn.pack(side="left", padx=(0, 8))

        self.stop_btn = tk.Button(
            btn_frame, text="⏹  Parar e ver relatório", font=mono,
            bg=SURFACE, fg=TEXT, activebackground=RED, activeforeground=BG,
            relief="flat", bd=0, padx=14, pady=6,
            command=self._stop,
            state="disabled"
        )
        self.stop_btn.pack(side="left")

        # --- Stats ao vivo ---
        stats_frame = tk.Frame(self, bg=SURFACE, pady=10)
        stats_frame.pack(fill="x", padx=16, pady=(8, 0))

        self.stat_labels = {}
        stats = [
            ("amostras", "Amostras"),
            ("media",    "Média"),
            ("desvio",   "Desvio padrão"),
            ("minimo",   "Mínimo"),
            ("maximo",   "Máximo"),
            ("drift",    "Drift acumulado"),
        ]
        for key, label in stats:
            row = tk.Frame(stats_frame, bg=SURFACE)
            row.pack(fill="x", padx=12, pady=2)
            tk.Label(row, text=f"{label}:", font=tiny, bg=SURFACE, fg=SUBTEXT, width=18, anchor="w").pack(side="left")
            val = tk.Label(row, text="—", font=tiny, bg=SURFACE, fg=TEXT, anchor="w")
            val.pack(side="left")
            self.stat_labels[key] = val

        # --- Instrução ---
        tk.Label(
            self, text="ESC também encerra a coleta",
            font=tiny, bg=BG, fg=SUBTEXT
        ).pack(pady=(8, 12))

        keyboard.add_hotkey("esc", self._stop)
        self.after(500, self._refresh_stats)

    def _start(self):
        global collecting, label_source, timestamps, intervals
        with lock:
            timestamps.clear()
            intervals.clear()
        label_source = self.src_var.get()
        collecting   = True

        self.status_dot.configure(fg=GREEN)
        self.status_lbl.configure(text=f"Coletando — {label_source}...")
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

    def _stop(self):
        global collecting
        if not collecting and not intervals:
            return
        collecting = False

        self.status_dot.configure(fg=SUBTEXT)
        self.status_lbl.configure(text="Coleta encerrada — gerando relatório...")
        self.stop_btn.configure(state="disabled")
        self.after(200, self._show_report)

    def _refresh_stats(self):
        with lock:
            data = list(intervals)

        if data:
            import statistics
            media  = sum(data) / len(data)
            desvio = statistics.stdev(data) if len(data) > 1 else 0
            minimo = min(data)
            maximo = max(data)
            drift  = sum(d - media for d in data)

            self.stat_labels["amostras"].configure(text=str(len(data)))
            self.stat_labels["media"].configure(text=f"{media:.2f} ms")
            self.stat_labels["desvio"].configure(text=f"{desvio:.2f} ms", fg=GREEN if desvio < 5 else YELLOW if desvio < 15 else RED)
            self.stat_labels["minimo"].configure(text=f"{minimo:.2f} ms")
            self.stat_labels["maximo"].configure(text=f"{maximo:.2f} ms")
            self.stat_labels["drift"].configure(text=f"{drift:+.1f} ms")

        self.after(500, self._refresh_stats)

    def _show_report(self):
        with lock:
            data = list(intervals)

        if len(data) < 2:
            self.status_lbl.configure(text="Dados insuficientes.")
            self.start_btn.configure(state="normal")
            return

        import statistics
        media    = sum(data) / len(data)
        desvio   = statistics.stdev(data)
        minimo   = min(data)
        maximo   = max(data)
        fonte    = label_source
        n        = len(data)

        # drift acumulado por amostra
        drift_series = []
        acum = 0
        for d in data:
            acum += d - media
            drift_series.append(acum)

        # --- Gráfico ---
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), facecolor="#1e1e2e")
        fig.canvas.manager.set_window_title(f"Workbench — {fonte}")

        for ax in (ax1, ax2):
            ax.set_facecolor("#2a2a3e")
            ax.tick_params(colors="#cdd6f4")
            ax.xaxis.label.set_color("#cdd6f4")
            ax.yaxis.label.set_color("#cdd6f4")
            ax.title.set_color("#cdd6f4")
            for spine in ax.spines.values():
                spine.set_edgecolor("#6c7086")

        # Intervalos ao longo do tempo
        ax1.plot(data, color="#89b4fa", linewidth=0.8, label="Intervalo real (ms)")
        ax1.axhline(media,  color="#a6e3a1", linewidth=1.2, linestyle="--", label=f"Média: {media:.1f}ms")
        ax1.axhline(media + desvio, color="#f9e2af", linewidth=0.8, linestyle=":", label=f"±1σ: {desvio:.1f}ms")
        ax1.axhline(media - desvio, color="#f9e2af", linewidth=0.8, linestyle=":")
        ax1.set_title(f"Intervalos entre teclas — {fonte}  ({n} amostras)")
        ax1.set_xlabel("Amostra")
        ax1.set_ylabel("Intervalo (ms)")
        ax1.legend(facecolor="#2a2a3e", labelcolor="#cdd6f4", edgecolor="#6c7086")

        # Drift acumulado
        ax2.plot(drift_series, color="#f38ba8", linewidth=0.8)
        ax2.axhline(0, color="#6c7086", linewidth=0.8, linestyle="--")
        ax2.set_title("Drift acumulado ao longo do tempo")
        ax2.set_xlabel("Amostra")
        ax2.set_ylabel("Drift (ms)")

        # Rodapé com resumo
        resumo = (
            f"Fonte: {fonte}   |   Amostras: {n}   |   "
            f"Média: {media:.2f}ms   |   σ: {desvio:.2f}ms   |   "
            f"Min: {minimo:.2f}ms   |   Máx: {maximo:.2f}ms"
        )
        fig.text(0.5, 0.01, resumo, ha="center", color="#6c7086", fontsize=8)
        plt.tight_layout(rect=[0, 0.03, 1, 1])
        plt.show()

        self.status_lbl.configure(text="Relatório gerado. Pode iniciar nova coleta.")
        self.start_btn.configure(state="normal")


def main():
    app = Workbench()
    app.mainloop()
    ctypes.windll.winmm.timeEndPeriod(1)


if __name__ == "__main__":
    main()

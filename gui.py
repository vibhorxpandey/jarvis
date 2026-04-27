import math
import queue
import random
import tkinter as tk
from datetime import datetime


class FridayGUI:
    # ── Palette ───────────────────────────────────────────────────────
    BG        = "#050810"
    BG2       = "#080d1a"
    CYAN      = "#00d4ff"
    CYAN_DIM  = "#003a50"
    BLUE      = "#0055cc"
    TEXT      = "#b0d8f0"
    TEXT_DIM  = "#1e4a60"
    GREEN     = "#00ff88"
    ORANGE    = "#ff8c00"

    W, H = 920, 620

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("F.R.I.D.A.Y.")
        self.root.configure(bg=self.BG)
        self.root.overrideredirect(True)          # borderless
        self.root.resizable(False, False)

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{self.W}x{self.H}+{(sw-self.W)//2}+{(sh-self.H)//2}")

        # animation state
        self._angle      = 0.0
        self._pulse      = 0.0
        self._pulse_d    = 1
        self._wave       = [4] * 22
        self._wave_t     = 0
        self._status     = "STANDBY"
        self._audio_level = 0.0   # real mic energy, updated live

        # thread → GUI queue
        self._q = queue.Queue()

        # drag
        self._dx = self._dy = 0

        self._build()
        self._tick()
        self._drain()

    # ── Public API (safe to call from any thread) ─────────────────────

    def set_status(self, s: str):
        self._q.put(("status", s))

    def add_message(self, speaker: str, text: str):
        self._q.put(("msg", speaker, text))

    def set_audio_level(self, level: float):
        """Feed real mic energy (float32 mean-abs) into the waveform."""
        self._q.put(("level", level))

    def run(self):
        self.root.mainloop()

    # ── Layout ────────────────────────────────────────────────────────

    def _build(self):
        # Title bar
        bar = tk.Frame(self.root, bg="#030609", height=38)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        lbl_title = tk.Label(bar, text="◈  F.R.I.D.A.Y.",
                             bg="#030609", fg=self.CYAN,
                             font=("Consolas", 13, "bold"))
        lbl_title.pack(side="left", padx=14, pady=6)
        lbl_title.bind("<Button-1>", self._drag_start)
        lbl_title.bind("<B1-Motion>", self._drag_move)

        self._clock_var = tk.StringVar()
        tk.Label(bar, textvariable=self._clock_var,
                 bg="#030609", fg=self.TEXT_DIM,
                 font=("Consolas", 9)).pack(side="right", padx=70, pady=10)

        for sym, hover_fg, hover_bg, action in [
            ("  ✕  ", "#ff4444", "#1a0505", self.root.destroy),
            ("  —  ", self.CYAN,  "#001a22", self.root.iconify),
        ]:
            b = tk.Label(bar, text=sym, bg="#030609", fg=self.TEXT_DIM,
                         font=("Consolas", 11, "bold"), cursor="hand2")
            b.pack(side="right")
            b.bind("<Enter>", lambda e, lbl=b, f=hover_fg, bg=hover_bg:
                   lbl.config(fg=f, bg=bg))
            b.bind("<Leave>", lambda e, lbl=b:
                   lbl.config(fg=self.TEXT_DIM, bg="#030609"))
            b.bind("<Button-1>", lambda e, a=action: a())

        bar.bind("<Button-1>", self._drag_start)
        bar.bind("<B1-Motion>", self._drag_move)

        tk.Frame(self.root, bg=self.CYAN_DIM, height=1).pack(fill="x")

        # Body
        body = tk.Frame(self.root, bg=self.BG)
        body.pack(fill="both", expand=True)

        # ── Left: HUD ─────────────────────────────────────────────────
        left = tk.Frame(body, bg=self.BG, width=470)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        self._hud = tk.Canvas(left, bg=self.BG, highlightthickness=0,
                              width=470, height=490)
        self._hud.pack(pady=8)

        self._waveform = tk.Canvas(left, bg=self.BG, highlightthickness=0,
                                   width=470, height=62)
        self._waveform.pack()

        # ── Divider ───────────────────────────────────────────────────
        tk.Frame(body, bg=self.CYAN_DIM, width=1).pack(side="left", fill="y", pady=16)

        # ── Right: log ────────────────────────────────────────────────
        right = tk.Frame(body, bg=self.BG)
        right.pack(side="left", fill="both", expand=True)

        tk.Label(right, text="◈  COMMUNICATION LOG",
                 bg=self.BG, fg=self.CYAN_DIM,
                 font=("Consolas", 9, "bold")).pack(anchor="w", padx=16, pady=(14, 4))
        tk.Frame(right, bg=self.CYAN_DIM, height=1).pack(fill="x", padx=16)

        self._log = tk.Text(
            right, bg=self.BG2, fg=self.TEXT, font=("Consolas", 10),
            state="disabled", wrap="word", relief="flat",
            insertbackground=self.CYAN, padx=10, pady=8,
            spacing1=3, spacing3=5
        )
        self._log.pack(fill="both", expand=True, padx=16, pady=(8, 0))
        self._log.tag_config("friday", foreground=self.CYAN,  font=("Consolas", 10, "bold"))
        self._log.tag_config("vibhor", foreground=self.GREEN, font=("Consolas", 10, "bold"))
        self._log.tag_config("ts",     foreground=self.TEXT_DIM, font=("Consolas", 8))
        self._log.tag_config("body",   foreground=self.TEXT)

        # ── Status bar ────────────────────────────────────────────────
        tk.Frame(self.root, bg=self.CYAN_DIM, height=1).pack(fill="x")
        sbar = tk.Frame(self.root, bg="#030609", height=30)
        sbar.pack(fill="x")
        sbar.pack_propagate(False)

        self._dot = tk.Label(sbar, text="●", bg="#030609",
                             fg=self.GREEN, font=("Consolas", 10))
        self._dot.pack(side="left", padx=(14, 4), pady=4)

        tk.Label(sbar, text="ONLINE", bg="#030609",
                 fg=self.TEXT_DIM, font=("Consolas", 9)).pack(side="left")
        tk.Label(sbar, text="│", bg="#030609",
                 fg=self.TEXT_DIM, font=("Consolas", 9)).pack(side="left", padx=10)

        self._mode_lbl = tk.Label(sbar, text='SAY "FRIDAY" TO ACTIVATE',
                                  bg="#030609", fg=self.TEXT_DIM,
                                  font=("Consolas", 9))
        self._mode_lbl.pack(side="left")

        tk.Label(sbar, text="v2.0 │ STARK TECH",
                 bg="#030609", fg=self.TEXT_DIM,
                 font=("Consolas", 9)).pack(side="right", padx=14)

    # ── Animation loop ────────────────────────────────────────────────

    def _tick(self):
        self._angle   = (self._angle + 1.4) % 360
        self._pulse  += 0.045 * self._pulse_d
        if self._pulse >= 1 or self._pulse <= 0:
            self._pulse_d *= -1

        self._wave_t += 1
        if self._wave_t % 3 == 0:
            if self._status == "LISTENING" and self._audio_level > 0:
                # Real mic energy drives bar height
                h = min(int(self._audio_level * 700), 50)
                self._wave = [max(3, h + random.randint(-h//3 - 1, h//3 + 1))
                              for _ in self._wave]
            elif self._status == "LISTENING":
                self._wave = [random.randint(3, 10) for _ in self._wave]
            elif self._status == "SPEAKING":
                self._wave = [random.randint(6, 32) for _ in self._wave]
            elif self._status == "CALIBRATING":
                self._wave = [random.randint(4, 20) for _ in self._wave]
            else:
                self._wave = [random.randint(2, 5)  for _ in self._wave]

        self._draw_hud()
        self._draw_wave()
        self._clock_var.set(datetime.now().strftime("  %a  %d %b %Y    %H:%M:%S  "))
        self.root.after(16, self._tick)

    def _accent(self):
        return {
            "LISTENING":  (self.CYAN,   "#003344"),
            "SPEAKING":   ("#80ffcc",   "#002233"),
            "PROCESSING": (self.ORANGE, "#331800"),
        }.get(self._status, ("#0088aa", "#001a22"))

    def _draw_hud(self):
        c = self._hud
        c.delete("all")
        cx, cy = 235, 245
        ac, ac_dim = self._accent()
        p = self._pulse

        # subtle grid
        for i in range(0, 470, 40):
            c.create_line(i, 0, i, 490, fill="#080e1c", width=1)
        for j in range(0, 490, 40):
            c.create_line(0, j, 470, j, fill="#080e1c", width=1)

        # outer static ring + tick marks
        R = 185
        c.create_oval(cx-R, cy-R, cx+R, cy+R, outline=self.CYAN_DIM, width=1)
        for deg in range(0, 360, 15):
            rad = math.radians(deg)
            tick = 8 if deg % 90 == 0 else 4
            x1 = cx + (R - tick) * math.cos(rad)
            y1 = cy + (R - tick) * math.sin(rad)
            x2 = cx + (R + 3)    * math.cos(rad)
            y2 = cy + (R + 3)    * math.sin(rad)
            c.create_line(x1, y1, x2, y2,
                          fill=(ac if deg % 90 == 0 else ac_dim), width=1)

        # ring 1 — slow, clockwise
        a1 = self._angle
        c.create_arc(cx-162, cy-162, cx+162, cy+162,
                     start=a1, extent=250, style="arc", outline=ac, width=2)
        c.create_arc(cx-162, cy-162, cx+162, cy+162,
                     start=a1+260, extent=70, style="arc", outline=ac, width=2)

        # ring 2 — medium, counter-clockwise
        a2 = -self._angle * 1.7
        c.create_arc(cx-118, cy-118, cx+118, cy+118,
                     start=a2, extent=195, style="arc", outline=self.BLUE, width=2)
        c.create_arc(cx-118, cy-118, cx+118, cy+118,
                     start=a2+205, extent=110, style="arc", outline=self.BLUE, width=2)

        # ring 3 — small, fast
        a3 = self._angle * 2.5
        for start, ext in [(a3, 120), (a3+140, 75), (a3+250, 50)]:
            c.create_arc(cx-80, cy-80, cx+80, cy+80,
                         start=start, extent=ext, style="arc", outline=ac, width=1)

        # glow halo
        glow_r = int(58 + 8 * p)
        for i, alpha in enumerate(["#001828", "#001525", "#001020", "#000c18"]):
            r = glow_r - i * 5
            if r > 0:
                c.create_oval(cx-r, cy-r, cx+r, cy+r, fill=alpha, outline="")

        # inner circle
        c.create_oval(cx-54, cy-54, cx+54, cy+54,
                      fill="#020912", outline=ac, width=2)

        # core pulse dot
        dr = int(7 + 5 * p)
        c.create_oval(cx-dr, cy-dr, cx+dr, cy+dr, fill=ac, outline="")

        # cross-hairs
        for x1, y1, x2, y2 in [
            (cx-185, cy, cx-62, cy), (cx+62, cy, cx+185, cy),
            (cx, cy-185, cx, cy-62), (cx, cy+62, cx, cy+185),
        ]:
            c.create_line(x1, y1, x2, y2, fill=ac_dim, width=1)

        # status + label below core
        c.create_text(cx, cy+72, text=self._status,
                      fill=ac, font=("Consolas", 11, "bold"), anchor="center")
        c.create_text(cx, cy+90, text="F.R.I.D.A.Y.",
                      fill=self.TEXT_DIM, font=("Consolas", 8), anchor="center")

        # corner brackets
        for bx, by, pos in [
            (cx-185, cy-185, "tl"), (cx+185, cy-185, "tr"),
            (cx-185, cy+185, "bl"), (cx+185, cy+185, "br"),
        ]:
            self._bracket(c, bx, by, pos, ac_dim)

    def _bracket(self, c, x, y, pos, col, L=18):
        w = 1
        dirs = {
            "tl": [(x, y+L, x, y), (x, y, x+L, y)],
            "tr": [(x, y+L, x, y), (x, y, x-L, y)],
            "bl": [(x, y-L, x, y), (x, y, x+L, y)],
            "br": [(x, y-L, x, y), (x, y, x-L, y)],
        }
        for x1, y1, x2, y2 in dirs[pos]:
            c.create_line(x1, y1, x2, y2, fill=col, width=w)

    def _draw_wave(self):
        c = self._waveform
        c.delete("all")
        n   = len(self._wave)
        bw  = 8
        gap = 12
        total = n * (bw + gap) - gap
        x0  = (470 - total) // 2
        mid = 31
        ac, _ = self._accent()
        col = ac if self._status in ("LISTENING", "SPEAKING") else self.CYAN_DIM

        for i, h in enumerate(self._wave):
            x = x0 + i * (bw + gap)
            c.create_rectangle(x, mid - h//2, x + bw, mid + h//2,
                                fill=col, outline="")

    # ── Queue drain ───────────────────────────────────────────────────

    def _drain(self):
        try:
            while True:
                item = self._q.get_nowait()
                if item[0] == "status":
                    self._apply_status(item[1])
                elif item[0] == "msg":
                    self._write_log(item[1], item[2])
                elif item[0] == "level":
                    self._audio_level = item[1]
        except queue.Empty:
            pass
        self.root.after(40, self._drain)

    def _apply_status(self, s: str):
        self._status = s
        modes = {
            "STANDBY":     ('SAY "FRIDAY" TO ACTIVATE', self.TEXT_DIM, self.TEXT_DIM),
            "LISTENING":   ("● LISTENING...",            self.CYAN,     self.CYAN),
            "PROCESSING":  ("● PROCESSING...",           self.ORANGE,   self.ORANGE),
            "SPEAKING":    ("● SPEAKING...",             "#80ffcc",     "#80ffcc"),
            "CALIBRATING": ("● CALIBRATING MIC...",      "#cc88ff",     "#cc88ff"),
        }
        text, fg, dot = modes.get(s, (s, self.TEXT_DIM, self.TEXT_DIM))
        self._mode_lbl.config(text=text, fg=fg)
        self._dot.config(fg=dot)

    def _write_log(self, speaker: str, text: str):
        self._log.config(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self._log.insert("end", f"[{ts}]  ", "ts")
        tag = "friday" if speaker.upper() == "FRIDAY" else "vibhor"
        self._log.insert("end", f"{speaker.upper()}: ", tag)
        self._log.insert("end", f"{text}\n", "body")
        self._log.see("end")
        self._log.config(state="disabled")

    # ── Drag ──────────────────────────────────────────────────────────

    def _drag_start(self, e):
        self._dx, self._dy = e.x, e.y

    def _drag_move(self, e):
        x = self.root.winfo_x() + e.x - self._dx
        y = self.root.winfo_y() + e.y - self._dy
        self.root.geometry(f"+{x}+{y}")

#!/usr/bin/env python3
"""Small window around cup0.py / sndg.py / cupicon.py: browse the cups, add GameBanana tracks and cups, set a cup icon.  python tools/gui.py"""
import os, re, subprocess, sys, threading, tkinter as tk
from tkinter import filedialog, messagebox, ttk

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import cup0, cupicon, sndg

CEMU_DEFAULT = os.path.expandvars(r'%APPDATA%\Cemu\mlc01\usr\title\0005000e\1010ed00\content')
TAGS = ['', '3DS', 'Wii', 'N64', 'GBA', 'SNES', 'DS', 'GCN', 'Tour']


class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title('MK8 CTGP-Café – cups & tracks'); self.geometry('1240x720')
        self.content = tk.StringVar(value=CEMU_DEFAULT if os.path.isdir(CEMU_DEFAULT) else '')
        self.base = tk.StringVar(); self.src = tk.StringVar(); self.name = tk.StringVar(); self.tag = tk.StringVar()
        self.mode = tk.StringVar(value='slot'); self.newcup = tk.StringVar(); self.extras = tk.BooleanVar(value=True)
        self.music = tk.BooleanVar(value=True); self.emblem = tk.StringVar(); self.picture = tk.StringVar()
        top = ttk.Frame(self, padding=6); top.pack(fill='x')
        self.row(top, '1. Game content folder: the one that contains data.cup0 (Cemu: mlc01/usr/title/0005000e/1010ed00/content)', self.content, 0, self.pick_dir)
        self.row(top, '2. Original game content folder (optional): lets the tool check the music labels', self.base, 1, self.pick_dir)
        body = ttk.Frame(self, padding=6); body.pack(fill='both', expand=True)
        left = ttk.LabelFrame(body, text='Cups', padding=4); left.pack(side='left', fill='both', expand=True)
        self.tree = ttk.Treeview(left, columns=('dir', 'tag'), height=18); self.tree.pack(fill='both', expand=True, side='left')
        self.tree.heading('#0', text='cup / slot'); self.tree.heading('dir', text='folder'); self.tree.heading('tag', text='tag')
        self.tree.column('#0', width=280); self.tree.column('dir', width=170); self.tree.column('tag', width=50)
        sb = ttk.Scrollbar(left, command=self.tree.yview); sb.pack(side='right', fill='y'); self.tree.config(yscrollcommand=sb.set)
        right = ttk.Frame(body, padding=(8, 0), width=460); right.pack(side='left', fill='y'); right.pack_propagate(True)
        add = ttk.LabelFrame(right, text='Add a track to a cup', padding=6); add.pack(fill='x')
        self.row(add, 'Track download from GameBanana (.zip) or its folder', self.src, 0, self.pick_src)
        self.row(add, 'Name shown in the game (you can type it)', self.name, 1)
        ttk.Label(add, text='Origin tag (small label next to the name, optional)').grid(row=4, column=0, columnspan=3, sticky='w', pady=(4, 0)); ttk.Combobox(add, textvariable=self.tag, values=TAGS, width=8).grid(row=5, column=0, sticky='w')
        self.row(add, 'Preview picture of the track (.bflim, optional - a placeholder is used otherwise)', self.picture, 3, self.pick_file)
        ttk.Radiobutton(add, text='Put it in the slot I selected in the list on the left (CTGP cups only)', variable=self.mode, value='slot').grid(row=8, column=0, columnspan=3, sticky='w', pady=(8, 0))
        ttk.Radiobutton(add, text='Create a new cup named:', variable=self.mode, value='cup').grid(row=9, column=0, sticky='w')
        ttk.Entry(add, textvariable=self.newcup, width=22).grid(row=9, column=1, columnspan=2, sticky='w')
        ttk.Checkbutton(add, text='copy sky boxes / music from the archive', variable=self.extras).grid(row=10, column=0, columnspan=3, sticky='w')
        ttk.Checkbutton(add, text='fix the music (own stream names + labels the game knows)', variable=self.music).grid(row=11, column=0, columnspan=3, sticky='w')
        ttk.Button(add, text='Add the track', command=self.add_track).grid(row=12, column=0, sticky='w', pady=6)
        ico = ttk.LabelFrame(right, text='Cup icon (selected CTGP cup)', padding=6); ico.pack(fill='x', pady=8)
        ttk.Label(ico, text='Select a CTGP cup in the list on the left first.').grid(row=0, column=0, columnspan=3, sticky='w'); self.row(ico, 'Picture for the middle of the icon (PNG with a transparent background)', self.emblem, 1, self.pick_file)
        ttk.Button(ico, text='Make the blue medallion icon and install it', command=self.set_icon).grid(row=6, column=0, sticky='w', pady=4)
        ttk.Button(right, text='Refresh list', command=self.refresh).pack(anchor='w')
        self.log = tk.Text(self, height=9); self.log.pack(fill='x', padx=6, pady=6)
        self.refresh()

    def row(self, parent, label, var, r, browse=None, hint=''):
        ttk.Label(parent, text=label).grid(row=r * 2, column=0, columnspan=3, sticky='w', pady=(4, 0))
        e = ttk.Entry(parent, textvariable=var, width=40, state='readonly' if browse else 'normal'); e.grid(row=r * 2 + 1, column=0, columnspan=2, sticky='we', padx=(0, 4))
        if browse:
            e.bind('<Button-1>', lambda _e: browse(var)); ttk.Button(parent, text='Choose...', command=lambda: browse(var)).grid(row=r * 2 + 1, column=2)

    def pick_dir(self, var):
        d = filedialog.askdirectory();  d and (var.set(d), self.refresh())
    def pick_src(self, var):
        f = filedialog.askopenfilename(filetypes=[('archives', '*.zip'), ('all', '*.*')]) or filedialog.askdirectory()
        if f: var.set(f); self.name.get() or self.name.set(os.path.splitext(os.path.basename(f))[0].replace('_', ' ').title())
    def pick_file(self, var):
        f = filedialog.askopenfilename();  f and var.set(f)

    def say(self, s): self.after(0, lambda: (self.log.insert('end', s + '\n'), self.log.see('end')))

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        p = os.path.join(self.content.get(), 'data.cup0')
        if not os.path.exists(p): return
        self.cups = cup0.parse(open(p, 'rb').read())
        for i, c in enumerate(self.cups):
            n = self.tree.insert('', 'end', iid='c%d' % i, text='%2d  %s%s' % (i, c.name, '' if c.type == 2 else '  (game DLC)'), open=c.type == 2)
            for k, t in enumerate(c.tracks): self.tree.insert(n, 'end', iid='c%d_%d' % (i, k), text='slot %d  %s' % (k, t.name or '(game)'), values=(t.dir, t.tag))

    def selected(self):
        s = self.tree.selection(); m = re.fullmatch(r'c(\d+)(?:_(\d))?', s[0]) if s else None
        return (int(m.group(1)), int(m.group(2)) if m.group(2) else None) if m else (None, None)

    def run(self, fn):
        def go():
            try: fn()
            except SystemExit as e: self.say('error: %s' % e)
            except Exception as e: self.say('error: %r' % e)
            self.after(0, self.refresh)
        threading.Thread(target=go, daemon=True).start()

    def add_track(self):
        c, s = self.selected(); content = self.content.get(); src = self.src.get(); name = self.name.get().strip()
        if not (content and src and name): return messagebox.showwarning('missing', 'content folder, archive and track name are required')
        cmd = [sys.executable, os.path.join(HERE, 'cup0.py'), 'add-track', '--content', content, '--course', src, '--name', name, '--tag', self.tag.get()]
        if self.mode.get() == 'cup':
            if not self.newcup.get().strip(): return messagebox.showwarning('missing', 'give the new cup a name')
            cmd += ['--new-cup', self.newcup.get().strip()]
        else:
            if c is None or s is None or self.cups[c].type != 2: return messagebox.showwarning('select a slot', 'select a slot of a CTGP cup (not a game DLC cup) in the list')
            cmd += ['--cup', str(c), '--slot', str(s)]
        if self.picture.get(): cmd += ['--picture', self.picture.get()]
        if self.extras.get(): cmd += ['--extras', 'mapobj,audio']
        def work():
            before = {t.dir for cu in cup0.parse(open(os.path.join(content, 'data.cup0'), 'rb').read()) for t in cu.tracks}
            r = subprocess.run(cmd, capture_output=True, text=True); self.say((r.stdout + r.stderr).strip())
            if r.returncode: return
            after = [t.dir for cu in cup0.parse(open(os.path.join(content, 'data.cup0'), 'rb').read()) for t in cu.tracks if t.dir not in before]
            if self.music.get() and after:
                base = os.path.join(self.base.get(), 'audio', 'turbo_sound.bfsar') if self.base.get() else None
                if not base: self.say('(no base game folder given: only the stream names are made unique, labels are not checked)')
                sndg.auto_music(content, after[0], base, self.say)
            self.say('done. Restart Cemu to see it.')
        self.run(work)

    def set_icon(self):
        c, _ = self.selected(); content = self.content.get()
        if c is None or self.cups[c].type != 2: return messagebox.showwarning('select a cup', 'select a CTGP cup in the list')
        if not self.emblem.get(): return messagebox.showwarning('missing', 'choose an emblem image')
        def work():
            szs_path = os.path.join(content, 'ui', 'cmn', 'ctgp.szs')
            if not os.path.exists(szs_path + '.bak'): open(szs_path + '.bak', 'wb').write(open(szs_path, 'rb').read())
            name = 'ym_CupIcon' + re.sub(r'[^A-Za-z0-9]', '', self.cups[c].name)[:12]
            data, _ = cupicon.build(self.emblem.get(), szs_path)
            n = cupicon.install_icon(szs_path, szs_path, data, self.cups[c].icon, name); self.say('icon installed in ctgp.szs (%d bytes); restart Cemu' % n)
        self.run(work)


if __name__ == '__main__':
    App().mainloop()

import os
import re
import json
import sys
import subprocess
import time
import queue
import datetime
import threading
import zipfile
import urllib.parse
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException

NAVY = "#323A4E"
NAVY_HOVER = "#414A62"
BLUE = "#1EA5FF"
BLUE_DARK = "#0E8EE6"
BG = "#FFFFFF"
TAB = "#EBEBEB"
BORDER = "#D9D9D9"
TEXT = "#2B2B2B"
GREEN_BG = "#E3F4D7"
GREEN = "#62C93F"
ORANGE = "#FF8C00"

TEXT_OPTS = dict(
    relief="flat", borderwidth=0, highlightthickness=1,
    highlightbackground=BORDER, highlightcolor=BLUE,
    bg="white", fg=TEXT, insertbackground=TEXT,
    selectbackground=BLUE, selectforeground="white",
)
LIST_OPTS = dict(
    relief="flat", borderwidth=0, highlightthickness=1,
    highlightbackground=BORDER, highlightcolor=BLUE,
    bg="white", fg=TEXT, selectbackground=BLUE, selectforeground="white",
)

# سكريبت مشترك يدعم وضعين: 'click' لتسجيل الخطوات، و 'extract' لالتقاط العناصر بدون تنفيذ النقر
REC_JS = r"""
(function () {
  if (window.__recInstalled) return;
  window.__recInstalled = true;
  window.__recMode = window.__recMode || 'click';

  function uniq(sel) {
    try { return document.querySelectorAll(sel).length === 1; } catch (e) { return false; }
  }

  function buildSelector(el) {
    var tag = el.tagName.toLowerCase();
    if (el.id && uniq('#' + CSS.escape(el.id))) return '#' + CSS.escape(el.id);

    var attrs = ['data-testid', 'data-test', 'data-id', 'name', 'aria-label', 'title'];
    for (var i = 0; i < attrs.length; i++) {
      var v = el.getAttribute(attrs[i]);
      if (v && v.length < 80) {
        var s = tag + '[' + attrs[i] + '="' + v.replace(/"/g, '\\"') + '"]';
        if (uniq(s)) return s;
      }
    }

    var classes = Array.from(el.classList).filter(function (c) {
      return c.length < 40 && !/\d{3,}/.test(c);
    });
    for (var j = 0; j < classes.length; j++) {
      var s1 = tag + '.' + CSS.escape(classes[j]);
      if (uniq(s1)) return s1;
    }
    if (classes.length > 1) {
      var s2 = tag + '.' + classes.map(function (c) { return CSS.escape(c); }).join('.');
      if (uniq(s2)) return s2;
    }

    var parts = [];
    var cur = el;
    while (cur && cur.nodeType === 1 && cur !== document.documentElement) {
      var part = cur.tagName.toLowerCase();
      if (cur.id && uniq('#' + CSS.escape(cur.id))) {
        parts.unshift('#' + CSS.escape(cur.id));
        break;
      }
      var parent = cur.parentElement;
      if (parent) {
        var sibs = Array.from(parent.children).filter(function (c) {
          return c.tagName === cur.tagName;
        });
        if (sibs.length > 1) part += ':nth-of-type(' + (sibs.indexOf(cur) + 1) + ')';
      }
      parts.unshift(part);
      cur = parent;
    }
    return parts.join(' > ');
  }

  // تمييز العنصر بصرياً عند تمرير الماوس في وضع الاستخراج
  var lastHovered = null;
  document.addEventListener('mouseover', function (e) {
    if (window.__recMode !== 'extract') return;
    if (lastHovered) lastHovered.style.outline = '';
    lastHovered = e.target;
    lastHovered.style.outline = '2px solid #FF8C00';
  }, true);

  document.addEventListener('click', function (e) {
    try {
      var mode = window.__recMode;
      var t = (mode === 'click')
        ? (e.target.closest('a,button,input,select,label,summary,[role=button],[role=tab],[onclick]') || e.target)
        : e.target;

      if (mode === 'extract') {
        e.preventDefault();
        e.stopPropagation();
        t.style.outline = '2px solid #62C93F';
      }

      var sampleText = (t.innerText || t.value || t.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ').slice(0, 40);
      var data = {
        mode: mode,
        selector: buildSelector(t),
        sample: sampleText
      };
      console.log('__REC__' + encodeURIComponent(JSON.stringify(data)));
    } catch (err) {}
  }, true);
})();
"""

def parse_selector(sel):
    sel = sel.strip()
    low = sel.lower()
    if low.startswith("xpath="):
        return By.XPATH, sel[6:].strip()
    if low.startswith("text="):
        lit = "'" + sel[5:].strip() + "'"
        return By.XPATH, f"//*[text()[contains(normalize-space(.), {lit})]]"
    return By.CSS_SELECTOR, sel

def apply_stealth_options(options):
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--lang=en-US")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

def apply_stealth_driver(driver):
    try:
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"})
    except Exception:
        pass

def open_file(path):
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass

def make_service(path):
    return Service(executable_path=path) if path else Service()

def is_displayed(el):
    try:
        return el.is_displayed()
    except Exception:
        return False

def click_element(driver, el):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    except Exception:
        pass
    try:
        el.click()
    except Exception:
        driver.execute_script("arguments[0].click();", el)

def num(var, default):
    try:
        return var.get()
    except tk.TclError:
        return default

ALL_SITES = "*"
ALL_SITES_LABEL = "All sites (default)"
APP_VERSION = "2.2.0-visual-scraper"

def settings_file():
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "WebScraperTool", "settings_v2.json")

def host_of(url):
    try:
        h = urllib.parse.urlparse(url if "//" in url else "//" + url).hostname or ""
    except ValueError:
        h = ""
    return h.lower()[4:] if h.lower().startswith("www.") else h.lower()

def host_matches(host, key):
    key = (key or "").lower()
    if key.startswith("www."):
        key = key[4:]
    return bool(key) and (host == key or host.endswith("." + key))

def items_for_url(sets_dict, url):
    host = host_of(url)
    best = None
    for key in sets_dict:
        if key != ALL_SITES and host_matches(host, key):
            if best is None or len(key) > len(best):
                best = key
    if best is not None and sets_dict[best]:
        return sets_dict[best]
    return sets_dict.get(ALL_SITES, [])

def tsv(row):
    return "\t".join(re.sub(r"[\t\r\n]+", " ", str(x)) for x in row) + "\n"

def xml_escape(text):
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(text))
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def col_letter(n):
    s, n = "", n + 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s

def write_xlsx(path, rows):
    head = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    ns_main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    ns_rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    ns_pkg = "http://schemas.openxmlformats.org/package/2006/relationships"

    col_count = max((len(r) for r in rows), default=1)
    sheet = [head, f'<worksheet xmlns="{ns_main}">',
             '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" '
             'activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>',
             "<cols>" + "".join(f'<col min="{i}" max="{i}" width="28" customWidth="1"/>' for i in range(1, col_count + 1)) + "</cols>",
             "<sheetData>"]
    for r, row in enumerate(rows, 1):
        style = ' s="1"' if r == 1 else ""
        cells = "".join(f'<c r="{col_letter(c)}{r}" t="inlineStr"{style}><is><t xml:space="preserve">{xml_escape(v)}</t></is></c>' for c, v in enumerate(row))
        sheet.append(f'<row r="{r}">{cells}</row>')
    last_col = col_letter(col_count - 1)
    sheet.append(f'</sheetData><autoFilter ref="A1:{last_col}{max(len(rows), 1)}"/></worksheet>')

    parts = {
        "[Content_Types].xml": head + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>',
        "_rels/.rels": head + f'<Relationships xmlns="{ns_pkg}"><Relationship Id="rId1" Type="{ns_rel}/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": head + f'<workbook xmlns="{ns_main}" xmlns:r="{ns_rel}"><sheets><sheet name="Extracted Data" sheetId="1" r:id="rId1"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": head + f'<Relationships xmlns="{ns_pkg}"><Relationship Id="rId1" Type="{ns_rel}/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="{ns_rel}/styles" Target="styles.xml"/></Relationships>',
        "xl/styles.xml": head + f'<styleSheet xmlns="{ns_main}"><fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts><fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>',
        "xl/worksheets/sheet1.xml": "".join(sheet),
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in parts.items():
            z.writestr(name, content)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Visual Web Scraper Pro  v{APP_VERSION}")
        self.geometry("1120x800")
        self.minsize(960, 680)

        self.msg_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.rec_stop = threading.Event()
        self.worker = None
        self.rec_mode = None  # None | 'click' | 'extract'
        self.rec_driver = None
        self.live_drivers = set()
        self.opt_visible = False

        self.step_sets = {ALL_SITES: []}
        self.extract_sets = {ALL_SITES: []}
        self.current_set = ALL_SITES
        self.saved_links = ""

        self.var_folder = tk.StringVar()
        self.var_driver = tk.StringVar()
        self.var_load_wait = tk.IntVar(value=5)
        self.var_stop_loading = tk.BooleanVar(value=True)
        self.var_dedupe = tk.BooleanVar(value=True)
        self.var_browser_mode = tk.StringVar(value="single")
        self.var_stealth = tk.BooleanVar(value=False)
        self.var_url_delay = tk.DoubleVar(value=0)
        self.var_step_timeout = tk.DoubleVar(value=10)
        self.var_step_delay = tk.DoubleVar(value=1)
        self.var_after_steps = tk.DoubleVar(value=2)
        self.var_continue = tk.BooleanVar(value=True)
        self.var_retries = tk.IntVar(value=2)
        self.var_workers = tk.IntVar(value=1)
        self.var_resume = tk.BooleanVar(value=True)

        self.persist = {
            "folder": self.var_folder, "driver": self.var_driver,
            "load_wait": self.var_load_wait, "stop_loading": self.var_stop_loading,
            "dedupe": self.var_dedupe, "browser_mode": self.var_browser_mode,
            "stealth": self.var_stealth, "url_delay": self.var_url_delay,
            "step_timeout": self.var_step_timeout, "step_delay": self.var_step_delay,
            "after_steps": self.var_after_steps, "continue": self.var_continue,
            "retries": self.var_retries, "workers": self.var_workers,
            "resume": self.var_resume,
        }
        self.load_settings()
        self.build_ui()
        if self.saved_links:
            self.txt_links.insert("1.0", self.saved_links)
            self.update_link_count()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(100, self.poll_queue)

    @property
    def steps(self):
        return self.step_sets.setdefault(self.current_set, [])

    @steps.setter
    def steps(self, value):
        self.step_sets[self.current_set] = value

    @property
    def extracts(self):
        return self.extract_sets.setdefault(self.current_set, [])

    @extracts.setter
    def extracts(self, value):
        self.extract_sets[self.current_set] = value

    def load_settings(self):
        try:
            with open(settings_file(), encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        if not isinstance(data, dict):
            return
        for key, var in self.persist.items():
            if key in data:
                try:
                    var.set(data[key])
                except Exception:
                    pass
        if isinstance(data.get("step_sets"), dict):
            self.step_sets = data["step_sets"]
            self.step_sets.setdefault(ALL_SITES, [])
        if isinstance(data.get("extract_sets"), dict):
            self.extract_sets = data["extract_sets"]
            self.extract_sets.setdefault(ALL_SITES, [])
        if data.get("current_set") in (set(self.step_sets) | set(self.extract_sets)):
            self.current_set = data["current_set"]
        if isinstance(data.get("links"), str):
            self.saved_links = data["links"]

    def save_settings(self):
        data = {key: var.get() for key, var in self.persist.items() if hasattr(var, "get")}
        data["step_sets"] = self.step_sets
        data["extract_sets"] = self.extract_sets
        data["current_set"] = self.current_set
        data["links"] = self.txt_links.get("1.0", "end").strip()
        try:
            path = settings_file()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

    def build_ui(self):
        self.apply_theme()
        pad = {"padx": 8, "pady": 4}

        # ----- Toolbar -----
        self.toolbar = ttk.Frame(self, style="Toolbar.TFrame")
        self.toolbar.pack(side="top", fill="x")
        tb = ttk.Frame(self.toolbar, style="Toolbar.TFrame")
        tb.pack(fill="x", padx=12, pady=10)
        self.btn_start = ttk.Button(tb, text="\u25B6 Start Scraping", style="Accent.TButton", command=self.start)
        self.btn_start.pack(side="left")
        self.btn_stop = ttk.Button(tb, text="\u25A0 Stop", style="Toolbar.TButton", command=self.stop, state="disabled")
        self.btn_stop.pack(side="left", padx=(8, 0))
        self.btn_test = ttk.Button(tb, text="Test on first link", style="Toolbar.TButton", command=self.test_first)
        self.btn_test.pack(side="left", padx=(8, 0))

        self.btn_options = ttk.Button(tb, text="", style="Toolbar.TButton", command=self.toggle_options)
        self.btn_options.pack(side="right")
        self.btn_export = ttk.Button(tb, text="Export Excel", style="Toolbar.TButton", command=self.export_excel)
        self.btn_export.pack(side="right", padx=(0, 8))
        self.btn_folder = ttk.Button(tb, text="Open folder", style="Toolbar.TButton", command=self.open_folder)
        self.btn_folder.pack(side="right", padx=(0, 8))

        # ----- Status Bar -----
        status_line = ttk.Frame(self, style="StatusLine.TFrame", height=4)
        status_line.pack(side="bottom", fill="x")
        status = ttk.Frame(self, style="Status.TFrame")
        status.pack(side="bottom", fill="x")
        self.lbl_summary = ttk.Label(status, text="", style="Status.TLabel")
        self.lbl_summary.pack(side="left", padx=12, pady=8)
        self.lbl_progress = ttk.Label(status, text="0 / 0", style="Status.TLabel")
        self.lbl_progress.pack(side="right", padx=12)
        self.progress = ttk.Progressbar(status, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, padx=(0, 6))

        # ----- Options Box -----
        box = ttk.LabelFrame(self, text="Scraper Options")
        self.opt_box = box
        box.columnconfigure(1, weight=1)

        ttk.Label(box, text="Save folder:").grid(row=0, column=0, sticky="w", **pad)
        ttk.Entry(box, textvariable=self.var_folder).grid(row=0, column=1, sticky="ew", **pad)
        ttk.Button(box, text="Browse...", command=self.pick_folder).grid(row=0, column=2, **pad)

        ttk.Label(box, text="chromedriver (optional):").grid(row=1, column=0, sticky="w", **pad)
        ttk.Entry(box, textvariable=self.var_driver).grid(row=1, column=1, sticky="ew", **pad)
        ttk.Button(box, text="Browse...", command=self.pick_driver).grid(row=1, column=2, **pad)

        opts = ttk.Frame(box)
        opts.grid(row=2, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(opts, text="Page load wait (s):").pack(side="left")
        ttk.Spinbox(opts, from_=1, to=120, width=6, textvariable=self.var_load_wait).pack(side="left", padx=(4, 16))
        ttk.Label(opts, text="Delay between URLs (s):").pack(side="left")
        ttk.Spinbox(opts, from_=0, to=300, increment=0.5, width=6, textvariable=self.var_url_delay).pack(side="left", padx=(4, 16))
        ttk.Label(opts, text="Retries:").pack(side="left")
        ttk.Spinbox(opts, from_=0, to=10, width=5, textvariable=self.var_retries).pack(side="left", padx=(4, 16))
        ttk.Label(opts, text="Parallel workers (1-4):").pack(side="left")
        ttk.Spinbox(opts, from_=1, to=4, width=5, textvariable=self.var_workers).pack(side="left", padx=(4, 0))

        checks = ttk.Frame(box)
        checks.grid(row=3, column=0, columnspan=3, sticky="w", **pad)
        ttk.Checkbutton(checks, text="One browser for all URLs", variable=self.var_browser_mode, onvalue="single", offvalue="each").pack(side="left", padx=(0, 16))
        ttk.Checkbutton(checks, text="Stop loading early", variable=self.var_stop_loading).pack(side="left", padx=(0, 16))
        ttk.Checkbutton(checks, text="Remove duplicates", variable=self.var_dedupe, command=self.update_link_count).pack(side="left", padx=(0, 16))
        ttk.Checkbutton(checks, text="Stealth mode", variable=self.var_stealth).pack(side="left", padx=(0, 16))
        ttk.Checkbutton(checks, text="Skip already scraped (Resume)", variable=self.var_resume).pack(side="left")

        # ----- Site Selector Bar -----
        site_bar = ttk.Frame(self)
        site_bar.pack(fill="x", padx=10, pady=(6, 0))
        ttk.Label(site_bar, text="Configuration profile for:").pack(side="left")
        self.cmb_set = ttk.Combobox(site_bar, state="readonly", width=26)
        self.cmb_set.pack(side="left", padx=(6, 6))
        self.cmb_set.bind("<<ComboboxSelected>>", self.on_set_selected)
        ttk.Button(site_bar, text="New site...", command=self.add_site).pack(side="left")
        ttk.Button(site_bar, text="Delete site", command=self.delete_site).pack(side="left", padx=4)

        # ----- Main Panes: Links | Pre-Click Steps | Extract Fields -----
        pane_opts = dict(sashwidth=8, sashrelief="flat", bg="#E9ECF1", bd=0, opaqueresize=True)
        main_pane = tk.PanedWindow(self, orient="vertical", **pane_opts)
        main_pane.pack(fill="both", expand=True, padx=10, pady=4)
        mid = tk.PanedWindow(main_pane, orient="horizontal", **pane_opts)
        main_pane.add(mid, stretch="always", minsize=220)

        # 1. Links Column
        links = ttk.LabelFrame(mid, text="1. Target URLs")
        mid.add(links, stretch="always", minsize=250)
        self.txt_links = scrolledtext.ScrolledText(links, height=10, width=32, wrap="none", **TEXT_OPTS)
        self.txt_links.pack(fill="both", expand=True, padx=6, pady=6)
        bar = ttk.Frame(links)
        bar.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Button(bar, text="Load .txt", command=self.load_links_file).pack(side="left")
        ttk.Button(bar, text="Clear", command=lambda: self.txt_links.delete("1.0", "end")).pack(side="left", padx=4)
        self.lbl_count = ttk.Label(bar, text="0 links")
        self.lbl_count.pack(side="right")
        self.txt_links.bind("<<Modified>>", self.on_links_modified)

        # 2. Pre-Extraction Clicks Column
        steps = ttk.LabelFrame(mid, text="2. Pre-Actions (Click before scraping)")
        mid.add(steps, stretch="always", minsize=340)
        self.lst_steps = tk.Listbox(steps, height=8, activestyle="none", exportselection=False, **LIST_OPTS)
        self.lst_steps.pack(fill="both", expand=True, padx=6, pady=(6, 4))

        r1 = ttk.Frame(steps)
        r1.pack(fill="x", padx=6, pady=2)
        self.btn_rec_click = ttk.Button(r1, text="\u25CF Record Clicks", command=lambda: self.toggle_record("click"))
        self.btn_rec_click.pack(side="left")
        ttk.Button(r1, text="+ Click", command=self.add_click).pack(side="left", padx=4)
        ttk.Button(r1, text="+ Wait", command=self.add_wait).pack(side="left")

        r2 = ttk.Frame(steps)
        r2.pack(fill="x", padx=6, pady=(2, 6))
        ttk.Button(r2, text="Delete", command=self.delete_step).pack(side="left")
        ttk.Button(r2, text="Up", width=4, command=lambda: self.move_step(-1)).pack(side="left", padx=4)
        ttk.Button(r2, text="Down", width=5, command=lambda: self.move_step(1)).pack(side="left")
        ttk.Button(r2, text="Clear", command=self.clear_steps).pack(side="right")

        # 3. Fields to Extract Column
        ext_box = ttk.LabelFrame(mid, text="3. Data to Extract (Columns in Excel)")
        mid.add(ext_box, stretch="always", minsize=360)
        self.lst_extracts = tk.Listbox(ext_box, height=8, activestyle="none", exportselection=False, **LIST_OPTS)
        self.lst_extracts.pack(fill="both", expand=True, padx=6, pady=(6, 4))

        er1 = ttk.Frame(ext_box)
        er1.pack(fill="x", padx=6, pady=2)
        self.btn_rec_extract = ttk.Button(er1, text="\u25CF Pick Elements Visually", style="Accent.TButton", command=lambda: self.toggle_record("extract"))
        self.btn_rec_extract.pack(side="left")
        ttk.Button(er1, text="+ Manual Field", command=self.add_extract_manual).pack(side="left", padx=4)

        er2 = ttk.Frame(ext_box)
        er2.pack(fill="x", padx=6, pady=(2, 6))
        ttk.Button(er2, text="Rename Col", command=self.rename_extract).pack(side="left")
        ttk.Button(er2, text="Delete", command=self.delete_extract).pack(side="left", padx=4)
        ttk.Button(er2, text="Clear", command=self.clear_extracts).pack(side="right")

        # ----- Log -----
        logf = ttk.LabelFrame(main_pane, text="Scraping Log")
        main_pane.add(logf, stretch="always", minsize=90)
        self.txt_log = scrolledtext.ScrolledText(logf, height=7, state="disabled", **TEXT_OPTS)
        self.txt_log.pack(fill="both", expand=True, padx=6, pady=6)

        self.refresh_sets()
        self.refresh_steps()
        self.refresh_extracts()
        self.update_summary()
        self.set_options(False)

    def apply_theme(self):
        self.configure(bg=BG)
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure(".", background=BG, foreground=TEXT, fieldbackground=BG, bordercolor=BORDER)
        s.configure("TFrame", background=BG)
        s.configure("TLabel", background=BG, foreground=TEXT)
        s.configure("TLabelframe", background=BG, bordercolor=BORDER, relief="solid", borderwidth=1)
        s.configure("TLabelframe.Label", background=BG, foreground="#4A4A4A", font=("Segoe UI", 10, "bold"))

        def flat_button(name, bg, fg, hover, pressed, dis_bg, dis_fg, padding, bold=False):
            s.configure(name, background=bg, foreground=fg, bordercolor=bg, padding=padding, relief="flat", borderwidth=1)
            if bold:
                s.configure(name, font=("Segoe UI", 10, "bold"))

        flat_button("TButton", TAB, "#333333", "#DDDDDD", "#D0D0D0", "#F4F4F4", "#A8A8A8", (8, 4))
        flat_button("Accent.TButton", BLUE, "white", BLUE_DARK, "#0A7DCC", "#A8D9FB", "white", (12, 5), bold=True)
        flat_button("Toolbar.TButton", NAVY, "#E6EAF2", NAVY_HOVER, "#2A3142", NAVY, "#7A859B", (12, 8))

        s.configure("Horizontal.TProgressbar", troughcolor="#D5DBE4", background=BLUE, thickness=10)
        s.configure("Toolbar.TFrame", background=NAVY)
        s.configure("Status.TFrame", background=GREEN_BG)
        s.configure("StatusLine.TFrame", background=GREEN)
        s.configure("Status.TLabel", background=GREEN_BG, foreground="#34502A")

    def toggle_options(self):
        self.set_options(not self.opt_visible)

    def set_options(self, show):
        self.opt_visible = show
        if show:
            self.opt_box.pack(fill="x", padx=10, pady=(8, 0), after=self.toolbar)
        else:
            self.opt_box.pack_forget()
        self.btn_options.config(text=f"\u2630 Options {'\u25BE' if show else '\u25B8'}")

    def update_summary(self):
        self.lbl_summary.config(text=f"Pre-steps: {len(self.steps)}   \u00B7   Extract Columns: {len(self.extracts)}   \u00B7   Workers: {num(self.var_workers, 1)}")

    def update_link_count(self):
        self.lbl_count.config(text=f"{len(self.get_links())} links")

    def on_links_modified(self, _event=None):
        if self.txt_links.edit_modified():
            self.update_link_count()
            self.txt_links.edit_modified(False)

    def get_links(self, dedupe=True):
        raw = self.txt_links.get("1.0", "end").splitlines()
        links = [x.strip() for x in raw if x.strip()]
        return list(dict.fromkeys(links)) if (dedupe and self.var_dedupe.get()) else links

    def pick_folder(self):
        d = filedialog.askdirectory(title="Choose save folder")
        if d:
            self.var_folder.set(d)

    def pick_driver(self):
        f = filedialog.askopenfilename(title="Choose chromedriver", filetypes=[("chromedriver", "*.exe"), ("All files", "*.*")])
        if f:
            self.var_driver.set(f)

    def load_links_file(self):
        f = filedialog.askopenfilename(title="Choose links file", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if f:
            with open(f, encoding="utf-8", errors="ignore") as fh:
                self.txt_links.delete("1.0", "end")
                self.txt_links.insert("1.0", fh.read())

    def open_folder(self):
        folder = self.var_folder.get().strip()
        if folder and os.path.isdir(folder):
            open_file(folder)
        else:
            messagebox.showinfo("Open folder", "Choose an existing save folder first.")

    def export_excel(self):
        folder = self.var_folder.get().strip()
        tsv_path = os.path.join(folder, "Scraped_Data.txt") if folder else ""
        if not tsv_path or not os.path.exists(tsv_path):
            messagebox.showinfo("Export Excel", "No scraped data found yet.")
            return
        rows = []
        with open(tsv_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rows.append(line.rstrip("\n").split("\t"))
        path = os.path.join(folder, "Extracted_Data.xlsx")
        try:
            write_xlsx(path, rows)
            open_file(path)
        except Exception as e:
            messagebox.showerror("Export Excel", f"Error:\n{e}")

    # ----- Profiles -----
    def refresh_sets(self):
        keys = [ALL_SITES] + sorted((set(self.step_sets) | set(self.extract_sets)) - {ALL_SITES})
        self.cmb_set.config(values=[ALL_SITES_LABEL if k == ALL_SITES else k for k in keys])
        self.cmb_set.set(ALL_SITES_LABEL if self.current_set == ALL_SITES else self.current_set)

    def on_set_selected(self, _event=None):
        label = self.cmb_set.get()
        self.current_set = ALL_SITES if label == ALL_SITES_LABEL else label
        self.refresh_steps()
        self.refresh_extracts()
        self.update_summary()

    def add_site(self):
        links = self.get_links()
        first = host_of(links[0]) if links else ""
        text = simpledialog.askstring("New site", "Domain name:", initialvalue=first, parent=self)
        host = host_of(text.strip()) if text else ""
        if host:
            self.step_sets.setdefault(host, [])
            self.extract_sets.setdefault(host, [])
            self.current_set = host
            self.refresh_sets()
            self.refresh_steps()
            self.refresh_extracts()

    def delete_site(self):
        if self.current_set != ALL_SITES and messagebox.askyesno("Delete site", f"Delete profile for {self.current_set}?"):
            self.step_sets.pop(self.current_set, None)
            self.extract_sets.pop(self.current_set, None)
            self.current_set = ALL_SITES
            self.refresh_sets()
            self.refresh_steps()
            self.refresh_extracts()

    # ----- Pre-Action Steps List -----
    def refresh_steps(self, select=None):
        self.lst_steps.delete(0, "end")
        for n, st in enumerate(self.steps, 1):
            txt = f"{n}. Wait {st['seconds']:g} s" if st["type"] == "wait" else f"{n}. Click: {st['selector']}"
            self.lst_steps.insert("end", txt)
        if select is not None and 0 <= select < len(self.steps):
            self.lst_steps.selection_set(select)
        self.update_summary()

    def delete_step(self):
        sel = self.lst_steps.curselection()
        if sel:
            del self.steps[sel[0]]
            self.refresh_steps()

    def move_step(self, delta):
        sel = self.lst_steps.curselection()
        if not sel:
            return
        i = sel[0]
        j = i + delta
        if 0 <= j < len(self.steps):
            self.steps[i], self.steps[j] = self.steps[j], self.steps[i]
            self.refresh_steps(select=j)

    def clear_steps(self):
        if self.steps and messagebox.askyesno("Clear", "Remove all pre-steps?"):
            self.steps = []
            self.refresh_steps()

    def add_wait(self):
        sec = simpledialog.askfloat("Wait", "Seconds:", minvalue=0.1, maxvalue=60, parent=self)
        if sec:
            self.steps.append({"type": "wait", "seconds": sec})
            self.refresh_steps(select=len(self.steps) - 1)

    def add_click(self):
        sel = simpledialog.askstring("Add Click", "CSS Selector to click:", parent=self)
        if sel and sel.strip():
            self.steps.append({"type": "click", "selector": sel.strip()})
            self.refresh_steps(select=len(self.steps) - 1)

    # ----- Extraction Fields List -----
    def refresh_extracts(self, select=None):
        self.lst_extracts.delete(0, "end")
        for n, ex in enumerate(self.extracts, 1):
            sample = f"  (e.g. '{ex['sample']}')" if ex.get("sample") else ""
            self.lst_extracts.insert("end", f"{n}. [{ex['name']}] -> {ex['selector']}{sample}")
        if select is not None and 0 <= select < len(self.extracts):
            self.lst_extracts.selection_set(select)
        self.update_summary()

    def add_extract_manual(self):
        name = simpledialog.askstring("Column Name", "Enter Excel Column Name (e.g. Price, Part Number):", parent=self)
        if not name or not name.strip():
            return
        sel = simpledialog.askstring("Selector", f"Enter CSS Selector for '{name.strip()}':", parent=self)
        if sel and sel.strip():
            self.extracts.append({"name": name.strip(), "selector": sel.strip(), "sample": ""})
            self.refresh_extracts(select=len(self.extracts) - 1)

    def rename_extract(self):
        sel = self.lst_extracts.curselection()
        if not sel:
            return
        idx = sel[0]
        cur_name = self.extracts[idx]["name"]
        new_name = simpledialog.askstring("Rename Column", "New column name:", initialvalue=cur_name, parent=self)
        if new_name and new_name.strip():
            self.extracts[idx]["name"] = new_name.strip()
            self.refresh_extracts(select=idx)

    def delete_extract(self):
        sel = self.lst_extracts.curselection()
        if sel:
            del self.extracts[sel[0]]
            self.refresh_extracts()

    def clear_extracts(self):
        if self.extracts and messagebox.askyesno("Clear", "Remove all extraction fields?"):
            self.extracts = []
            self.refresh_extracts()

    # ----- Dual Visual Recording (Click Mode vs Extract Mode) -----
    def toggle_record(self, mode):
        if self.rec_mode is not None:
            self.rec_stop.set()
            return
        links = self.get_links()
        url = links[0] if links else simpledialog.askstring("Sample URL", "Enter URL to open:", parent=self)
        if not url:
            return

        self.rec_mode = mode
        self.rec_stop.clear()
        self.btn_start.config(state="disabled")
        if mode == "click":
            self.btn_rec_click.config(text="\u25A0 Stop Recording")
            self.btn_rec_extract.config(state="disabled")
            self.log("MODE: Recording PRE-ACTIONS. Click buttons/tabs you want automated before scraping.")
        else:
            self.btn_rec_extract.config(text="\u25A0 Stop Picking")
            self.btn_rec_click.config(state="disabled")
            self.log("MODE: PICKING DATA FIELDS. Hover & click elements to extract (links won't open).")

        threading.Thread(target=self.record_worker, args=(url, mode, self.var_driver.get().strip(), self.var_stealth.get()), daemon=True).start()

    def drain_logs(self, driver):
        for entry in driver.get_log("browser"):
            m = re.search(r"__REC__([^\"'\s]+)", entry.get("message", ""))
            if m:
                try:
                    data = json.loads(urllib.parse.unquote(m.group(1)))
                    self.msg_queue.put(("rec_event", data))
                except Exception:
                    pass

    def record_worker(self, url, mode, driver_path, stealth):
        driver = None
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
            if stealth:
                apply_stealth_options(options)
            driver = webdriver.Chrome(service=make_service(driver_path), options=options)
            self.rec_driver = driver
            if stealth:
                apply_stealth_driver(driver)

            init_script = f"window.__recMode = '{mode}';\n" + REC_JS
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": init_script})
            driver.get(url)

            while not self.rec_stop.is_set():
                try:
                    self.drain_logs(driver)
                except Exception:
                    break
                time.sleep(0.3)
        except Exception as e:
            self.msg_queue.put(("log", f"Browser error: {e}"))
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
            self.rec_driver = None
            self.msg_queue.put(("rec_done", None))

    def log(self, text):
        self.txt_log.config(state="normal")
        self.txt_log.insert("end", text + "\n")
        self.txt_log.see("end")
        self.txt_log.config(state="disabled")

    def poll_queue(self):
        try:
            while True:
                kind, data = self.msg_queue.get_nowait()
                if kind == "log":
                    self.log(data)
                elif kind == "progress":
                    done, total = data
                    self.progress["maximum"] = max(total, 1)
                    self.progress["value"] = done
                    self.lbl_progress.config(text=f"{done} / {total}")
                elif kind == "done":
                    self.btn_start.config(state="normal")
                    self.btn_stop.config(state="disabled")
                    self.btn_rec_click.config(state="normal")
                    self.btn_rec_extract.config(state="normal")
                elif kind == "rec_event":
                    if data.get("mode") == "click":
                        self.steps.append({"type": "click", "selector": data["selector"]})
                        self.refresh_steps(select=len(self.steps) - 1)
                        self.log(f"[Pre-Click Recorded]: {data['selector']}")
                    elif data.get("mode") == "extract":
                        col_name = f"Field_{len(self.extracts) + 1}"
                        self.extracts.append({
                            "name": col_name,
                            "selector": data["selector"],
                            "sample": data.get("sample", "")
                        })
                        self.refresh_extracts(select=len(self.extracts) - 1)
                        self.log(f"[Extract Field Picked]: {col_name} -> {data['selector']} (Sample: {data.get('sample', '')})")
                elif kind == "rec_done":
                    self.rec_mode = None
                    self.btn_rec_click.config(text="\u25CF Record Clicks", state="normal")
                    self.btn_rec_extract.config(text="\u25CF Pick Elements Visually", state="normal")
                    self.btn_start.config(state="normal")
                    self.log("Visual session closed.")
        except queue.Empty:
            pass
        self.after(100, self.poll_queue)

    def on_close(self):
        self.save_settings()
        self.rec_stop.set()
        self.stop_event.set()
        for d in list(self.live_drivers) + [self.rec_driver]:
            if d:
                try:
                    d.quit()
                except Exception:
                    pass
        self.destroy()

    # ----- Scraping Execution -----
    def build_cfg(self):
        folder = self.var_folder.get().strip()
        links = self.get_links()
        if not folder or not links:
            messagebox.showwarning("Warning", "Please specify save folder and target URLs.")
            return None
        os.makedirs(folder, exist_ok=True)
        return links, {
            "folder": os.path.abspath(folder),
            "driver": self.var_driver.get().strip(),
            "load_wait": num(self.var_load_wait, 5),
            "stop_loading": self.var_stop_loading.get(),
            "step_timeout": num(self.var_step_timeout, 10),
            "step_delay": num(self.var_step_delay, 1),
            "after_steps": num(self.var_after_steps, 2),
            "continue_missing": self.var_continue.get(),
            "step_sets": json.loads(json.dumps(self.step_sets)),
            "extract_sets": json.loads(json.dumps(self.extract_sets)),
            "new_browser": self.var_browser_mode.get() == "each",
            "stealth": self.var_stealth.get(),
            "url_delay": num(self.var_url_delay, 0),
            "retries": max(0, num(self.var_retries, 2)),
            "workers": max(1, min(4, num(self.var_workers, 1))),
            "resume": self.var_resume.get(),
        }

    def start(self):
        if self.rec_mode:
            return
        built = self.build_cfg()
        if not built:
            return
        links, cfg = built
        self.save_settings()
        self.stop_event.clear()
        self.btn_start.config(state="disabled")
        self.btn_rec_click.config(state="disabled")
        self.btn_rec_extract.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.msg_queue.put(("progress", (0, len(links))))
        self.worker = threading.Thread(target=self.run_job, args=(links, cfg), daemon=True)
        self.worker.start()

    def test_first(self):
        if self.rec_mode or (self.worker and self.worker.is_alive()):
            return
        built = self.build_cfg()
        if not built:
            return
        links, cfg = built
        self.save_settings()
        self.stop_event.clear()
        threading.Thread(target=self.run_test, args=(links[0], cfg), daemon=True).start()

    def run_test(self, link, cfg):
        q = self.msg_queue
        q.put(("log", f"TEST scraping: {link}"))
        driver = None
        try:
            driver = self.new_driver(cfg)
            fields = items_for_url(cfg["extract_sets"], link)
            vals, status, note = self.scrape_url(driver, link, cfg, fields)
            q.put(("log", f"   Status: {status} {note}"))
            for f, v in zip(fields, vals):
                q.put(("log", f"   [{f['name']}]: {v}"))
        except Exception as e:
            q.put(("log", f"   Error: {e}"))
        finally:
            self.close_driver(driver)

    def stop(self):
        self.stop_event.set()
        self.msg_queue.put(("log", "Stopping..."))

    def new_driver(self, cfg):
        options = webdriver.ChromeOptions()
        options.page_load_strategy = "none"
        options.add_argument("--start-maximized")
        if cfg.get("stealth"):
            apply_stealth_options(options)
        driver = webdriver.Chrome(service=make_service(cfg["driver"]), options=options)
        if cfg.get("stealth"):
            apply_stealth_driver(driver)
        self.live_drivers.add(driver)
        return driver

    def close_driver(self, driver):
        if driver:
            self.live_drivers.discard(driver)
            try:
                driver.quit()
            except Exception:
                pass

    def run_steps(self, driver, steps, cfg):
        for st in steps:
            if st["type"] == "wait":
                time.sleep(st["seconds"])
                continue
            by, val = parse_selector(st["selector"])
            try:
                els = WebDriverWait(driver, cfg["step_timeout"]).until(lambda d: d.find_elements(by, val) or False)
            except TimeoutException:
                els = []
            if not els:
                if cfg["continue_missing"]:
                    continue
                raise RuntimeError(f"Pre-action element not found ({st['selector']})")
            visible = [e for e in els if is_displayed(e)] or els
            for el in visible[:1]:
                try:
                    click_element(driver, el)
                except Exception:
                    pass
            time.sleep(cfg["step_delay"])

    def scrape_url(self, driver, link, cfg, fields):
        driver.get(link)
        time.sleep(cfg["load_wait"])
        if cfg["stop_loading"]:
            driver.execute_script("window.stop();")

        steps = items_for_url(cfg["step_sets"], link)
        if steps:
            self.run_steps(driver, steps, cfg)
            time.sleep(cfg["after_steps"])

        extracted_values = []
        for field in fields:
            by, val = parse_selector(field["selector"])
            try:
                els = driver.find_elements(by, val)
                texts = [e.text.strip() for e in els if e.text.strip()]
                extracted_values.append(" | ".join(texts) if texts else "")
            except Exception:
                extracted_values.append("")
        return extracted_values, "OK", ""

    def worker_loop(self, task_q, cfg, ctx, all_fields):
        holder = {"d": None}
        try:
            while not self.stop_event.is_set():
                try:
                    i, link = task_q.get_nowait()
                except queue.Empty:
                    break
                self.msg_queue.put(("log", f"Scraping [{i + 1}/{ctx['total']}]: {link}"))
                
                vals, status, note = [""] * len(all_fields), "Error", ""
                for attempt in range(1, cfg["retries"] + 2):
                    if self.stop_event.is_set():
                        break
                    try:
                        if holder["d"] is None:
                            holder["d"] = self.new_driver(cfg)
                        vals, status, note = self.scrape_url(holder["d"], link, cfg, all_fields)
                        break
                    except Exception as e:
                        note = str(e).splitlines()[0] if str(e) else type(e).__name__
                        if holder["d"]:
                            self.close_driver(holder["d"])
                            holder["d"] = None
                    if attempt <= cfg["retries"] and not self.stop_event.is_set():
                        time.sleep(2)

                row = [link, status, note, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")] + vals
                with ctx["lock"]:
                    ctx["out"].write(tsv(row))
                    ctx["out"].flush()
                    ctx["done"] += 1
                    self.msg_queue.put(("progress", (ctx["done"], ctx["total"])))
        finally:
            self.close_driver(holder["d"])

    def run_job(self, links, cfg):
        q = self.msg_queue
        total = len(links)
        out_path = os.path.join(cfg["folder"], "Scraped_Data.txt")
        
        active_fields = items_for_url(cfg["extract_sets"], links[0])
        header = ["URL", "Status", "Notes", "Timestamp"] + [f["name"] for f in active_fields]

        done_links = set()
        if cfg["resume"] and os.path.exists(out_path):
            with open(out_path, encoding="utf-8") as f:
                for line in f:
                    parts = line.split("\t")
                    if len(parts) > 1 and parts[1] == "OK":
                        done_links.add(parts[0])

        todo = [(i, l) for i, l in enumerate(links) if l not in done_links]
        if not os.path.exists(out_path) or not cfg["resume"]:
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(tsv(header))

        ctx = {"lock": threading.Lock(), "done": total - len(todo), "total": total}
        q.put(("progress", (ctx["done"], total)))

        task_q = queue.Queue()
        for t in todo:
            task_q.put(t)

        n_workers = max(1, min(cfg["workers"], len(todo))) if todo else 0
        with open(out_path, "a", encoding="utf-8") as out:
            ctx["out"] = out
            threads = [threading.Thread(target=self.worker_loop, args=(task_q, cfg, ctx, active_fields), daemon=True) for _ in range(n_workers)]
            for t in threads: t.start()
            for t in threads: t.join()

        q.put(("log", f"Scraping finished! Saved to: {out_path}"))
        q.put(("done", None))

if __name__ == "__main__":
    App().mainloop()

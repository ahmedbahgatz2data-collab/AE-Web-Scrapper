import os
import re
import json
import sys
import shutil
import socket
import subprocess
import time
import queue
import datetime
import threading
import zipfile
import tempfile
import urllib.parse
import urllib.request
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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

GITHUB_REPO = "ahmedbahgatz2data-collab/AE-Web-Scrapper"
GITHUB_API_LATEST = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

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

REC_JS = r"""
(function () {
  if (window.__recInstalled) return;
  window.__recInstalled = true;

  function uniq(sel) {
    try { return document.querySelectorAll(sel).length === 1; } catch (e) { return false; }
  }

  function count(sel) {
    try { return document.querySelectorAll(sel).length; } catch (e) { return 0; }
  }

  function buildExactSelector(el) {
    var tag = el.tagName.toLowerCase();
    if (el.id && uniq('#' + CSS.escape(el.id))) return '#' + CSS.escape(el.id);

    var attrs = ['data-testid', 'data-test', 'data-id', 'name', 'aria-label', 'placeholder', 'title'];
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

  function buildMultiSelector(el) {
    var td = el.closest('td, th');
    if (td) {
      var tr = td.parentElement;
      var table = td.closest('table');
      if (tr && table) {
        var colIdx = Array.from(tr.children).indexOf(td) + 1;
        var tablePrefix = table.id ? ('#' + CSS.escape(table.id)) : buildExactSelector(table);
        var section = tr.parentElement && (tr.parentElement.tagName === 'TBODY' || tr.parentElement.tagName === 'THEAD')
          ? (' > ' + tr.parentElement.tagName.toLowerCase()) : '';
        var colSel = tablePrefix + section + ' > tr > ' + td.tagName.toLowerCase() + ':nth-of-type(' + colIdx + ')';
        if (count(colSel) > 1) return colSel;
      }
    }

    var parts = [];
    var cur = el;
    var generalized = false;
    while (cur && cur.nodeType === 1 && cur !== document.documentElement) {
      var part = cur.tagName.toLowerCase();
      if (cur.id && uniq('#' + CSS.escape(cur.id))) {
        parts.unshift('#' + CSS.escape(cur.id));
        break;
      }
      var classes = Array.from(cur.classList).filter(function (c) {
        return c.length < 35 && !/\d{2,}/.test(c) && !/active|selected|hover|focus/i.test(c);
      });
      if (classes.length > 0) {
        part += '.' + classes.slice(0, 2).map(function (c) { return CSS.escape(c); }).join('.');
      }
      var parent = cur.parentElement;
      if (parent) {
        var sibs = Array.from(parent.children).filter(function (c) {
          return c.tagName === cur.tagName;
        });
        if (sibs.length > 1) {
          if (!generalized && (cur.tagName === 'LI' || sibs.length >= 3)) {
            generalized = true;
          } else {
            part += ':nth-of-type(' + (sibs.indexOf(cur) + 1) + ')';
          }
        }
      }
      parts.unshift(part);
      cur = parent;
    }
    var sel = parts.join(' > ');
    return count(sel) > 1 ? sel : buildExactSelector(el);
  }

  var lastHovered = null;
  document.addEventListener('mouseover', function (e) {
    if (window.__recMode !== 'extract' && window.__recMode !== 'searchbox') return;
    if (lastHovered) {
      lastHovered.style.outline = '';
      lastHovered = null;
    }
    if (e.altKey) return;
    lastHovered = e.target;
    lastHovered.style.outline = (window.__recMode === 'searchbox') ? '2px solid #1EA5FF' : '2px solid #FF8C00';
  }, true);

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Alt' && lastHovered) {
      lastHovered.style.outline = '';
      lastHovered = null;
    }
  }, true);

  document.addEventListener('click', function (e) {
    try {
      if (e.altKey) {
        if (lastHovered) {
          lastHovered.style.outline = '';
          lastHovered = null;
        }
        return;
      }

      var mode = window.__recMode || 'click';
      var t = e.target;
      if (mode === 'click') {
        t = e.target.closest('select,a,button,input,label,summary,[role=button],[role=tab],[onclick]') || e.target;
      } else if (mode === 'searchbox') {
        t = e.target.closest('input,textarea,[contenteditable="true"]') || e.target;
      }

      if (mode === 'extract' || mode === 'searchbox') {
        e.preventDefault();
        e.stopPropagation();
        t.style.outline = '2px solid #62C93F';
      }

      var anchor = t.closest('a') || t.querySelector('a');
      var sampleHref = anchor ? (anchor.href || '') : '';
      var exactSel = buildExactSelector(t);
      var multiSel = buildMultiSelector(t);
      var multiCount = count(multiSel);
      var sampleText = (t.innerText || t.value || t.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ').slice(0, 45);
      var isSelect = (t.tagName && t.tagName.toLowerCase() === 'select');

      var data = {
        type: mode,
        selector: exactSel,
        multi_selector: multiSel,
        multi_count: multiCount,
        sample: sampleText,
        sample_href: sampleHref,
        is_select: isSelect
      };
      console.log('__REC__' + encodeURIComponent(JSON.stringify(data)));
    } catch (err) {}
  }, true);
})();
"""

SET_SELECT_VALUE_JS = r"""
var el = arguments[0];
var targetVal = String(arguments[1]).trim();
var targetLow = targetVal.toLowerCase();

if (el.tagName && el.tagName.toLowerCase() === 'select') {
  var found = false;
  var matchedVal = targetVal;
  for (var i = 0; i < el.options.length; i++) {
    var optVal = (el.options[i].value || '').trim();
    var optTxt = (el.options[i].text || '').trim();
    if (optVal.toLowerCase() === targetLow || optTxt.toLowerCase() === targetLow) {
      el.selectedIndex = i;
      matchedVal = optVal || optTxt;
      found = true;
      break;
    }
  }
  if (!found) {
    var opt = document.createElement('option');
    opt.value = targetVal;
    opt.text = targetVal;
    el.add(opt);
    el.value = targetVal;
  }
  el.dispatchEvent(new Event('change', { bubbles: true }));
  el.dispatchEvent(new Event('input', { bubbles: true }));

  try {
    if (window.jQuery && window.jQuery.fn && window.jQuery.fn.dataTable) {
      var tbl = window.jQuery(el).closest('.dataTables_wrapper').find('table.dataTable');
      if (tbl.length) {
        var numLen = parseInt(matchedVal, 10);
        if (!isNaN(numLen)) {
          tbl.DataTable().page.len(numLen).draw();
        } else if (targetLow.indexOf('all') !== -1) {
          tbl.DataTable().page.len(-1).draw();
        }
      }
    }
  } catch (e) {}
} else {
  el.click();
  setTimeout(function () {
    var items = document.querySelectorAll('li, option, [role="option"], a, button, span, div');
    for (var j = 0; j < items.length; j++) {
      var t = (items[j].innerText || '').trim().toLowerCase();
      if (t === targetLow) {
        items[j].click();
        break;
      }
    }
  }, 300);
}
"""


def parse_ver_tuple(ver_str):
    nums = re.findall(r"\d+", str(ver_str or ""))
    return tuple(int(x) for x in nums) if nums else (0,)


def schedule_silent_exe_replace(staged_exe_path, restart_after=False):
    if not getattr(sys, "frozen", False):
        return False
    current_exe = os.path.abspath(sys.executable)
    if not os.path.exists(staged_exe_path):
        return False

    pid = os.getpid()
    bat_path = os.path.join(tempfile.gettempdir(), f"ae_scraper_upd_{pid}.bat")
    log_path = os.path.join(tempfile.gettempdir(), f"ae_scraper_upd_{pid}.log")
    restart_cmd = f'start "" "{current_exe}"\r\n' if restart_after else ""

    bat_content = (
        "@echo off\r\n"
        f'echo Starting update at %date% %time% > "{log_path}"\r\n'
        ":waitloop\r\n"
        f'tasklist /FI "PID eq {pid}" 2>NUL | find /I "{pid}" >NUL\r\n'
        "if not errorlevel 1 (\r\n"
        "  timeout /t 1 /nobreak >NUL\r\n"
        "  goto waitloop\r\n"
        ")\r\n"
        "timeout /t 3 /nobreak >NUL\r\n"
        "set /a tries=0\r\n"
        ":moveloop\r\n"
        "set /a tries+=1\r\n"
        f'move /y "{staged_exe_path}" "{current_exe}" >> "{log_path}" 2>&1\r\n'
        "if errorlevel 1 (\r\n"
        "  if %tries% LSS 15 (\r\n"
        "    timeout /t 1 /nobreak >NUL\r\n"
        "    goto moveloop\r\n"
        "  )\r\n"
        ")\r\n"
        f"{restart_cmd}"
        '(goto) 2>nul & del "%~f0"\r\n'
    )
    try:
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        subprocess.Popen(
            ["cmd.exe", "/c", bat_path],
            creationflags=creation_flags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        return True
    except Exception:
        return False


def find_system_chrome(custom_path=""):
    if custom_path and os.path.exists(custom_path):
        return custom_path

    candidates = [
        os.path.join(os.environ.get("PROGRAMFILES", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
    ]
    for p in candidates:
        if p and os.path.exists(p):
            return p

    if sys.platform.startswith("win"):
        try:
            import winreg
            for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(root, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe") as k:
                        val, _ = winreg.QueryValueEx(k, None)
                        if val and os.path.exists(val):
                            return val
                except OSError:
                    pass
        except Exception:
            pass
    return None


def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) == 0


def sync_profile_to_isolated_dir(src_profile_path, port):
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    isolated_root = os.path.join(base, "WebScraperTool", f"IsolatedProfile_{port}")

    src = os.path.normpath(src_profile_path.strip())
    prof_name = os.path.basename(src)
    if prof_name != "Default" and not prof_name.startswith("Profile "):
        prof_name = "Default"
        src = os.path.join(src, "Default") if os.path.isdir(os.path.join(src, "Default")) else src

    dest_prof = os.path.join(isolated_root, prof_name)
    os.makedirs(dest_prof, exist_ok=True)

    parent_src = os.path.dirname(src)
    local_state_src = os.path.join(parent_src, "Local State")
    if os.path.exists(local_state_src):
        try:
            shutil.copy2(local_state_src, os.path.join(isolated_root, "Local State"))
        except Exception:
            pass

    essential_items = [
        "Network", "Cookies", "Login Data", "Web Data",
        "Preferences", "Secure Preferences", "Local Storage",
        "Session Storage", "IndexedDB", "Extension State"
    ]
    for item in essential_items:
        s_item = os.path.join(src, item)
        d_item = os.path.join(dest_prof, item)
        if not os.path.exists(s_item):
            continue
        try:
            if os.path.isdir(s_item):
                shutil.copytree(s_item, d_item, dirs_exist_ok=True)
            else:
                shutil.copy2(s_item, d_item)
        except Exception:
            pass

    return isolated_root, prof_name


def launch_real_chrome(port=9222, headless=False, chrome_path="", custom_profile="", incognito=False):
    if is_port_open(port):
        return True, f"Connected to running Chrome on port {port}"

    chrome_exe = find_system_chrome(chrome_path)
    if not chrome_exe:
        return False, "Could not find chrome.exe automatically. Please select chrome.exe in Global Options."

    if incognito:
        base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
        user_data_dir = os.path.join(base, "WebScraperTool", f"IncognitoProfile_{port}")
        os.makedirs(user_data_dir, exist_ok=True)
        profile_sub = None
    elif custom_profile and custom_profile.strip() and os.path.exists(custom_profile.strip()):
        user_data_dir, profile_sub = sync_profile_to_isolated_dir(custom_profile, port)
    else:
        base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
        user_data_dir = os.path.join(base, "WebScraperTool", f"RealChromeProfile_{port}")
        os.makedirs(user_data_dir, exist_ok=True)
        profile_sub = None

    cmd = [
        chrome_exe,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-background-networking",
        "--start-maximized",
    ]
    if incognito:
        cmd.append("--incognito")
    if profile_sub:
        cmd.append(f"--profile-directory={profile_sub}")
    if headless:
        cmd.append("--headless=new")
        cmd.append("--window-size=1920,1080")

    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        return False, f"Failed to start Chrome ({chrome_exe}): {e}"

    for _ in range(45):
        if is_port_open(port):
            mode_tag = " [Incognito]" if incognito else (f" [Cloned Profile: {profile_sub}]" if profile_sub else "")
            return True, f"Launched Real Chrome{mode_tag} on port {port}"
        time.sleep(0.2)
    return False, f"Chrome launched but port {port} did not open. Try clicking 'Kill Chrome' first."


def parse_selector(sel):
    sel = sel.strip()
    low = sel.lower()
    if low.startswith("xpath="):
        return By.XPATH, sel[6:].strip()
    if low.startswith("text="):
        lit = "'" + sel[5:].strip() + "'"
        return By.XPATH, f"//*[text()[contains(normalize-space(.), {lit})]]"
    return By.CSS_SELECTOR, sel


def extract_element_pair(el):
    txt = ""
    href = ""
    try:
        txt = (el.text or el.get_attribute("innerText") or el.get_attribute("value") or "").strip()
        txt = re.sub(r"\s+", " ", txt)
    except Exception:
        pass

    try:
        href = el.get_attribute("href") or el.get_attribute("src") or ""
        if not href:
            sub_links = el.find_elements(By.TAG_NAME, "a")
            if sub_links:
                href = sub_links[0].get_attribute("href") or ""
        if not href:
            anc = el.find_elements(By.XPATH, "./ancestor::a[1]")
            if anc:
                href = anc[0].get_attribute("href") or ""
    except Exception:
        pass

    return txt, href.strip()


def apply_stealth_options(options):
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--lang=en-US")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])


def apply_stealth_driver(driver):
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"},
        )
    except Exception:
        pass
    try:
        ua = driver.execute_script("return navigator.userAgent")
        driver.execute_cdp_cmd(
            "Network.setUserAgentOverride",
            {"userAgent": ua.replace("HeadlessChrome", "Chrome"), "acceptLanguage": "en-US,en;q=0.9"},
        )
    except Exception:
        pass


def apply_zoom(driver, zoom_pct):
    try:
        z = int(zoom_pct)
        if z and z != 100:
            driver.execute_script(f"document.body.style.zoom = '{z}%';")
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
DEFAULT_MODULE = "Default"
APP_VERSION = "4.1.0"
SITE_OPT_KEYS = (
    "load_wait", "step_timeout", "step_delay", "url_delay",
    "stop_loading", "stealth", "headless", "incognito", "new_browser",
    "use_real_chrome", "zoom_pct"
)


def settings_file():
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "WebScraperTool", "settings_v6.json")


def host_of(url):
    try:
        h = urllib.parse.urlparse(url if "//" in url else "//" + url).hostname or ""
    except ValueError:
        h = ""
    h = h.lower()
    return h[4:] if h.startswith("www.") else h


def host_matches(host, key):
    key = (key or "").lower()
    if key.startswith("www."):
        key = key[4:]
    return bool(key) and (host == key or host.endswith("." + key))


def normalize_site_entry(entry):
    if isinstance(entry, list):
        return {
            "active_module": DEFAULT_MODULE,
            "modules": {
                DEFAULT_MODULE: {"pattern": "", "steps": entry}
            },
        }
    if isinstance(entry, dict) and isinstance(entry.get("modules"), dict):
        mods = entry["modules"]
        if not mods:
            mods[DEFAULT_MODULE] = {"pattern": "", "steps": []}
        for mname, mval in list(mods.items()):
            if isinstance(mval, list):
                mods[mname] = {"pattern": "", "steps": mval}
            elif isinstance(mval, dict):
                mval.setdefault("pattern", "")
                mval.setdefault("steps", [])
            else:
                mods[mname] = {"pattern": "", "steps": []}
        act = entry.get("active_module")
        if act not in mods:
            act = next(iter(mods))
        return {"active_module": act, "modules": mods}
    return {
        "active_module": DEFAULT_MODULE,
        "modules": {DEFAULT_MODULE: {"pattern": "", "steps": []}},
    }


def url_matches_pattern(url, pattern):
    pat = (pattern or "").strip()
    if not pat:
        return False
    low_u = url.lower()
    for part in pat.split("|"):
        p = part.strip()
        if not p:
            continue
        if p.lower().startswith("re:"):
            try:
                if re.search(p[3:].strip(), url, re.IGNORECASE):
                    return True
            except re.error:
                pass
        elif p.lower() in low_u:
            return True
    return False


def resolve_site_and_module(sets_dict, url):
    host = host_of(url)
    best = None
    for key in sets_dict:
        if key != ALL_SITES and host_matches(host, key):
            if best is None or len(key) > len(best):
                best = key

    chosen_site = ALL_SITES
    if best is not None:
        entry = normalize_site_entry(sets_dict[best])
        has_any_steps = any(m.get("steps") for m in entry["modules"].values())
        if has_any_steps:
            chosen_site = best

    entry = normalize_site_entry(sets_dict.get(chosen_site))
    mods = entry["modules"]

    for mname, mdata in mods.items():
        if mdata.get("steps") and url_matches_pattern(url, mdata.get("pattern", "")):
            return chosen_site, mname, mdata.get("steps", [])

    act = entry.get("active_module", DEFAULT_MODULE)
    if act not in mods:
        act = next(iter(mods))
    steps = mods[act].get("steps", [])
    if not steps:
        for mname, mdata in mods.items():
            if mdata.get("steps"):
                return chosen_site, mname, mdata.get("steps", [])
    return chosen_site, act, steps


def apply_site_cfg(base_cfg, url):
    host = host_of(url)
    site_settings = base_cfg.get("site_settings") or {}
    best = None
    for key in site_settings:
        if host_matches(host, key) and (best is None or len(key) > len(best)):
            best = key
    if not best:
        return base_cfg
    merged = dict(base_cfg)
    merged.update({k: v for k, v in site_settings[best].items() if k in SITE_OPT_KEYS})
    return merged


def xml_escape(text):
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(text))
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def col_letter(n):
    s, n = "", n + 1
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def safe_sheet_name(name, used):
    clean = re.sub(r'[\\/*?:\[\]]+', "_", str(name)).strip()[:28] or "Sheet"
    cand = clean
    idx = 2
    while cand.lower() in used:
        cand = f"{clean[:24]}_{idx}"
        idx += 1
    used.add(cand.lower())
    return cand


def write_multi_sheet_xlsx(path, sheets_dict):
    head = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    ns_main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    ns_rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    ns_pkg = "http://schemas.openxmlformats.org/package/2006/relationships"

    used_names = set()
    sheet_entries = []
    for raw_name, rows in sheets_dict.items():
        if not rows:
            continue
        sname = safe_sheet_name(raw_name, used_names)
        sheet_entries.append((sname, rows))

    if not sheet_entries:
        sheet_entries = [("Data", [["No data"]])]

    parts = {
        "[Content_Types].xml": head
        + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        + "".join(
            f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for i in range(1, len(sheet_entries) + 1)
        )
        + "</Types>",
        "_rels/.rels": head + f'<Relationships xmlns="{ns_pkg}">'
        f'<Relationship Id="rId1" Type="{ns_rel}/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": head + f'<workbook xmlns="{ns_main}" xmlns:r="{ns_rel}"><sheets>'
        + "".join(
            f'<sheet name="{xml_escape(sname)}" sheetId="{i}" r:id="rId{i}"/>'
            for i, (sname, _) in enumerate(sheet_entries, 1)
        )
        + "</sheets></workbook>",
        "xl/_rels/workbook.xml.rels": head + f'<Relationships xmlns="{ns_pkg}">'
        + "".join(
            f'<Relationship Id="rId{i}" Type="{ns_rel}/worksheet" Target="worksheets/sheet{i}.xml"/>'
            for i, (sname, _) in enumerate(sheet_entries, 1)
        )
        + f'<Relationship Id="rId{len(sheet_entries) + 1}" Type="{ns_rel}/styles" Target="styles.xml"/></Relationships>',
        "xl/styles.xml": head + f'<styleSheet xmlns="{ns_main}">'
        '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font>'
        '<font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="2"><fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill></fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        "</styleSheet>",
    }

    for i, (_sname, rows) in enumerate(sheet_entries, 1):
        col_count = max((len(r) for r in rows), default=1)
        sheet_xml = [
            head, f'<worksheet xmlns="{ns_main}">',
            '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" '
            'activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>',
            "<cols>" + "".join(f'<col min="{c}" max="{c}" width="26" customWidth="1"/>' for c in range(1, col_count + 1)) + "</cols>",
            "<sheetData>",
        ]
        for r, row in enumerate(rows, 1):
            style = ' s="1"' if r == 1 else ""
            cells = "".join(
                f'<c r="{col_letter(c)}{r}" t="inlineStr"{style}>'
                f'<is><t xml:space="preserve">{xml_escape(v)}</t></is></c>'
                for c, v in enumerate(row)
            )
            sheet_xml.append(f'<row r="{r}">{cells}</row>')
        last_col = col_letter(col_count - 1)
        sheet_xml.append(f'</sheetData><autoFilter ref="A1:{last_col}{max(len(rows), 1)}"/></worksheet>')
        parts[f"xl/worksheets/sheet{i}.xml"] = "".join(sheet_xml)

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in parts.items():
            z.writestr(name, content)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Multi-Site Sequential Web Scraper Pro  v{APP_VERSION}")
        self.geometry("1240x880")
        self.minsize(1040, 720)

        self.msg_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.rec_stop = threading.Event()
        self.worker = None
        self.rec_mode = None
        self.rec_driver = None
        self.live_drivers = set()
        self.opt_visible = True
        self.drag_index = None

        self.update_checking = False
        self.staged_update_path = None
        self.staged_update_version = None
        self.restart_for_update = True

        self.sequence_sets = {ALL_SITES: normalize_site_entry([])}
        self.site_settings = {}
        self.current_set = ALL_SITES
        self.saved_links = ""
        self.saved_keywords = ""

        self.var_folder = tk.StringVar()
        self.var_driver = tk.StringVar()
        self.var_chrome_exe = tk.StringVar()
        self.var_chrome_profile = tk.StringVar()
        self.var_use_real_chrome = tk.BooleanVar(value=True)
        self.var_debug_port = tk.IntVar(value=9222)
        self.var_close_on_finish = tk.BooleanVar(value=True)
        self.var_zoom_pct = tk.IntVar(value=100)
        self.var_mod_pattern = tk.StringVar()

        self.var_input_mode = tk.StringVar(value="urls")
        self.var_search_url = tk.StringVar()
        self.var_search_input_sel = tk.StringVar()
        self.var_search_btn_sel = tk.StringVar()

        self.var_load_wait = tk.IntVar(value=5)
        self.var_stop_loading = tk.BooleanVar(value=True)
        self.var_dedupe = tk.BooleanVar(value=True)
        self.var_browser_mode = tk.StringVar(value="single")
        self.var_headless = tk.BooleanVar(value=False)
        self.var_incognito = tk.BooleanVar(value=False)
        self.var_stealth = tk.BooleanVar(value=False)
        self.var_url_delay = tk.DoubleVar(value=0)
        self.var_step_timeout = tk.DoubleVar(value=10)
        self.var_step_delay = tk.DoubleVar(value=1.5)
        self.var_continue = tk.BooleanVar(value=True)
        self.var_retries = tk.IntVar(value=2)
        self.var_workers = tk.IntVar(value=1)
        self.var_resume = tk.BooleanVar(value=True)

        self.persist = {
            "folder": self.var_folder, "driver": self.var_driver,
            "chrome_exe": self.var_chrome_exe, "chrome_profile": self.var_chrome_profile,
            "use_real_chrome": self.var_use_real_chrome, "debug_port": self.var_debug_port,
            "close_on_finish": self.var_close_on_finish, "zoom_pct": self.var_zoom_pct,
            "input_mode": self.var_input_mode, "search_url": self.var_search_url,
            "search_input_sel": self.var_search_input_sel, "search_btn_sel": self.var_search_btn_sel,
            "load_wait": self.var_load_wait, "stop_loading": self.var_stop_loading,
            "dedupe": self.var_dedupe, "browser_mode": self.var_browser_mode,
            "headless": self.var_headless, "incognito": self.var_incognito,
            "stealth": self.var_stealth,
            "url_delay": self.var_url_delay, "step_timeout": self.var_step_timeout,
            "step_delay": self.var_step_delay, "continue": self.var_continue,
            "retries": self.var_retries, "workers": self.var_workers,
            "resume": self.var_resume,
        }
        self.load_settings()
        self.build_ui()
        if self.saved_links:
            self.txt_links.insert("1.0", self.saved_links)
            self.update_link_count()
        if self.saved_keywords:
            self.txt_keywords.insert("1.0", self.saved_keywords)
            self.update_kw_count()
        self.switch_input_mode()
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(100, self.poll_queue)
        self.after(2000, lambda: self.trigger_update_check(manual=False))

    def get_site_entry(self, site_key=None):
        sk = site_key if site_key is not None else self.current_set
        if sk not in self.sequence_sets:
            self.sequence_sets[sk] = normalize_site_entry([])
        else:
            self.sequence_sets[sk] = normalize_site_entry(self.sequence_sets[sk])
        return self.sequence_sets[sk]

    @property
    def current_module(self):
        entry = self.get_site_entry()
        return entry["active_module"]

    @current_module.setter
    def current_module(self, mod_name):
        entry = self.get_site_entry()
        if mod_name not in entry["modules"]:
            entry["modules"][mod_name] = {"pattern": "", "steps": []}
        entry["active_module"] = mod_name

    @property
    def sequence(self):
        entry = self.get_site_entry()
        mod = entry["modules"][entry["active_module"]]
        return mod.setdefault("steps", [])

    @sequence.setter
    def sequence(self, value):
        entry = self.get_site_entry()
        entry["modules"][entry["active_module"]]["steps"] = value

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
        if isinstance(data.get("sequence_sets"), dict):
            self.sequence_sets = {
                k: normalize_site_entry(v) for k, v in data["sequence_sets"].items()
            }
            self.sequence_sets.setdefault(ALL_SITES, normalize_site_entry([]))
        if isinstance(data.get("site_settings"), dict):
            self.site_settings = data["site_settings"]
        if data.get("current_set") in (set(self.sequence_sets) | set(self.site_settings)):
            self.current_set = data["current_set"]
            self.get_site_entry(self.current_set)
        if isinstance(data.get("links"), str):
            self.saved_links = data["links"]
        if isinstance(data.get("keywords"), str):
            self.saved_keywords = data["keywords"]

    def save_settings(self):
        data = {key: var.get() for key, var in self.persist.items() if hasattr(var, "get")}
        data["sequence_sets"] = self.sequence_sets
        data["site_settings"] = self.site_settings
        data["current_set"] = self.current_set
        data["links"] = self.txt_links.get("1.0", "end").strip()
        data["keywords"] = self.txt_keywords.get("1.0", "end").strip()
        try:
            path = settings_file()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

    def trigger_update_check(self, manual=False):
        if self.update_checking:
            if manual:
                self.log("Update check already in progress...")
            return
        if self.staged_update_path and os.path.exists(self.staged_update_path):
            if manual:
                if messagebox.askyesno(
                    "Update Ready",
                    f"Version {self.staged_update_version} is already downloaded and ready.\n"
                    f"Close and apply update now?\n(It will also apply automatically when you exit.)",
                ):
                    self.restart_for_update = True
                    self.on_close()
            return
        self.update_checking = True
        if manual:
            self.btn_update.config(text="Checking...", state="disabled")
        threading.Thread(target=self._update_worker, args=(manual,), daemon=True).start()

    def _update_worker(self, manual=False):
        try:
            req = urllib.request.Request(
                GITHUB_API_LATEST,
                headers={"User-Agent": f"AE-Web-Scrapper/{APP_VERSION}", "Accept": "application/vnd.github+json"},
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                release = json.loads(resp.read().decode("utf-8"))

            tag = str(release.get("tag_name") or release.get("name") or "").strip()
            latest_clean = tag.lstrip("vV")
            if not latest_clean or parse_ver_tuple(latest_clean) <= parse_ver_tuple(APP_VERSION):
                self.msg_queue.put(("update_result", {"status": "up_to_date", "manual": manual, "ver": tag or APP_VERSION}))
                return

            assets = release.get("assets") or []
            exe_asset = next((a for a in assets if str(a.get("name", "")).lower().endswith(".exe")), None)
            if not exe_asset:
                self.msg_queue.put(("update_result", {"status": "no_asset", "manual": manual, "ver": tag}))
                return

            if not getattr(sys, "frozen", False):
                self.msg_queue.put(("update_result", {"status": "dev_mode", "manual": manual, "ver": tag}))
                return

            dl_url = exe_asset.get("browser_download_url")
            staged_path = os.path.join(tempfile.gettempdir(), f"AE-Web-Scrapper_v{latest_clean}.exe")
            tmp_part = staged_path + ".part"

            dl_req = urllib.request.Request(dl_url, headers={"User-Agent": f"AE-Web-Scrapper/{APP_VERSION}"})
            with urllib.request.urlopen(dl_req, timeout=180) as r, open(tmp_part, "wb") as out_f:
                shutil.copyfileobj(r, out_f)
            os.replace(tmp_part, staged_path)

            self.msg_queue.put(("update_result", {
                "status": "staged",
                "manual": manual,
                "ver": tag,
                "path": staged_path,
            }))
        except Exception as e:
            self.msg_queue.put(("update_result", {"status": "error", "manual": manual, "err": str(e)}))

    def export_settings_file(self):
        self.save_settings()
        f = filedialog.asksaveasfilename(title="Export Settings JSON", defaultextension=".json", initialfile="scraper_settings.json", filetypes=[("JSON files", "*.json")])
        if f:
            try:
                with open(settings_file(), encoding="utf-8") as src, open(f, "w", encoding="utf-8") as dst:
                    dst.write(src.read())
                self.log(f"Settings exported to: {f}")
            except Exception as e:
                messagebox.showerror("Export Settings", f"Error:\n{e}")

    def import_settings_file(self):
        f = filedialog.askopenfilename(title="Import Settings JSON", filetypes=[("JSON files", "*.json")])
        if f:
            try:
                with open(f, encoding="utf-8") as src:
                    content = src.read()
                json.loads(content)
                path = settings_file()
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as dst:
                    dst.write(content)
                self.load_settings()
                self.refresh_sets()
                self.refresh_sequence()
                self.switch_input_mode()
                self.log(f"Settings imported from: {f}")
            except Exception as e:
                messagebox.showerror("Import Settings", f"Invalid settings file:\n{e}")

    def kill_all_chrome(self):
        if not messagebox.askyesno("Kill Chrome", "Force close all background chrome.exe processes?"):
            return
        try:
            if sys.platform.startswith("win"):
                subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.run(["pkill", "-f", "chrome"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.log("All background Chrome processes terminated.")
        except Exception as e:
            self.log(f"Error killing Chrome: {e}")

    def build_ui(self):
        self.apply_theme()
        pad = {"padx": 8, "pady": 3}

        self.toolbar = ttk.Frame(self, style="Toolbar.TFrame")
        self.toolbar.pack(side="top", fill="x")
        tb = ttk.Frame(self.toolbar, style="Toolbar.TFrame")
        tb.pack(fill="x", padx=12, pady=9)
        self.btn_start = ttk.Button(tb, text="\u25B6 Start Scraping", style="Accent.TButton", command=self.start)
        self.btn_start.pack(side="left")
        self.btn_stop = ttk.Button(tb, text="\u25A0 Stop", style="Toolbar.TButton", command=self.stop, state="disabled")
        self.btn_stop.pack(side="left", padx=(8, 0))
        self.btn_test = ttk.Button(tb, text="Test on 1st Item", style="Toolbar.TButton", command=self.test_first)
        self.btn_test.pack(side="left", padx=(8, 0))

        self.btn_options = ttk.Button(tb, text="", style="Toolbar.TButton", command=self.toggle_options)
        self.btn_options.pack(side="right")
        self.btn_update = ttk.Button(tb, text="Check Update", style="Toolbar.TButton", command=lambda: self.trigger_update_check(manual=True))
        self.btn_update.pack(side="right", padx=(0, 8))
        self.btn_export = ttk.Button(tb, text="Export Excel (Multi-Sheet)", style="Toolbar.TButton", command=self.export_excel)
        self.btn_export.pack(side="right", padx=(0, 8))
        self.btn_folder = ttk.Button(tb, text="Open folder", style="Toolbar.TButton", command=self.open_folder)
        self.btn_folder.pack(side="right", padx=(0, 8))

        status_line = ttk.Frame(self, style="StatusLine.TFrame", height=4)
        status_line.pack(side="bottom", fill="x")
        status = ttk.Frame(self, style="Status.TFrame")
        status.pack(side="bottom", fill="x")
        self.lbl_summary = ttk.Label(status, text="", style="Status.TLabel")
        self.lbl_summary.pack(side="left", padx=12, pady=7)
        self.lbl_progress = ttk.Label(status, text="0 / 0", style="Status.TLabel")
        self.lbl_progress.pack(side="right", padx=12)
        self.progress = ttk.Progressbar(status, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, padx=(0, 6))

        box = ttk.LabelFrame(self, text="Global Scraper Options (Browser, Profile, Zoom & Timings)")
        self.opt_box = box
        box.columnconfigure(1, weight=1)

        r0 = ttk.Frame(box)
        r0.grid(row=0, column=0, columnspan=3, sticky="ew", **pad)
        ttk.Label(r0, text="Save folder:").pack(side="left")
        ttk.Entry(r0, textvariable=self.var_folder).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(r0, text="Browse...", command=self.pick_folder).pack(side="left")

        r1 = ttk.Frame(box)
        r1.grid(row=1, column=0, columnspan=3, sticky="ew", **pad)
        ttk.Checkbutton(r1, text="Use Real Chrome (Port:", variable=self.var_use_real_chrome, command=self.update_summary).pack(side="left")
        ttk.Spinbox(r1, from_=9000, to=9999, width=5, textvariable=self.var_debug_port).pack(side="left", padx=3)
        ttk.Label(r1, text=")  Profile Dir:").pack(side="left")
        ttk.Entry(r1, textvariable=self.var_chrome_profile, width=22).pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(r1, text="Browse Profile...", command=self.pick_chrome_profile).pack(side="left", padx=(0, 4))
        ttk.Button(r1, text="Clear", command=lambda: self.var_chrome_profile.set("")).pack(side="left", padx=(0, 8))
        ttk.Label(r1, text="chrome.exe:").pack(side="left")
        ttk.Entry(r1, textvariable=self.var_chrome_exe, width=16).pack(side="left", padx=4)
        ttk.Button(r1, text="...", width=3, command=self.pick_chrome_exe).pack(side="left", padx=(0, 6))
        ttk.Button(r1, text="Kill Chrome", command=self.kill_all_chrome).pack(side="left")

        r2 = ttk.Frame(box)
        r2.grid(row=2, column=0, columnspan=3, sticky="w", **pad)
        ttk.Label(r2, text="Load wait (s):").pack(side="left")
        ttk.Spinbox(r2, from_=1, to=120, width=4, textvariable=self.var_load_wait).pack(side="left", padx=(3, 10))
        ttk.Label(r2, text="Step timeout (s):").pack(side="left")
        ttk.Spinbox(r2, from_=1, to=120, width=4, textvariable=self.var_step_timeout).pack(side="left", padx=(3, 10))
        ttk.Label(r2, text="Step delay (s):").pack(side="left")
        ttk.Spinbox(r2, from_=0, to=60, increment=0.5, width=4, textvariable=self.var_step_delay).pack(side="left", padx=(3, 10))
        ttk.Label(r2, text="URL/Search delay (s):").pack(side="left")
        ttk.Spinbox(r2, from_=0, to=300, increment=0.5, width=4, textvariable=self.var_url_delay).pack(side="left", padx=(3, 10))
        ttk.Label(r2, text="Zoom (%):").pack(side="left")
        ttk.Spinbox(r2, from_=25, to=200, increment=10, width=5, textvariable=self.var_zoom_pct).pack(side="left", padx=(3, 10))
        ttk.Label(r2, text="Workers:").pack(side="left")
        ttk.Spinbox(r2, from_=1, to=4, width=3, textvariable=self.var_workers).pack(side="left", padx=(3, 0))

        r3 = ttk.Frame(box)
        r3.grid(row=3, column=0, columnspan=3, sticky="ew", **pad)
        ttk.Checkbutton(r3, text="Close browser when finished", variable=self.var_close_on_finish).pack(side="left", padx=(0, 10))
        ttk.Checkbutton(r3, text="Incognito", variable=self.var_incognito, command=self.update_summary).pack(side="left", padx=(0, 10))
        ttk.Checkbutton(r3, text="Headless", variable=self.var_headless).pack(side="left", padx=(0, 10))
        ttk.Checkbutton(r3, text="Reuse browser", variable=self.var_browser_mode, onvalue="single", offvalue="each").pack(side="left", padx=(0, 10))
        ttk.Checkbutton(r3, text="Stop loading early", variable=self.var_stop_loading).pack(side="left", padx=(0, 10))
        ttk.Checkbutton(r3, text="Stealth", variable=self.var_stealth).pack(side="left", padx=(0, 10))
        ttk.Checkbutton(r3, text="Resume", variable=self.var_resume).pack(side="left", padx=(0, 10))
        ttk.Checkbutton(r3, text="Continue if missing", variable=self.var_continue).pack(side="left")

        site_bar = ttk.LabelFrame(self, text="Site Profile, Multi-Module Templates & Local Settings Backup")
        site_bar.pack(fill="x", padx=10, pady=(4, 0))

        sb_in = ttk.Frame(site_bar)
        sb_in.pack(fill="x", padx=8, pady=(5, 2))

        ttk.Label(sb_in, text="Active Site:").pack(side="left")
        self.cmb_set = ttk.Combobox(sb_in, state="readonly", width=24)
        self.cmb_set.pack(side="left", padx=(6, 6))
        self.cmb_set.bind("<<ComboboxSelected>>", self.on_set_selected)

        ttk.Button(sb_in, text="+ New site...", command=self.add_site).pack(side="left")
        ttk.Button(sb_in, text="Rename...", command=self.rename_site).pack(side="left", padx=4)
        ttk.Button(sb_in, text="Site Options...", style="Accent.TButton", command=self.edit_site_options).pack(side="left", padx=4)
        ttk.Button(sb_in, text="Delete", command=self.delete_site).pack(side="left", padx=4)

        ttk.Button(sb_in, text="Import Settings", command=self.import_settings_file).pack(side="right", padx=(4, 0))
        ttk.Button(sb_in, text="Export Settings", command=self.export_settings_file).pack(side="right", padx=(8, 0))
        self.lbl_site_info = ttk.Label(sb_in, text="", foreground="#0E8EE6")
        self.lbl_site_info.pack(side="right", padx=8)

        mod_in = ttk.Frame(site_bar)
        mod_in.pack(fill="x", padx=8, pady=(2, 6))

        ttk.Label(mod_in, text="Site Module:").pack(side="left")
        self.cmb_mod = ttk.Combobox(mod_in, state="readonly", width=22)
        self.cmb_mod.pack(side="left", padx=(6, 6))
        self.cmb_mod.bind("<<ComboboxSelected>>", self.on_module_selected)

        ttk.Button(mod_in, text="+ Add Module", command=self.add_module).pack(side="left")
        ttk.Button(mod_in, text="Duplicate", command=self.duplicate_module).pack(side="left", padx=4)
        ttk.Button(mod_in, text="Rename", command=self.rename_module).pack(side="left", padx=2)
        ttk.Button(mod_in, text="Delete", command=self.delete_module).pack(side="left", padx=4)

        ttk.Label(mod_in, text="Auto-Match URL Pattern (opt):").pack(side="left", padx=(14, 4))
        ent_pat = ttk.Entry(mod_in, textvariable=self.var_mod_pattern, width=28)
        ent_pat.pack(side="left", fill="x", expand=True)
        ent_pat.bind("<KeyRelease>", self.on_pattern_changed)
        ttk.Label(mod_in, text="(e.g. /p/ | datasheet | re:\\d+)", foreground="#6E6E6E").pack(side="left", padx=(6, 0))

        pane_opts = dict(sashwidth=8, sashrelief="flat", bg="#E9ECF1", bd=0, opaqueresize=True)
        main_pane = tk.PanedWindow(self, orient="vertical", **pane_opts)
        main_pane.pack(fill="both", expand=True, padx=10, pady=4)
        mid = tk.PanedWindow(main_pane, orient="horizontal", **pane_opts)
        main_pane.add(mid, stretch="always", minsize=240)

        left_box = ttk.LabelFrame(mid, text="1. Input Source (Direct URLs vs Keyword Search Mode)")
        mid.add(left_box, stretch="always", minsize=340)

        mode_bar = ttk.Frame(left_box)
        mode_bar.pack(fill="x", padx=6, pady=(5, 2))
        ttk.Radiobutton(mode_bar, text="Direct URLs List", variable=self.var_input_mode, value="urls", command=self.switch_input_mode).pack(side="left", padx=(0, 12))
        ttk.Radiobutton(mode_bar, text="Keyword Search Mode (Search Box)", variable=self.var_input_mode, value="search", command=self.switch_input_mode).pack(side="left")

        self.frm_urls = ttk.Frame(left_box)
        self.txt_links = scrolledtext.ScrolledText(self.frm_urls, height=10, width=36, wrap="none", **TEXT_OPTS)
        self.txt_links.pack(fill="both", expand=True, padx=6, pady=4)
        bar_u = ttk.Frame(self.frm_urls)
        bar_u.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Button(bar_u, text="Load .txt", command=self.load_links_file).pack(side="left")
        ttk.Button(bar_u, text="Auto-Detect Sites", command=self.auto_detect_sites).pack(side="left", padx=4)
        ttk.Button(bar_u, text="Clear", command=lambda: self.txt_links.delete("1.0", "end")).pack(side="left")
        self.lbl_count = ttk.Label(bar_u, text="0 links")
        self.lbl_count.pack(side="right")
        self.txt_links.bind("<<Modified>>", self.on_links_modified)

        self.frm_search = ttk.Frame(left_box)
        s_grid = ttk.Frame(self.frm_search)
        s_grid.pack(fill="x", padx=6, pady=4)
        s_grid.columnconfigure(1, weight=1)

        ttk.Label(s_grid, text="Search Page URL:").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(s_grid, textvariable=self.var_search_url).grid(row=0, column=1, columnspan=2, sticky="ew", padx=(4, 0), pady=2)

        ttk.Label(s_grid, text="Search Input Box:").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(s_grid, textvariable=self.var_search_input_sel).grid(row=1, column=1, sticky="ew", padx=4, pady=2)
        self.btn_pick_search = ttk.Button(s_grid, text="Pick Box", command=lambda: self.toggle_record("searchbox"))
        self.btn_pick_search.grid(row=1, column=2, pady=2)

        ttk.Label(s_grid, text="Submit Btn (opt):").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(s_grid, textvariable=self.var_search_btn_sel).grid(row=2, column=1, columnspan=2, sticky="ew", padx=(4, 0), pady=2)

        ttk.Label(self.frm_search, text="Keywords / Part Numbers (one per line):").pack(anchor="w", padx=6)
        self.txt_keywords = scrolledtext.ScrolledText(self.frm_search, height=6, width=36, wrap="none", **TEXT_OPTS)
        self.txt_keywords.pack(fill="both", expand=True, padx=6, pady=4)
        bar_k = ttk.Frame(self.frm_search)
        bar_k.pack(fill="x", padx=6, pady=(0, 6))
        ttk.Button(bar_k, text="Load Keywords .txt", command=self.load_keywords_file).pack(side="left")
        ttk.Button(bar_k, text="Clear", command=lambda: self.txt_keywords.delete("1.0", "end")).pack(side="left", padx=4)
        self.lbl_kw_count = ttk.Label(bar_k, text="0 keywords")
        self.lbl_kw_count.pack(side="right")
        self.txt_keywords.bind("<<Modified>>", self.on_kw_modified)

        self.seq_box = ttk.LabelFrame(mid, text="2. Module Workflow (Drag & Drop rows to reorder | Hold Alt+Click in browser to bypass)")
        mid.add(self.seq_box, stretch="always", minsize=560)
        self.lst_seq = tk.Listbox(self.seq_box, height=8, activestyle="none", exportselection=False, **LIST_OPTS)
        self.lst_seq.pack(fill="both", expand=True, padx=6, pady=(6, 4))

        self.lst_seq.bind("<Button-1>", self.on_drag_start)
        self.lst_seq.bind("<B1-Motion>", self.on_drag_motion)
        self.lst_seq.bind("<ButtonRelease-1>", self.on_drag_release)

        sr1 = ttk.Frame(self.seq_box)
        sr1.pack(fill="x", padx=6, pady=2)
        self.btn_rec_click = ttk.Button(sr1, text="\u25CF Record Click", command=lambda: self.toggle_record("click"))
        self.btn_rec_click.pack(side="left")
        self.btn_rec_extract = ttk.Button(sr1, text="\u25CF Pick Extract Element", style="Accent.TButton", command=lambda: self.toggle_record("extract"))
        self.btn_rec_extract.pack(side="left", padx=3)
        ttk.Button(sr1, text="+ Set Select / Show All", command=self.add_select_value_step).pack(side="left", padx=3)
        ttk.Button(sr1, text="+ Manual Field", command=self.add_manual_extract).pack(side="left", padx=3)
        ttk.Button(sr1, text="+ Zoom", command=self.add_zoom_step).pack(side="left", padx=3)
        ttk.Button(sr1, text="+ Wait", command=self.add_wait).pack(side="left")

        sr2 = ttk.Frame(self.seq_box)
        sr2.pack(fill="x", padx=6, pady=(2, 6))
        ttk.Button(sr2, text="Rename / Edit Val", command=self.rename_or_edit_seq).pack(side="left")
        ttk.Button(sr2, text="Text / Link / Both", command=self.toggle_extract_attr).pack(side="left", padx=3)
        ttk.Button(sr2, text="Single / Multi List", command=self.toggle_multi_mode).pack(side="left", padx=3)
        ttk.Button(sr2, text="All / 1st Only", command=self.toggle_first_link_only).pack(side="left", padx=3)
        ttk.Button(sr2, text="Delete", command=self.delete_seq_item).pack(side="left", padx=3)
        ttk.Button(sr2, text="Up", width=3, command=lambda: self.move_seq(-1)).pack(side="left", padx=2)
        ttk.Button(sr2, text="Down", width=5, command=lambda: self.move_seq(1)).pack(side="left")
        ttk.Button(sr2, text="Clear", command=self.clear_seq).pack(side="right")

        logf = ttk.LabelFrame(main_pane, text="Scraping Log")
        main_pane.add(logf, stretch="always", minsize=90)
        self.txt_log = scrolledtext.ScrolledText(logf, height=7, state="disabled", **TEXT_OPTS)
        self.txt_log.pack(fill="both", expand=True, padx=6, pady=6)

        self.refresh_sets()
        self.refresh_sequence()
        self.update_summary()
        self.set_options(True)

    def switch_input_mode(self):
        if self.var_input_mode.get() == "search":
            self.frm_urls.pack_forget()
            self.frm_search.pack(fill="both", expand=True)
        else:
            self.frm_search.pack_forget()
            self.frm_urls.pack(fill="both", expand=True)
        self.update_summary()

    def on_drag_start(self, event):
        idx = self.lst_seq.nearest(event.y)
        if 0 <= idx < len(self.sequence):
            self.drag_index = idx
            self.lst_seq.selection_clear(0, "end")
            self.lst_seq.selection_set(idx)

    def on_drag_motion(self, event):
        if self.drag_index is None:
            return
        target = self.lst_seq.nearest(event.y)
        if 0 <= target < len(self.sequence) and target != self.drag_index:
            item = self.sequence.pop(self.drag_index)
            self.sequence.insert(target, item)
            self.drag_index = target
            self.refresh_sequence(select=target)

    def on_drag_release(self, _event):
        self.drag_index = None

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

        flat_button("TButton", TAB, "#333333", "#DDDDDD", "#D0D0D0", "#F4F4F4", "#A8A8A8", (6, 4))
        flat_button("Accent.TButton", BLUE, "white", BLUE_DARK, "#0A7DCC", "#A8D9FB", "white", (10, 5), bold=True)
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
            self.opt_box.pack(fill="x", padx=10, pady=(6, 0), after=self.toolbar)
        else:
            self.opt_box.pack_forget()
        self.btn_options.config(text=f"\u2630 Global Options {'\u25BE' if show else '\u25B8'}")

    def update_summary(self):
        extract_count = sum(1 for item in self.sequence if item["type"] == "extract")
        mode_lbl = "Search Mode" if self.var_input_mode.get() == "search" else "URLs Mode"
        engine_txt = f"Real Chrome (:{num(self.var_debug_port, 9222)})" if self.var_use_real_chrome.get() else "Auto ChromeDriver"
        inc_txt = "   \u00B7   Incognito: ON" if self.var_incognito.get() else ""
        self.lbl_summary.config(
            text=f"Mode: {mode_lbl}   \u00B7   Engine: {engine_txt}{inc_txt}   \u00B7   Zoom: {num(self.var_zoom_pct, 100)}%   \u00B7   Module [{self.current_module}]: {len(self.sequence)} steps ({extract_count} fields)"
        )
        if self.current_set == ALL_SITES:
            self.lbl_site_info.config(text="Using Global Options")
        elif self.current_set in self.site_settings:
            self.lbl_site_info.config(text=f"Custom Options: [{self.current_set}]")
        else:
            self.lbl_site_info.config(text=f"Global Options: [{self.current_set}]")

    def update_link_count(self):
        links = self.get_links()
        hosts = {host_of(u) for u in links if host_of(u)}
        self.lbl_count.config(text=f"{len(links)} links ({len(hosts)} domains)")

    def update_kw_count(self):
        kws = self.get_keywords()
        self.lbl_kw_count.config(text=f"{len(kws)} keywords")

    def on_links_modified(self, _event=None):
        if self.txt_links.edit_modified():
            self.update_link_count()
            self.txt_links.edit_modified(False)

    def on_kw_modified(self, _event=None):
        if self.txt_keywords.edit_modified():
            self.update_kw_count()
            self.txt_keywords.edit_modified(False)

    def get_links(self, dedupe=True):
        raw = self.txt_links.get("1.0", "end").splitlines()
        links = [x.strip() for x in raw if x.strip()]
        return list(dict.fromkeys(links)) if (dedupe and self.var_dedupe.get()) else links

    def get_keywords(self, dedupe=True):
        raw = self.txt_keywords.get("1.0", "end").splitlines()
        kws = [x.strip() for x in raw if x.strip()]
        return list(dict.fromkeys(kws)) if (dedupe and self.var_dedupe.get()) else kws

    def auto_detect_sites(self):
        links = self.get_links()
        added = 0
        for u in links:
            h = host_of(u)
            if h and h not in self.sequence_sets:
                self.sequence_sets[h] = normalize_site_entry([])
                added += 1
        self.refresh_sets()
        self.update_summary()
        messagebox.showinfo("Auto-Detect Sites", f"Added {added} new site profile(s) from your links.")

    def pick_folder(self):
        d = filedialog.askdirectory(title="Choose save folder")
        if d:
            self.var_folder.set(d)

    def pick_chrome_profile(self):
        local_chrome = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "User Data")
        init_dir = local_chrome if os.path.isdir(local_chrome) else None
        d = filedialog.askdirectory(title="Choose Chrome Profile Folder (e.g. Default or Profile 1)", initialdir=init_dir)
        if d:
            self.var_chrome_profile.set(d)

    def pick_chrome_exe(self):
        f = filedialog.askopenfilename(title="Choose chrome.exe", filetypes=[("Chrome Executable", "chrome.exe"), ("All files", "*.*")])
        if f:
            self.var_chrome_exe.set(f)

    def load_links_file(self):
        f = filedialog.askopenfilename(title="Choose links file", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if f:
            with open(f, encoding="utf-8", errors="ignore") as fh:
                self.txt_links.delete("1.0", "end")
                self.txt_links.insert("1.0", fh.read())

    def load_keywords_file(self):
        f = filedialog.askopenfilename(title="Choose keywords file", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if f:
            with open(f, encoding="utf-8", errors="ignore") as fh:
                self.txt_keywords.delete("1.0", "end")
                self.txt_keywords.insert("1.0", fh.read())

    def open_folder(self):
        folder = self.var_folder.get().strip()
        if folder and os.path.isdir(folder):
            open_file(folder)
        else:
            messagebox.showinfo("Open folder", "Choose an existing save folder first.")

    def export_excel(self):
        folder = self.var_folder.get().strip()
        json_path = os.path.join(folder, "Scraped_Results.jsonl") if folder else ""
        if not json_path or not os.path.exists(json_path):
            messagebox.showinfo("Export Excel", "No scraped data found yet.")
            return

        by_sheet = {}
        with open(json_path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                site_key = rec.get("site_profile", "General")
                mod_name = rec.get("module_name") or DEFAULT_MODULE
                sheet_key = f"{site_key} - {mod_name}" if mod_name != DEFAULT_MODULE else site_key
                by_sheet.setdefault(sheet_key, []).append(rec)

        sheets_dict = {}
        for sheet_key, records in by_sheet.items():
            field_names = []
            for r in records:
                for k in r.get("fields", {}).keys():
                    if k not in field_names:
                        field_names.append(k)

            header = ["Module", "Keyword", "Input Link", "Final URL", "Page Title", "Row #", "Status", "Notes", "Timestamp"] + field_names
            rows = [header]
            for r in records:
                fdict = r.get("fields", {})
                row = [
                    r.get("module_name", DEFAULT_MODULE),
                    r.get("keyword", ""),
                    r.get("link", ""),
                    r.get("final_url", r.get("link", "")),
                    r.get("title", ""),
                    r.get("row_index", 1),
                    r.get("status", ""),
                    r.get("notes", ""),
                    r.get("timestamp", ""),
                ] + [fdict.get(fn, "") for fn in field_names]
                rows.append(row)
            sheets_dict[sheet_key] = rows

        out_xlsx = os.path.join(folder, "MultiSite_Extracted_Data.xlsx")
        try:
            write_multi_sheet_xlsx(out_xlsx, sheets_dict)
            self.log(f"Exported multi-sheet Excel: {out_xlsx}")
            open_file(out_xlsx)
        except Exception as e:
            messagebox.showerror("Export Excel", f"Error writing Excel:\n{e}")

    # ----- Site Profiles, Modules & Per-Site Options -----
    def refresh_modules_ui(self):
        entry = self.get_site_entry()
        mods = list(entry["modules"].keys())
        act = entry["active_module"]
        self.cmb_mod.config(values=mods)
        self.cmb_mod.set(act)
        self.var_mod_pattern.set(entry["modules"][act].get("pattern", ""))
        self.seq_box.config(text=f"2. Module Workflow [{self.current_set} :: {act}] (Drag & Drop rows to reorder | Hold Alt+Click to bypass)")

    def on_module_selected(self, _event=None):
        chosen = self.cmb_mod.get()
        if chosen:
            self.current_module = chosen
            self.refresh_modules_ui()
            self.refresh_sequence()
            self.update_summary()

    def on_pattern_changed(self, _event=None):
        entry = self.get_site_entry()
        entry["modules"][entry["active_module"]]["pattern"] = self.var_mod_pattern.get()

    def add_module(self):
        name = simpledialog.askstring("New Module", f"Enter module name for [{self.current_set}]:", parent=self)
        mname = (name or "").strip()
        if not mname:
            return
        entry = self.get_site_entry()
        if mname in entry["modules"]:
            messagebox.showwarning("New Module", f"Module '{mname}' already exists in this site.")
            return
        entry["modules"][mname] = {"pattern": "", "steps": []}
        entry["active_module"] = mname
        self.refresh_modules_ui()
        self.refresh_sequence()
        self.update_summary()

    def duplicate_module(self):
        entry = self.get_site_entry()
        src_name = entry["active_module"]
        new_name = simpledialog.askstring("Duplicate Module", f"Copy '{src_name}' as:", initialvalue=f"{src_name}_Copy", parent=self)
        mname = (new_name or "").strip()
        if not mname:
            return
        if mname in entry["modules"]:
            messagebox.showwarning("Duplicate Module", f"Module '{mname}' already exists.")
            return
        src_mod = entry["modules"][src_name]
        entry["modules"][mname] = {
            "pattern": src_mod.get("pattern", ""),
            "steps": json.loads(json.dumps(src_mod.get("steps", []))),
        }
        entry["active_module"] = mname
        self.refresh_modules_ui()
        self.refresh_sequence()
        self.update_summary()

    def rename_module(self):
        entry = self.get_site_entry()
        old_name = entry["active_module"]
        new_name = simpledialog.askstring("Rename Module", "Enter new module name:", initialvalue=old_name, parent=self)
        mname = (new_name or "").strip()
        if not mname or mname == old_name:
            return
        if mname in entry["modules"]:
            messagebox.showwarning("Rename Module", f"Module '{mname}' already exists.")
            return
        entry["modules"][mname] = entry["modules"].pop(old_name)
        entry["active_module"] = mname
        self.refresh_modules_ui()
        self.refresh_sequence()
        self.update_summary()

    def delete_module(self):
        entry = self.get_site_entry()
        if len(entry["modules"]) <= 1:
            messagebox.showinfo("Delete Module", "Each site must keep at least one module.")
            return
        mname = entry["active_module"]
        if messagebox.askyesno("Delete Module", f"Delete module '{mname}' from '{self.current_set}'?"):
            entry["modules"].pop(mname, None)
            entry["active_module"] = next(iter(entry["modules"]))
            self.refresh_modules_ui()
            self.refresh_sequence()
            self.update_summary()

    def refresh_sets(self):
        keys = [ALL_SITES] + sorted((set(self.sequence_sets) | set(self.site_settings)) - {ALL_SITES})
        self.cmb_set.config(values=[ALL_SITES_LABEL if k == ALL_SITES else k for k in keys])
        self.cmb_set.set(ALL_SITES_LABEL if self.current_set == ALL_SITES else self.current_set)
        self.get_site_entry(self.current_set)
        self.refresh_modules_ui()
        self.update_summary()

    def on_set_selected(self, _event=None):
        label = self.cmb_set.get()
        self.current_set = ALL_SITES if label == ALL_SITES_LABEL else label
        self.get_site_entry(self.current_set)
        self.refresh_modules_ui()
        self.refresh_sequence()
        self.update_summary()

    def add_site(self):
        links = self.get_links()
        first = next((host_of(u) for u in links if host_of(u) not in self.sequence_sets), "")
        text = simpledialog.askstring("New Site Profile", "Enter domain name (e.g. st.com, ti.com):", initialvalue=first, parent=self)
        host = host_of(text.strip()) if text else ""
        if host:
            self.sequence_sets.setdefault(host, normalize_site_entry([]))
            self.current_set = host
            self.refresh_sets()
            self.refresh_sequence()

    def rename_site(self):
        if self.current_set == ALL_SITES:
            messagebox.showinfo("Rename Site", "Cannot rename 'All sites (default)'. Select a specific site first.")
            return
        old_host = self.current_set
        new_text = simpledialog.askstring("Rename Site", "Enter new domain / profile name:", initialvalue=old_host, parent=self)
        new_host = host_of(new_text.strip()) if new_text else ""
        if not new_host or new_host == old_host:
            return
        if new_host in self.sequence_sets:
            messagebox.showwarning("Rename Site", f"A profile named '{new_host}' already exists.")
            return
        self.sequence_sets[new_host] = self.sequence_sets.pop(old_host, normalize_site_entry([]))
        if old_host in self.site_settings:
            self.site_settings[new_host] = self.site_settings.pop(old_host)
        self.current_set = new_host
        self.refresh_sets()
        self.refresh_sequence()
        self.log(f"Site renamed: {old_host} -> {new_host}")

    def delete_site(self):
        if self.current_set != ALL_SITES and messagebox.askyesno("Delete Site", f"Delete profile and settings for '{self.current_set}'?"):
            self.sequence_sets.pop(self.current_set, None)
            self.site_settings.pop(self.current_set, None)
            self.current_set = ALL_SITES
            self.refresh_sets()
            self.refresh_sequence()

    def edit_site_options(self):
        if self.current_set == ALL_SITES:
            messagebox.showinfo("Site Options", "Select a specific site first (or click '+ New site...') to customize its options.")
            return
        host = self.current_set
        cur = self.site_settings.get(host, {})

        dlg = tk.Toplevel(self)
        dlg.title(f"Custom Options for: {host}")
        dlg.transient(self)
        dlg.configure(bg=BG)
        dlg.resizable(False, False)

        v_use = tk.BooleanVar(value=host in self.site_settings)
        v_real = tk.BooleanVar(value=cur.get("use_real_chrome", self.var_use_real_chrome.get()))
        v_load = tk.IntVar(value=cur.get("load_wait", num(self.var_load_wait, 5)))
        v_tout = tk.DoubleVar(value=cur.get("step_timeout", num(self.var_step_timeout, 10)))
        v_sdel = tk.DoubleVar(value=cur.get("step_delay", num(self.var_step_delay, 1.5)))
        v_udel = tk.DoubleVar(value=cur.get("url_delay", num(self.var_url_delay, 0)))
        v_zoom = tk.IntVar(value=cur.get("zoom_pct", num(self.var_zoom_pct, 100)))
        v_inc = tk.BooleanVar(value=cur.get("incognito", self.var_incognito.get()))
        v_head = tk.BooleanVar(value=cur.get("headless", self.var_headless.get()))
        v_stel = tk.BooleanVar(value=cur.get("stealth", self.var_stealth.get()))
        v_stop = tk.BooleanVar(value=cur.get("stop_loading", self.var_stop_loading.get()))
        v_newb = tk.BooleanVar(value=cur.get("new_browser", self.var_browser_mode.get() == "each"))

        pad = {"padx": 12, "pady": 4}
        ttk.Checkbutton(dlg, text=f"Enable custom options for [{host}]", variable=v_use).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 6))

        ttk.Label(dlg, text="Page load wait (s):").grid(row=1, column=0, sticky="w", **pad)
        ttk.Spinbox(dlg, from_=1, to=120, width=8, textvariable=v_load).grid(row=1, column=1, sticky="w", **pad)

        ttk.Label(dlg, text="Step timeout (s):").grid(row=2, column=0, sticky="w", **pad)
        ttk.Spinbox(dlg, from_=1, to=120, width=8, textvariable=v_tout).grid(row=2, column=1, sticky="w", **pad)

        ttk.Label(dlg, text="Delay between steps (s):").grid(row=3, column=0, sticky="w", **pad)
        ttk.Spinbox(dlg, from_=0, to=60, increment=0.5, width=8, textvariable=v_sdel).grid(row=3, column=1, sticky="w", **pad)

        ttk.Label(dlg, text="Delay between URLs (s):").grid(row=4, column=0, sticky="w", **pad)
        ttk.Spinbox(dlg, from_=0, to=300, increment=0.5, width=8, textvariable=v_udel).grid(row=4, column=1, sticky="w", **pad)

        ttk.Label(dlg, text="Page Zoom (%):").grid(row=5, column=0, sticky="w", **pad)
        ttk.Spinbox(dlg, from_=25, to=200, increment=10, width=8, textvariable=v_zoom).grid(row=5, column=1, sticky="w", **pad)

        ttk.Checkbutton(dlg, text="Use Real Chrome Browser Directly", variable=v_real).grid(row=6, column=0, columnspan=2, sticky="w", **pad)
        ttk.Checkbutton(dlg, text="Incognito Mode", variable=v_inc).grid(row=7, column=0, columnspan=2, sticky="w", **pad)
        ttk.Checkbutton(dlg, text="Hidden Browser (Headless)", variable=v_head).grid(row=8, column=0, columnspan=2, sticky="w", **pad)
        ttk.Checkbutton(dlg, text="Stealth Mode (Anti-Bot)", variable=v_stel).grid(row=9, column=0, columnspan=2, sticky="w", **pad)
        ttk.Checkbutton(dlg, text="Stop loading early", variable=v_stop).grid(row=10, column=0, columnspan=2, sticky="w", **pad)
        ttk.Checkbutton(dlg, text="Reopen fresh browser for every URL", variable=v_newb).grid(row=11, column=0, columnspan=2, sticky="w", **pad)

        def save_site_opts():
            if not v_use.get():
                self.site_settings.pop(host, None)
            else:
                self.site_settings[host] = {
                    "use_real_chrome": bool(v_real.get()),
                    "load_wait": int(v_load.get()),
                    "step_timeout": float(v_tout.get()),
                    "step_delay": float(v_sdel.get()),
                    "url_delay": float(v_udel.get()),
                    "zoom_pct": int(v_zoom.get()),
                    "incognito": bool(v_inc.get()),
                    "headless": bool(v_head.get()),
                    "stealth": bool(v_stel.get()),
                    "stop_loading": bool(v_stop.get()),
                    "new_browser": bool(v_newb.get()),
                }
            dlg.destroy()
            self.update_summary()

        btns = ttk.Frame(dlg)
        btns.grid(row=12, column=0, columnspan=2, sticky="e", padx=12, pady=10)
        ttk.Button(btns, text="Save", style="Accent.TButton", command=save_site_opts).pack(side="left")
        ttk.Button(btns, text="Cancel", command=dlg.destroy).pack(side="left", padx=6)
        dlg.grab_set()

    def refresh_sequence(self, select=None):
        self.lst_seq.delete(0, "end")
        for n, item in enumerate(self.sequence, 1):
            t = item["type"]
            scope_tag = " [1ST ONLY]" if item.get("first_link_only") else ""
            if t == "wait":
                txt = f"{n}.{scope_tag} [WAIT] {item['seconds']:g} s"
            elif t == "zoom":
                txt = f"{n}.{scope_tag} [ZOOM] {item['zoom']}%"
            elif t == "click":
                txt = f"{n}.{scope_tag} [CLICK] -> {item['selector']}"
            elif t == "select_value":
                txt = f"{n}.{scope_tag} [SET SELECT = '{item['value']}'] -> {item['selector']}"
            elif t == "extract":
                mode_tag = "MULTI" if item.get("multi") else "SINGLE"
                attr_map = {"text": "TEXT", "href": "LINK", "both": "TEXT + LINK (2 Cols)"}
                attr_tag = attr_map.get(item.get("extract_attr", "text"), "TEXT")
                txt = f"{n}.{scope_tag} [EXTRACT {attr_tag} | {mode_tag}: {item['name']}] -> {item['selector']}"
            self.lst_seq.insert("end", txt)
        if select is not None and 0 <= select < len(self.sequence):
            self.lst_seq.selection_set(select)
        self.update_summary()

    def add_zoom_step(self):
        z = simpledialog.askinteger("Page Zoom", "Enter Zoom percentage (e.g. 50, 75, 100, 125):", initialvalue=75, minvalue=25, maxvalue=200, parent=self)
        if z:
            self.sequence.append({"type": "zoom", "zoom": z, "first_link_only": False})
            self.refresh_sequence(select=len(self.sequence) - 1)

    def add_select_value_step(self):
        sel = simpledialog.askstring(
            "Dropdown / Page Size Selector",
            "Enter CSS or xpath= selector for the dropdown\n(e.g. select[name*='length'] or .dataTables_length select):",
            initialvalue="select[name*='length']",
            parent=self,
        )
        if not sel or not sel.strip():
            return
        val = simpledialog.askstring(
            "Target Value",
            "Enter text or number to select/inject (e.g. Show All, All, 100, 2000):",
            initialvalue="2000",
            parent=self,
        )
        if not val or not val.strip():
            return
        self.sequence.append({
            "type": "select_value",
            "selector": sel.strip(),
            "value": val.strip(),
            "first_link_only": False,
        })
        self.refresh_sequence(select=len(self.sequence) - 1)

    def toggle_first_link_only(self):
        sel = self.lst_seq.curselection()
        if not sel:
            return
        idx = sel[0]
        item = self.sequence[idx]
        item["first_link_only"] = not item.get("first_link_only", False)
        self.refresh_sequence(select=idx)

    def toggle_extract_attr(self):
        sel = self.lst_seq.curselection()
        if not sel:
            return
        idx = sel[0]
        item = self.sequence[idx]
        if item["type"] != "extract":
            messagebox.showinfo("Info", "Select an Extract field first.")
            return
        order = ["text", "href", "both"]
        cur = item.get("extract_attr", "text")
        nxt = order[(order.index(cur) + 1) % len(order)]
        item["extract_attr"] = nxt
        self.refresh_sequence(select=idx)

    def toggle_multi_mode(self):
        sel = self.lst_seq.curselection()
        if not sel:
            return
        idx = sel[0]
        item = self.sequence[idx]
        if item["type"] != "extract":
            messagebox.showinfo("Info", "Select an Extract field first.")
            return
        item["multi"] = not item.get("multi", False)
        if item["multi"] and item.get("multi_selector"):
            item["selector"], item["multi_selector"] = item["multi_selector"], item["selector"]
        self.refresh_sequence(select=idx)

    def add_manual_extract(self):
        name = simpledialog.askstring("Field Name", "Column Name (e.g. Part Number, Datasheet):", parent=self)
        if not name or not name.strip():
            return
        sel = simpledialog.askstring("Selector", f"CSS or xpath= selector for '{name.strip()}':", parent=self)
        if not sel or not sel.strip():
            return
        is_multi = messagebox.askyesno("Extraction Mode", "Does this selector match MULTIPLE repeating items on the same page?")
        is_both = messagebox.askyesno("Data Type", "Extract BOTH Text and Link into 2 separate columns?")
        attr = "both" if is_both else ("href" if messagebox.askyesno("Link Only", "Extract ONLY the Link URL (href)?") else "text")
        self.sequence.append({
            "type": "extract",
            "name": name.strip(),
            "selector": sel.strip(),
            "multi": is_multi,
            "extract_attr": attr,
            "first_link_only": False,
        })
        self.refresh_sequence(select=len(self.sequence) - 1)

    def delete_seq_item(self):
        sel = self.lst_seq.curselection()
        if sel:
            del self.sequence[sel[0]]
            self.refresh_sequence()

    def move_seq(self, delta):
        sel = self.lst_seq.curselection()
        if not sel:
            return
        i = sel[0]
        j = i + delta
        if 0 <= j < len(self.sequence):
            self.sequence[i], self.sequence[j] = self.sequence[j], self.sequence[i]
            self.refresh_sequence(select=j)

    def clear_seq(self):
        if self.sequence and messagebox.askyesno("Clear", f"Remove all steps in module '{self.current_module}'?"):
            self.sequence = []
            self.refresh_sequence()

    def add_wait(self):
        sec = simpledialog.askfloat("Wait", "Seconds to wait:", minvalue=0.1, maxvalue=60, parent=self)
        if sec:
            self.sequence.append({"type": "wait", "seconds": sec, "first_link_only": False})
            self.refresh_sequence(select=len(self.sequence) - 1)

    def rename_or_edit_seq(self):
        sel = self.lst_seq.curselection()
        if not sel:
            return
        idx = sel[0]
        item = self.sequence[idx]
        if item["type"] == "extract":
            new_name = simpledialog.askstring("Rename Field", "New column name:", initialvalue=item["name"], parent=self)
            if new_name and new_name.strip():
                item["name"] = new_name.strip()
                self.refresh_sequence(select=idx)
        elif item["type"] == "select_value":
            new_val = simpledialog.askstring("Edit Select Value", "New target value (e.g. Show All, 100, 2000):", initialvalue=item["value"], parent=self)
            if new_val and new_val.strip():
                item["value"] = new_val.strip()
                self.refresh_sequence(select=idx)
        elif item["type"] == "zoom":
            new_z = simpledialog.askinteger("Edit Zoom", "New Zoom %:", initialvalue=item["zoom"], minvalue=25, maxvalue=200, parent=self)
            if new_z:
                item["zoom"] = new_z
                self.refresh_sequence(select=idx)

    def toggle_record(self, mode):
        if self.rec_mode is not None:
            self.rec_stop.set()
            return

        if self.var_input_mode.get() == "search" and self.var_search_url.get().strip():
            url = self.var_search_url.get().strip()
        else:
            links = self.get_links()
            if self.current_set != ALL_SITES:
                matched = [u for u in links if host_matches(host_of(u), self.current_set)]
                if matched:
                    url = matched[0]
                elif "." in self.current_set:
                    url = "https://" + self.current_set
                else:
                    url = links[0] if links else simpledialog.askstring("Sample URL", "Enter full URL to open:", parent=self)
            else:
                url = links[0] if links else simpledialog.askstring("Sample URL", "Enter full URL to open:", parent=self)

        if not url:
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        self.rec_mode = mode
        self.rec_stop.clear()
        if mode == "click":
            self.btn_rec_click.config(text="\u25A0 Stop Click Rec")
            self.btn_rec_extract.config(state="disabled")
        elif mode == "searchbox":
            self.btn_pick_search.config(text="\u25A0 Stop")
        else:
            self.btn_rec_extract.config(text="\u25A0 Stop Picking")
            self.btn_rec_click.config(state="disabled")

        rec_cfg = {
            "driver": self.var_driver.get().strip(),
            "chrome_exe": self.var_chrome_exe.get().strip(),
            "chrome_profile": self.var_chrome_profile.get().strip(),
            "use_real_chrome": self.var_use_real_chrome.get(),
            "debug_port": num(self.var_debug_port, 9222),
            "incognito": self.var_incognito.get(),
            "stealth": self.var_stealth.get(),
        }
        threading.Thread(target=self.record_worker, args=(url, mode, rec_cfg), daemon=True).start()

    def drain_logs(self, driver):
        for entry in driver.get_log("browser"):
            m = re.search(r"__REC__([^\"'\s]+)", entry.get("message", ""))
            if m:
                try:
                    data = json.loads(urllib.parse.unquote(m.group(1)))
                    self.msg_queue.put(("rec_event", data))
                except Exception:
                    pass

    def record_worker(self, url, mode, rec_cfg):
        driver = None
        is_real = bool(rec_cfg.get("use_real_chrome"))
        incognito = bool(rec_cfg.get("incognito"))
        try:
            options = webdriver.ChromeOptions()
            options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

            if is_real:
                port = int(rec_cfg.get("debug_port", 9222))
                ok, msg = launch_real_chrome(
                    port=port,
                    headless=False,
                    chrome_path=rec_cfg.get("chrome_exe", ""),
                    custom_profile=rec_cfg.get("chrome_profile", ""),
                    incognito=incognito,
                )
                self.msg_queue.put(("log", msg))
                if not ok:
                    return
                options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
                driver = webdriver.Chrome(service=make_service(rec_cfg["driver"]), options=options)
            else:
                options.add_argument("--start-maximized")
                if incognito:
                    options.add_argument("--incognito")
                if rec_cfg.get("stealth"):
                    apply_stealth_options(options)
                driver = webdriver.Chrome(service=make_service(rec_cfg["driver"]), options=options)
                if rec_cfg.get("stealth"):
                    apply_stealth_driver(driver)

            self.rec_driver = driver
            init_script = f"window.__recMode = '{mode}';\n" + REC_JS
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": init_script})
            driver.get(url)
            driver.execute_script(init_script)

            while not self.rec_stop.is_set():
                try:
                    self.drain_logs(driver)
                except Exception:
                    break
                time.sleep(0.3)
        except Exception as e:
            self.msg_queue.put(("log", f"Browser error: {e}"))
        finally:
            if driver and not is_real:
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
                elif kind == "update_result":
                    self.update_checking = False
                    self.btn_update.config(text="Check Update", state="normal")
                    st = data.get("status")
                    manual = data.get("manual", False)
                    if st == "staged":
                        self.staged_update_path = data["path"]
                        self.staged_update_version = data["ver"]
                        self.btn_update.config(text=f"Update Ready ({data['ver']})")
                        self.log(f"[Auto-Update] {data['ver']} downloaded silently. It will install automatically when you close the app.")
                        if manual:
                            if messagebox.askyesno(
                                "Update Ready",
                                f"Version {data['ver']} has been downloaded.\n"
                                f"Close and restart now to apply the update immediately?\n"
                                f"(Otherwise it will apply automatically when you exit.)",
                            ):
                                self.restart_for_update = True
                                self.on_close()
                                return
                    elif st == "up_to_date" and manual:
                        messagebox.showinfo("Check Update", f"You are running the latest version (v{APP_VERSION}).")
                    elif st == "dev_mode" and manual:
                        messagebox.showinfo("Check Update", f"New version {data['ver']} is available on GitHub (running from .py source).")
                    elif st == "no_asset" and manual:
                        messagebox.showinfo("Check Update", f"Release {data['ver']} found on GitHub, but no .exe asset is attached yet.")
                    elif st == "error" and manual:
                        messagebox.showwarning("Check Update", f"Could not check for updates:\n{data.get('err', '')}")
                elif kind == "rec_event":
                    m = data.get("type")
                    if m == "searchbox":
                        self.var_search_input_sel.set(data["selector"])
                        self.rec_stop.set()
                        self.log(f"Picked Search Box: {data['selector']}")
                    elif m == "click":
                        if data.get("is_select"):
                            val = simpledialog.askstring(
                                "Dropdown Detected (<select>)",
                                f"You clicked a dropdown: {data['selector']}\n\n"
                                f"Enter the text or value to select/inject (e.g. Show All, 100, 2000):",
                                initialvalue="2000",
                                parent=self,
                            )
                            if val and val.strip():
                                self.sequence.append({
                                    "type": "select_value",
                                    "selector": data["selector"],
                                    "value": val.strip(),
                                    "first_link_only": False,
                                })
                                self.refresh_sequence(select=len(self.sequence) - 1)
                                continue

                        first_only = messagebox.askyesno(
                            "Click Scope",
                            f"Recorded Click: {data['selector']}\n\nRun this click on the FIRST item only (e.g. Cookie banner)?\n(Click 'No' to run on ALL items)"
                        )
                        self.sequence.append({
                            "type": "click",
                            "selector": data["selector"],
                            "first_link_only": first_only,
                        })
                        self.refresh_sequence(select=len(self.sequence) - 1)
                    elif m == "extract":
                        extract_count = sum(1 for item in self.sequence if item["type"] == "extract")
                        col_name = f"Field_{extract_count + 1}"
                        multi_count = data.get("multi_count", 1)
                        use_multi = False
                        chosen_sel = data["selector"]
                        alt_sel = data.get("multi_selector", chosen_sel)

                        if multi_count > 1:
                            ans = messagebox.askyesno(
                                "Repeating Column/Items Detected",
                                f"Found {multi_count} matching items in this column/list!\n"
                                f"Sample: '{data.get('sample', '')}'\n\n"
                                f"Extract ALL {multi_count} items as separate rows (Multi-Row List)?"
                            )
                            if ans:
                                use_multi = True
                                chosen_sel, alt_sel = alt_sel, chosen_sel

                        extract_attr = "text"
                        if data.get("sample_href"):
                            want_both = messagebox.askyesno(
                                "Link Detected (href)",
                                f"This element contains a link:\n{data['sample_href']}\n\n"
                                f"Extract BOTH Text AND Link into 2 separate columns?\n"
                                f"(Click 'No' to choose Text only or Link only)"
                            )
                            if want_both:
                                extract_attr = "both"
                            elif messagebox.askyesno("Link Only", "Extract ONLY the Link URL (href)?"):
                                extract_attr = "href"

                        self.sequence.append({
                            "type": "extract",
                            "name": col_name,
                            "selector": chosen_sel,
                            "multi_selector": alt_sel,
                            "multi": use_multi,
                            "extract_attr": extract_attr,
                            "first_link_only": False,
                        })
                        self.refresh_sequence(select=len(self.sequence) - 1)
                elif kind == "rec_done":
                    self.rec_mode = None
                    self.btn_rec_click.config(text="\u25CF Record Click", state="normal")
                    self.btn_rec_extract.config(text="\u25CF Pick Extract Element", state="normal")
                    self.btn_pick_search.config(text="Pick Box", state="normal")
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
        if self.staged_update_path and os.path.exists(self.staged_update_path):
            schedule_silent_exe_replace(self.staged_update_path, restart_after=self.restart_for_update)
        self.destroy()

    def build_cfg(self):
        folder = self.var_folder.get().strip()
        mode = self.var_input_mode.get()
        if not folder:
            messagebox.showwarning("Warning", "Please specify save folder.")
            return None

        tasks = []
        if mode == "search":
            s_url = self.var_search_url.get().strip()
            s_box = self.var_search_input_sel.get().strip()
            kws = self.get_keywords()
            if not s_url or not s_box or not kws:
                messagebox.showwarning("Warning", "In Search Mode, please enter Search Page URL, Search Input Box selector, and at least 1 keyword.")
                return None
            if not s_url.startswith(("http://", "https://")):
                s_url = "https://" + s_url
            for idx, kw in enumerate(kws):
                tasks.append({"link": s_url, "keyword": kw, "is_first": idx == 0})
        else:
            links = self.get_links()
            if not links:
                messagebox.showwarning("Warning", "Please enter target URLs.")
                return None
            seen_domains = set()
            for l in links:
                dom = host_of(l)
                is_first = dom not in seen_domains
                seen_domains.add(dom)
                tasks.append({"link": l, "keyword": "", "is_first": is_first})

        os.makedirs(folder, exist_ok=True)
        return tasks, {
            "folder": os.path.abspath(folder),
            "input_mode": mode,
            "search_input_sel": self.var_search_input_sel.get().strip(),
            "search_btn_sel": self.var_search_btn_sel.get().strip(),
            "driver": self.var_driver.get().strip(),
            "chrome_exe": self.var_chrome_exe.get().strip(),
            "chrome_profile": self.var_chrome_profile.get().strip(),
            "use_real_chrome": self.var_use_real_chrome.get(),
            "debug_port": num(self.var_debug_port, 9222),
            "close_on_finish": self.var_close_on_finish.get(),
            "zoom_pct": num(self.var_zoom_pct, 100),
            "load_wait": num(self.var_load_wait, 5),
            "stop_loading": self.var_stop_loading.get(),
            "step_timeout": num(self.var_step_timeout, 10),
            "step_delay": num(self.var_step_delay, 1.5),
            "continue_missing": self.var_continue.get(),
            "sequence_sets": json.loads(json.dumps(self.sequence_sets)),
            "site_settings": json.loads(json.dumps(self.site_settings)),
            "new_browser": self.var_browser_mode.get() == "each",
            "headless": self.var_headless.get(),
            "incognito": self.var_incognito.get(),
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
        tasks, cfg = built
        self.save_settings()
        self.stop_event.clear()
        self.btn_start.config(state="disabled")
        self.btn_rec_click.config(state="disabled")
        self.btn_rec_extract.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.msg_queue.put(("progress", (0, len(tasks))))
        self.worker = threading.Thread(target=self.run_job, args=(tasks, cfg), daemon=True)
        self.worker.start()

    def test_first(self):
        if self.rec_mode or (self.worker and self.worker.is_alive()):
            return
        built = self.build_cfg()
        if not built:
            return
        tasks, cfg = built
        self.save_settings()
        threading.Thread(target=self.run_test, args=(tasks[0], cfg), daemon=True).start()

    def run_test(self, task, cfg):
        q = self.msg_queue
        link = task["link"]
        kw = task["keyword"]
        site_key, mod_name, seq = resolve_site_and_module(cfg["sequence_sets"], link)
        scfg = apply_site_cfg(cfg, link)
        q.put(("log", f"TEST [{site_key} :: {mod_name}] {f'(Keyword: {kw}) ' if kw else ''}on: {link}"))
        driver = None
        try:
            driver = self.new_driver(scfg, worker_idx=0)
            final_url, page_title, rows_data, status, note = self.execute_task(
                driver, link, kw, scfg, seq, is_first_in_domain=True, reload_page=True
            )
            q.put(("log", f"   Final URL: {final_url}"))
            q.put(("log", f"   Title: {page_title} | Extracted Rows: {len(rows_data)}"))
            for r_idx, fdict in enumerate(rows_data[:10], 1):
                q.put(("log", f"   Row {r_idx}: {json.dumps(fdict, ensure_ascii=False)}"))
        except Exception as e:
            q.put(("log", f"   Error: {e}"))
        finally:
            self.close_driver(driver, is_real_chrome=scfg.get("use_real_chrome"), force_close=scfg.get("close_on_finish"))

    def stop(self):
        self.stop_event.set()
        self.msg_queue.put(("log", "Stopping..."))

    def new_driver(self, scfg, worker_idx=0):
        options = webdriver.ChromeOptions()
        options.page_load_strategy = "none"
        incognito = bool(scfg.get("incognito"))

        if scfg.get("use_real_chrome"):
            port = int(scfg.get("debug_port", 9222)) + worker_idx
            ok, msg = launch_real_chrome(
                port=port,
                headless=scfg.get("headless", False),
                chrome_path=scfg.get("chrome_exe", ""),
                custom_profile=scfg.get("chrome_profile", ""),
                incognito=incognito,
            )
            self.msg_queue.put(("log", f"   {msg}"))
            if not ok:
                raise RuntimeError(msg)
            options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
            driver = webdriver.Chrome(service=make_service(scfg["driver"]), options=options)
            self.live_drivers.add(driver)
            return driver

        options.add_argument("--start-maximized")
        if incognito:
            options.add_argument("--incognito")
        if scfg.get("headless"):
            options.add_argument("--headless=new")
            options.add_argument("--window-size=1920,1080")
        if scfg.get("stealth"):
            apply_stealth_options(options)
        driver = webdriver.Chrome(service=make_service(scfg["driver"]), options=options)
        if scfg.get("stealth"):
            apply_stealth_driver(driver)
        self.live_drivers.add(driver)
        return driver

    def close_driver(self, driver, is_real_chrome=False, force_close=False):
        if driver:
            self.live_drivers.discard(driver)
            try:
                if not is_real_chrome or force_close:
                    driver.quit()
            except Exception:
                pass

    def execute_task(self, driver, link, keyword, scfg, sequence, is_first_in_domain=False, reload_page=True):
        if reload_page or not keyword:
            driver.get(link)
            time.sleep(scfg["load_wait"])
            if scfg["stop_loading"]:
                driver.execute_script("window.stop();")

        apply_zoom(driver, scfg.get("zoom_pct", 100))

        if keyword:
            by_s, val_s = parse_selector(scfg["search_input_sel"])
            try:
                s_els = WebDriverWait(driver, scfg["step_timeout"]).until(lambda d: d.find_elements(by_s, val_s) or False)
            except TimeoutException:
                s_els = []
            if not s_els:
                raise RuntimeError(f"Search input box not found: {scfg['search_input_sel']}")
            s_box = ([e for e in s_els if is_displayed(e)] or s_els)[0]
            click_element(driver, s_box)
            try:
                s_box.clear()
            except Exception:
                pass
            s_box.send_keys(Keys.CONTROL, "a")
            s_box.send_keys(Keys.BACKSPACE)
            s_box.send_keys(keyword)

            btn_sel = scfg.get("search_btn_sel", "").strip()
            if btn_sel:
                by_b, val_b = parse_selector(btn_sel)
                b_els = driver.find_elements(by_b, val_b)
                if b_els:
                    click_element(driver, ([e for e in b_els if is_displayed(e)] or b_els)[0])
                else:
                    s_box.send_keys(Keys.ENTER)
            else:
                s_box.send_keys(Keys.ENTER)

            time.sleep(scfg["load_wait"])
            if scfg["stop_loading"]:
                driver.execute_script("window.stop();")
            apply_zoom(driver, scfg.get("zoom_pct", 100))

        single_fields = {}
        multi_fields = {}

        for item in sequence:
            if item.get("first_link_only") and not is_first_in_domain:
                continue

            t = item["type"]
            if t == "wait":
                time.sleep(item["seconds"])
            elif t == "zoom":
                apply_zoom(driver, item["zoom"])
            elif t == "click":
                by, val = parse_selector(item["selector"])
                try:
                    els = WebDriverWait(driver, scfg["step_timeout"]).until(lambda d: d.find_elements(by, val) or False)
                except TimeoutException:
                    els = []
                if not els:
                    if scfg["continue_missing"]:
                        continue
                    raise RuntimeError(f"Element not found for click: {item['selector']}")
                visible = [e for e in els if is_displayed(e)] or els
                for el in visible[:1]:
                    try:
                        click_element(driver, el)
                    except Exception:
                        pass
                time.sleep(scfg["step_delay"])
            elif t == "select_value":
                by, val = parse_selector(item["selector"])
                try:
                    els = WebDriverWait(driver, scfg["step_timeout"]).until(lambda d: d.find_elements(by, val) or False)
                except TimeoutException:
                    els = []
                if not els:
                    if scfg["continue_missing"]:
                        continue
                    raise RuntimeError(f"Dropdown not found: {item['selector']}")
                target_el = ([e for e in els if is_displayed(e)] or els)[0]
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", target_el)
                driver.execute_script(SET_SELECT_VALUE_JS, target_el, item["value"])
                time.sleep(scfg["step_delay"])
            elif t == "extract":
                by, val = parse_selector(item["selector"])
                attr_mode = item.get("extract_attr", "text")
                col_name = item["name"]
                link_col_name = f"{col_name}_Link"

                try:
                    els = driver.find_elements(by, val)
                    pairs = [extract_element_pair(e) for e in els]
                except Exception:
                    pairs = []

                if item.get("multi"):
                    if attr_mode == "text":
                        multi_fields[col_name] = [p[0] for p in pairs if p[0]]
                    elif attr_mode == "href":
                        multi_fields[col_name] = [p[1] for p in pairs if p[1]]
                    elif attr_mode == "both":
                        valid_pairs = [p for p in pairs if p[0] or p[1]]
                        multi_fields[col_name] = [p[0] for p in valid_pairs]
                        multi_fields[link_col_name] = [p[1] for p in valid_pairs]
                else:
                    if attr_mode == "text":
                        single_fields[col_name] = " | ".join(p[0] for p in pairs if p[0])
                    elif attr_mode == "href":
                        single_fields[col_name] = " | ".join(p[1] for p in pairs if p[1])
                    elif attr_mode == "both":
                        single_fields[col_name] = " | ".join(p[0] for p in pairs if p[0])
                        single_fields[link_col_name] = " | ".join(p[1] for p in pairs if p[1])

        final_url = ""
        page_title = ""
        try:
            final_url = driver.current_url.strip()
            page_title = driver.title.strip()
        except Exception:
            pass

        max_rows = max((len(v) for v in multi_fields.values()), default=1)
        max_rows = max(1, max_rows)

        rows_output = []
        for idx in range(max_rows):
            row_dict = dict(single_fields)
            for fname, vlist in multi_fields.items():
                row_dict[fname] = vlist[idx] if idx < len(vlist) else ""
            rows_output.append(row_dict)

        return final_url, page_title, rows_output, "OK", ""

    def worker_loop(self, task_q, cfg, ctx, worker_idx=0):
        holder = {"d": None, "sig": None, "real": False, "last_url": None}
        try:
            while not self.stop_event.is_set():
                try:
                    i, task = task_q.get_nowait()
                except queue.Empty:
                    break

                link = task["link"]
                kw = task["keyword"]
                is_first_domain = task["is_first"]

                site_key, mod_name, seq = resolve_site_and_module(cfg["sequence_sets"], link)
                scfg = apply_site_cfg(cfg, link)
                is_real = bool(scfg.get("use_real_chrome"))
                driver_sig = (scfg.get("headless"), scfg.get("incognito"), scfg.get("stealth"), is_real)

                if holder["d"] is not None and holder["sig"] != driver_sig:
                    self.close_driver(holder["d"], is_real_chrome=holder["real"], force_close=not holder["real"])
                    holder["d"] = None
                    holder["last_url"] = None

                label = f"[KW: {kw}] {link}" if kw else link
                self.msg_queue.put(("log", f"[{i + 1}/{ctx['total']}] ({site_key} :: {mod_name}) {label}"))

                final_url, page_title, rows_data, status, note = link, "", [{}], "Error", ""
                for attempt in range(1, cfg["retries"] + 2):
                    if self.stop_event.is_set():
                        break
                    try:
                        if holder["d"] is None:
                            holder["d"] = self.new_driver(scfg, worker_idx=worker_idx)
                            holder["sig"] = driver_sig
                            holder["real"] = is_real
                            holder["last_url"] = None

                        need_reload = (not kw) or (holder["last_url"] != link) or (attempt > 1)
                        final_url, page_title, rows_data, status, note = self.execute_task(
                            holder["d"], link, kw, scfg, seq,
                            is_first_in_domain=is_first_domain,
                            reload_page=need_reload,
                        )
                        holder["last_url"] = link
                        break
                    except Exception as e:
                        note = str(e).splitlines()[0] if str(e) else type(e).__name__
                        self.msg_queue.put(("log", f"   Attempt {attempt} error: {note}"))
                        if holder["d"]:
                            self.close_driver(holder["d"], is_real_chrome=holder["real"], force_close=not holder["real"])
                            holder["d"] = None
                            holder["last_url"] = None
                    if attempt <= cfg["retries"] and not self.stop_event.is_set():
                        time.sleep(2)

                if scfg.get("new_browser") and holder["d"] and not holder["real"]:
                    self.close_driver(holder["d"], is_real_chrome=False, force_close=True)
                    holder["d"] = None
                    holder["last_url"] = None

                ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with ctx["lock"]:
                    for r_idx, fdict in enumerate(rows_data, 1):
                        rec = {
                            "site_profile": site_key if site_key != ALL_SITES else (host_of(link) or "General"),
                            "module_name": mod_name,
                            "keyword": kw,
                            "link": link,
                            "final_url": final_url,
                            "title": page_title,
                            "row_index": r_idx,
                            "status": status,
                            "notes": note,
                            "timestamp": ts,
                            "fields": fdict,
                        }
                        ctx["out"].write(json.dumps(rec, ensure_ascii=False) + "\n")
                    ctx["out"].flush()
                    ctx["done"] += 1
                    self.msg_queue.put(("progress", (ctx["done"], ctx["total"])))

                if scfg.get("url_delay", 0) > 0 and not self.stop_event.is_set():
                    time.sleep(scfg["url_delay"])
        finally:
            self.close_driver(
                holder["d"],
                is_real_chrome=holder["real"],
                force_close=cfg.get("close_on_finish", False) and not holder["real"],
            )

    def run_job(self, tasks, cfg):
        q = self.msg_queue
        total = len(tasks)
        out_path = os.path.join(cfg["folder"], "Scraped_Results.jsonl")

        done_keys = set()
        if cfg["resume"] and os.path.exists(out_path):
            with open(out_path, encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        rec = json.loads(line)
                        if rec.get("status") == "OK":
                            done_keys.add((rec.get("link", ""), rec.get("keyword", "")))
                    except Exception:
                        pass

        todo = []
        for i, t in enumerate(tasks):
            if (t["link"], t["keyword"]) in done_keys:
                continue
            todo.append((i, t))

        if not os.path.exists(out_path) or not cfg["resume"]:
            open(out_path, "w", encoding="utf-8").close()

        ctx = {"lock": threading.Lock(), "done": total - len(todo), "total": total}
        q.put(("progress", (ctx["done"], total)))

        task_q = queue.Queue()
        for item in todo:
            task_q.put(item)

        n_workers = max(1, min(cfg["workers"], len(todo))) if todo else 0
        with open(out_path, "a", encoding="utf-8") as out:
            ctx["out"] = out
            threads = [
                threading.Thread(target=self.worker_loop, args=(task_q, cfg, ctx, w_idx), daemon=True)
                for w_idx in range(n_workers)
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        q.put(("log", "Scraping finished! Click 'Export Excel (Multi-Sheet)' to view organized tabs."))
        q.put(("done", None))


if __name__ == "__main__":
    App().mainloop()

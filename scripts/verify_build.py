#!/usr/bin/env python3
"""Verify the statified build (stdlib only, read-only).

    python3 scripts/verify_build.py [--build site] [--raw PATH]

Hard checks (exit 1 on failure):
  * no ASP/SSI leftovers (`<%`, `%>`, `#include`, `$$...$$` macros, VBScript/FileSystemObject calls)
    in pages (.htm/.html/.shtml: the .shtml pages keep their URL but are plain HTML) and text files
  * no `<form` anywhere; no *.inc / *.asp file; no link to a .asp page
  * no hit counter (cnxweb.com), no ftp URL with credentials, no e-mail address
  * nothing matching the exclusion globs was published
  * every html page declares its charset (iso-8859-1 unless it really is UTF-8)
  * no NEW broken internal link compared with the original site
Reported (not failing): broken-link counts original vs build (exact and case-only), IPv4-like strings.

Link resolution: href/src/background/action/<frame src>; external schemes ignored;
query/fragment dropped; a directory resolves to index.html / index.htm / index.shtml.
Links are compared case-sensitively (bunny.net is): a case-only mismatch counts as broken.
The rendered ASP pages (`index2.asp`, `forum.asp`) are compared under their `.html` name.
"""
import argparse
import fnmatch
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote

ENC = "iso-8859-1"
REPO = Path(__file__).resolve().parent.parent
LINK_RE = re.compile(r"""(?ix)\b(?:href|src|background|action)\s*=\s*(?:(["'])(.*?)\1|([^\s"'>]+))""")
SKIP_SCHEME = re.compile(r"(?i)^(?:[a-z][a-z0-9+.-]*:|//|#|\$\$|<%)")
LEFTOVERS = [
    ("asp open tag", re.compile(r"<%")),
    ("asp close tag", re.compile(r"%>")),
    ("ssi include", re.compile(r"<!--\s*#(?:include|exec|echo|config)", re.I)),
    ("host macro $$..$$", re.compile(r"\$\$[A-Z]+(?::[^$]*)?\$\$")),
    ("vbscript api", re.compile(r"(?i)\b(?:FileSystemObject|OpenTextFile|CreateTextFile|Request\.(?:Form|QueryString|ServerVariables)|Server\.MapPath|Response\.(?:Write|Redirect))\b")),
    ("form tag", re.compile(r"(?i)<form\b")),
    ("'logins' (credentials file)", re.compile(r"(?i)logins")),
    ("e-mail address", re.compile(r"[A-Za-z0-9._+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")),
    ("mailto:", re.compile(r"(?i)mailto:")),
    ("hit counter (cnxweb.com)", re.compile(r"(?i)cnxweb")),
    ("ftp URL with credentials", re.compile(r"(?i)ftp://[^\s:/@\"'<>]+:[^\s/@\"'<>]+@")),
]
PAGE_EXT = (".htm", ".html", ".shtml")
TEXT_EXT = PAGE_EXT + (".txt", ".c")
ASP_RENDERED = {"index2.asp": "index2.html", "forum.asp": "forum.html"}
KEY_PAGES = ("index.htm", "index2.html", "forum.html", "LTP4FINRES.SHTML", "ORGWORDEND.SHTML",
             "bilan.shtml", "fastresults.html", "fastcode.html")
IPV4 = re.compile(r"(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\d.])")


# The removal-request footer (statify.py) carries the only mailto: of the site: leave it out of every scan.
REMOVAL_NOTE_RE = re.compile(r'(?s)<div id="removal-note".*?</div>')


def rd(p):
    return REMOVAL_NOTE_RE.sub("", Path(p).read_bytes().decode(ENC))


def all_files(root):
    out = []
    for r, ds, fs in os.walk(root):
        ds.sort()
        for f in fs:
            out.append(Path(r, f).relative_to(root).as_posix())
    return sorted(out)


def load_globs(path):
    return [l.strip() for l in rd(path).splitlines() if l.strip() and not l.startswith("#")] if path.is_file() else []


def excluded(rel, globs):
    base = rel.rsplit("/", 1)[-1]
    for g in globs:
        g = g.lstrip("/")
        if g.endswith("/"):
            d = g.rstrip("/")
            if rel == d or rel.startswith(d + "/"):
                return True
        elif "/" not in g:
            if fnmatch.fnmatchcase(base, g):
                return True
        elif fnmatch.fnmatchcase(rel, g) or (g.startswith("**/") and fnmatch.fnmatchcase(rel, g[3:])):
            return True
    return False


def extract_links(text):
    for m in LINK_RE.finditer(text):
        v = m.group(2) if m.group(2) is not None else m.group(3)
        if v is not None:
            yield v.strip()


def norm(p):
    d, _, b = p.rpartition("/")
    b = ASP_RENDERED.get(b.lower(), b)
    return d + "/" + b if d else b


def check_links(root, files_set, lower_map):
    """Returns {(source rel, resolved target): 'missing' | 'case'} for internal links that do not resolve.
    The rendered ASP pages are normalised to their `.html` name so original and build can be compared."""
    bad = {}
    for rel in files_set:
        low = rel.lower()
        if not low.endswith(PAGE_EXT + (".asp",)):
            continue
        text = rd(root / rel)
        for raw in extract_links(text):
            if not raw or SKIP_SCHEME.match(raw) or "<%" in raw or re.search(r"[()\\;+]", raw):
                continue
            u = raw.split("#", 1)[0]
            path, _, query = u.partition("?")
            if path == "":
                continue
            path = unquote(path)
            if path.startswith("/"):
                target = os.path.normpath(path.lstrip("/"))
            else:
                target = os.path.normpath(os.path.join(os.path.dirname(rel), path))
            if target.startswith(".."):
                bad[(norm(rel), norm(target))] = "missing"
                continue
            target = target.replace(os.sep, "/")
            if target == ".":
                target = ""
            cands = [target]
            if target == "" or path.endswith("/") or ("." not in target.rsplit("/", 1)[-1]):
                base = target.rstrip("/")
                pre = base + "/" if base else ""
                cands = [pre + n for n in ("index.html", "index.htm", "index.shtml", "default.htm")]
                if not path.endswith("/") and target in files_set:
                    cands.append(target)
            if any(c in files_set for c in cands):
                continue
            kind = "case" if any(c.lower() in lower_map for c in cands) else "missing"
            bad[(norm(rel), norm(target))] = kind
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", "--site", dest="site", default=os.environ.get("LTP4PP_RAW") or str(REPO / "private" / "site-raw"),
                    help="raw original tree, for the link comparison only (optional; skipped when absent, e.g. in CI)")
    ap.add_argument("--build", default=str(REPO / "site"), help="published tree to check (default: <repo>/site)")
    ap.add_argument("--exclude-file", action="append", default=None)
    ap.add_argument("--show", type=int, default=15, help="how many offending items to print per check")
    a = ap.parse_args(argv)
    site, build = Path(a.site), Path(a.build)
    if not build.is_dir():
        print("build folder missing: %s (run scripts/statify.py first)" % build)
        return 2
    failures = 0

    def fail(title, items):
        nonlocal failures
        failures += 1
        print("FAIL %s: %d" % (title, len(items)))
        for it in items[:a.show]:
            print("   ", it)
        if len(items) > a.show:
            print("    ... +%d more" % (len(items) - a.show))

    bfiles = all_files(build)
    bset = set(bfiles)
    missing = [f for f in KEY_PAGES if f not in bset]
    if missing or len(bfiles) < 100:
        fail("build looks incomplete (missing key pages / too few files)", missing or [str(len(bfiles))])
    print("build: %d files" % len(bfiles))

    # 1. leftovers (text files only: html + txt)
    hits = defaultdict(list)
    for rel in bfiles:
        if rel.lower().endswith(TEXT_EXT):
            t = rd(build / rel)
            for label, rx in LEFTOVERS:
                if label == "form tag" and not rel.lower().endswith(PAGE_EXT):
                    continue
                if rx.search(t):
                    hits[label].append(rel)
    for label, _ in LEFTOVERS:
        if hits[label]:
            fail("leftover '%s' in" % label, hits[label])
    asp = []
    for rel in bfiles:
        if rel.lower().endswith(PAGE_EXT):
            for raw in extract_links(rd(build / rel)):
                if not SKIP_SCHEME.match(raw) and raw.split("#")[0].split("?")[0].lower().endswith(".asp"):
                    asp.append("%s -> %s" % (rel, raw))
    if asp:
        fail("internal links still pointing to .asp", asp)
    # 2. forbidden file types
    bad = [r for r in bfiles if r.lower().endswith((".inc", ".asp", ".aspx", ".cgi", ".dll", ".exe", ".bat"))]
    if bad:
        fail("server-side/executable files present", bad)
    # 3. exclusion globs honoured
    globs = []
    for f in (a.exclude_file or [REPO / "scripts" / "exclude-globs.txt"]):
        globs += load_globs(Path(f))
    pub = [r for r in bfiles if excluded(r, globs)]
    if pub:
        fail("published files matching exclusion globs", pub)
    # 4. charset declaration
    nocs = []
    for rel in bfiles:
        if rel.lower().endswith(PAGE_EXT) and not re.search(rb"(?i)charset\s*=", (build / rel).read_bytes()):
            nocs.append(rel)
    if nocs:
        fail("html without charset declaration", nocs)

    # 5. links: build alone, then compared with the raw original when it is available
    b_bad = check_links(build, bset, {f.lower() for f in bset})
    b_missing = {k for k, v in b_bad.items() if v == "missing"}
    b_case = {k for k, v in b_bad.items() if v == "case"}
    print("broken internal links  build:    %d missing + %d case-only (%d pages)"
          % (len(b_missing), len(b_case), len({k[0] for k in b_bad})))
    if site.is_dir():
        sfiles = all_files(site)
        sset = set(sfiles)
        s_bad = check_links(site, sset, {f.lower() for f in sset})
        print("broken internal links  original: %d missing + %d case-only (%d pages)"
              % (sum(v == "missing" for v in s_bad.values()), sum(v == "case" for v in s_bad.values()),
                 len({k[0] for k in s_bad})))
        new = sorted(k for k in b_bad if k not in s_bad)
        if new:
            fail("NEW broken links (not broken in original)", ["%s -> %s" % k for k in new])
        else:
            print("ok: no new broken link vs original")
    else:
        print("notice: raw tree not found (%s): comparison with the original skipped (CI mode)" % site)
    by_target = defaultdict(int)
    for (_r, raw) in b_missing:
        by_target[raw] += 1
    if b_missing:
        top = sorted(by_target.items(), key=lambda t: -t[1])[:a.show]
        print("most frequent remaining broken targets:", ", ".join("%s (x%d)" % t for t in top))
    if b_case:
        print("case-only mismatches (work on Windows, 404 on bunny): e.g.",
              ", ".join("%s -> %s" % k for k in sorted(b_case)[:5]))

    # 6. IPv4: allowed only as the host of an http(s) URL (1990s servers of groups/links, no visitor data)
    ips, urlips = [], 0
    for rel in bfiles:
        if rel.lower().endswith(TEXT_EXT):
            t = rd(build / rel)
            for m in IPV4.finditer(t):
                if t[max(0, m.start() - 8):m.start()].lower().endswith("://"):
                    urlips += 1
                else:
                    ips.append("%s: %s" % (rel, t[max(0, m.start() - 25):m.end() + 10].replace("\n", " ")))
    if ips:
        fail("IPv4 outside a URL host", ips)
    print("ok: %d IPv4 only as URL hosts (allow-listed), 0 elsewhere" % urlips if not ips else "")

    print("RESULT:", "FAIL" if failures else "OK")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Statify the LTP4 (Lucky & Tigrou Party 4, August 2000) post-party site into plain static HTML.

    python3 scripts/statify.py [--raw PATH] [--forum PATH] [--out site] [options]

Reads ONLY from the raw tree (never writes to it). The pages keep their original
URLs where they were static (`index.htm`, `LTP4FINRES.SHTML`, `bilan.shtml`, ...):
the SSI include of `menu.inc` is inlined and the extension is kept, so that the
old links keep working. The two classic-ASP pages are rendered once into `.html`:
`index2.asp` (results hub) -> `index2.html`, `forum.asp` (attenders' words, read
from the flat files of `ltpdata/forum/`) -> `forum.html`. Other files are copied
as-is, except what scripts/exclude-globs.txt lists.

Python 3.9+, standard library only. Files are read/written as iso-8859-1
(lossless round trip), and every HTML page declares that charset.
"""
import argparse
import fnmatch
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ENC = "iso-8859-1"

# ---- removal-request footer: added to every page that lists or describes people
REMOVAL_MARK = 'id="removal-note"'
REMOVAL_NOTE = (
    '<div id="removal-note" style="clear:both;margin:28px auto 8px;padding:6px 8px 0;width:760px;max-width:96%;box-sizing:border-box;'
    'border-top:1px solid #808080;text-align:center;font:10px/14px Verdana,Arial,Helvetica,sans-serif;'
    'color:#808080;background:transparent">To be removed from this page, '
    '<a href="mailto:chandra_oj@pm.me" style="color:#808080;text-decoration:underline">contact me</a>.</div>'
)
_BODY_END = re.compile(r"(?is)</body\s*>(?!.*</body\s*>)")


def add_removal_note(text):
    if REMOVAL_MARK in text:
        return text
    m = _BODY_END.search(text)
    if m:
        return text[: m.start()] + REMOVAL_NOTE + "\n" + text[m.start():]
    return text + "\n" + REMOVAL_NOTE + "\n"

# Pages that carry a family name, an address or an e-mail local part in clear (directly or in a
# zip they link): fast compo results (fast03.zip, fast.zip) and the results hub (fast.zip).
# The tribute home page and the forum only hold nicks and first names: no footer.
PEOPLE_PAGES = {"fastresults.html", "index2.html"}

# Every page is limited to 1024 px and centred (the footer, added first, is inside the wrapper).
WIDTH_OPEN = '<div id="site-width" style="max-width:1024px;margin:0 auto">'
_BODY_START = re.compile(r"(?is)<body\b[^>]*>")


def limit_width(text):
    if 'id="site-width"' in text:
        return text
    m = _BODY_START.search(text)
    e = _BODY_END.search(text)
    if not m or not e:
        raise RuntimeError("no <body>...</body> to wrap")
    return text[: m.end()] + "\n" + WIDTH_OPEN + text[m.end(): e.start()] + "</div>\n" + text[e.start():]


def is_people_page(rel):
    return rel in PEOPLE_PAGES

REPO = Path(__file__).resolve().parent.parent
# The raw originals live in private/ (git-ignored: they hold ASP sources and the forum data).
RAW_DEFAULT = Path(os.environ.get("LTP4PP_RAW") or (REPO / "private" / "site-raw"))
FORUM_DEFAULT = Path(os.environ.get("LTP4PP_FORUM") or (REPO / "private" / "ltpdata" / "forum"))
MASK = "????"   # placeholder for every redacted value
META_CHARSET = '<meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">'
HOSTS_SELF = r"(?:ltp\.ojuice\.net)"
# ASP pages rendered to static HTML: source -> published name.
ASP_PAGES = {"index2.asp": "index2.html", "forum.asp": "forum.html"}
# Where the link to the site's own dead host (http://ltp.ojuice.net, "LTP party" on the
# home page) now points: the 2000 results hub, otherwise unreachable from the 2001 home page.
SELF_HOME = "/index2.html"


class Ctx:
    """Run-wide options and counters."""

    def __init__(self, site, forum, out, opts):
        self.site = site
        self.forum = forum
        self.out = out
        self.opts = opts
        self.globs = []
        self.excluded = []
        self.rendered = []      # (old rel, new rel)
        self.redirects = []     # (old url, new url)
        self.copied = 0
        self.warnings = []
        self.counters = 0
        self.ftp_creds = 0
        self.forum_posts = 0

    def warn(self, msg):
        self.warnings.append(msg)


# --------------------------------------------------------------------------- io
def read_text(p):
    return Path(p).read_bytes().decode(ENC)


def write_text(p, s):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(s.encode(ENC, errors="xmlcharrefreplace"))


# ------------------------------------------------------------------- exclusions
def load_globs(path):
    out = []
    if path.is_file():
        for line in read_text(path).splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(line)
    return out


def is_excluded(rel, globs):
    """gitignore-like: no '/' -> matches a basename anywhere; trailing '/' -> a directory;
    otherwise fnmatch on the whole path relative to site/ ('*' crosses '/')."""
    base = rel.rsplit("/", 1)[-1]
    for g in globs:
        g = g.lstrip("/")
        if g.endswith("/"):
            d = g.rstrip("/")
            if rel == d or rel.startswith(d + "/") or ("/" not in d and ("/" + d + "/") in ("/" + rel)):
                return True
        elif "/" not in g:
            if fnmatch.fnmatchcase(base, g):
                return True
        elif fnmatch.fnmatchcase(rel, g) or (g.startswith("**/") and fnmatch.fnmatchcase(rel, g[3:])):
            return True
    return False


# --------------------------------------------------------------- VBScript bits
def html_encode(s):
    """Server.HTMLEncode."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def format_width(s, w):
    """forum.asp FormatWidth(): hard-wrap at w characters, cutting after the last space, comma or
    full stop of the chunk (the original counts across existing line breaks too)."""
    out = []
    while len(s) > w:
        tmp = s[:w]
        i = max(tmp.rfind(" "), tmp.rfind(","), tmp.rfind(".")) + 1   # InStrRev, 1-based, 0 if none
        if i > 0:
            out.append(tmp[:i] + "\r\n")
            s = s[i:]
        else:
            out.append(tmp + "\r\n")
            s = s[w:]
    out.append(s)
    return "".join(out)


# ------------------------------------------------------------------- templates
def archived_inline(what="this form"):
    return ('<P><FONT size="1" face="Verdana, Arial, Helvetica, sans-serif" color="#808080">'
            '[ archived: %s is no longer available &#8211; this site is a read-only snapshot ]</FONT></P>' % what)


# ---------------------------------------------------------------- page renderers
def render_forum(ctx, text):
    """forum.asp: the POST handler and the admin answer/delete pages are dropped; the listing is
    rendered from ltpdata/forum/ (newest first, as the ASP did) and the form becomes a notice."""
    text = text.replace("\r\n", "\n")
    s = text.index("<html>\n\n<head>")            # the visitor page (after the VBScript header)
    page = text[s:]
    a = page.index("<%\n\tSET f = fs.GetFolder")
    b = page.index("NEXT %>", a) + len("NEXT %>")
    posts = sorted(p.name for p in ctx.forum.glob("*_1.txt")) if ctx.forum.is_dir() else []
    if not posts:
        ctx.warn("forum: no message found in %s (forum.html rendered empty)" % ctx.forum)
    out = []
    for name in reversed(posts):
        raw = read_text(ctx.forum / name).replace("\r\n", "\n").replace("\r", "\n")
        pseudo, _, texte = raw.partition("\n")
        texte = texte.replace("\n", "\r\n")
        ans = ctx.forum / (name[:15] + "2.txt")
        body = html_encode(format_width(texte.replace("<BR>", "\r\n"), 60)).replace("\r\n", "<BR>")
        rows = ['<table cellspacing=0 cellpadding=5 border=1 width=501 bordercolor="#000000">\n'
                '<tr bgcolor="#635A4A"> \n<td valign="top" height=15><font face="Verdana, Arial, Helvetica, sans-serif" size=2> \n'
                '%s/%s/%s - %s\n</font></td>\n</tr>\n'
                '<tr>\n<td><font face="Verdana, Arial, Helvetica, sans-serif" size=2> \n%s\n</font></td>\n</tr>\n'
                % (name[6:8], name[4:6], name[:4], html_encode(pseudo), body)]
        if ans.is_file():
            answer = read_text(ans).replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<BR>")
            rows.append('<tr bgcolor="#857C6C"> \n<td valign="top" height=15><font face="Verdana, Arial, Helvetica, sans-serif" size=2> \n'
                        'Answer of the organizing team </font></td>\n</tr>\n'
                        '<tr> \n<td><font face="Verdana, Arial, Helvetica, sans-serif" size=2> \n%s\n</font></td>\n</tr>\n'
                        % answer)
        rows.append("</table>\n<BR><BR>\n")
        out.append("".join(rows))
        ctx.forum_posts += 1
    page = page[:a] + "".join(out) + page[b:]
    page = page.replace("<H3><%=ErrMsg%></H3>", "")
    # the "LTP4 - The AFTER" posting box: keep its title, replace the form by the notice
    page = re.sub(r"<FORM\b.*?</FORM>", archived_inline("posting a message"), page, count=1, flags=re.S | re.I)
    return page


def render_asp(ctx, rel, text):
    if rel == "forum.asp":
        return render_forum(ctx, text)
    if rel == "index2.asp":
        return text   # static apart from the SSI include and the counter (generic pass)
    raise RuntimeError("%s: ASP page without a renderer" % rel)


# ------------------------------------------------------------ generic html pass
INCLUDE_RE = re.compile(r"""<!--\s*#include\s+file\s*=\s*"([^"]+)"\s*-->""", re.I)
FORM_RE = re.compile(r"<form\b.*?</form\s*>", re.I | re.S)
ATTR_RE = re.compile(r"""(?ix)\b(href|src|background|action)\s*=\s*(?:(["'])(.*?)\2|([^\s"'>]+))""")
# cnxweb.com hit counter: a document.write() script, its <noscript> twin and a plain <img>.
COUNTER_SCRIPT_RE = re.compile(r"<script\b[^>]*>(?:(?!</script>).)*cnxweb\.com(?:(?!</script>).)*</script\s*>\s*", re.I | re.S)
COUNTER_NOSCRIPT_RE = re.compile(r"<noscript>\s*<img\b[^>]*cnxweb\.com[^>]*>\s*</noscript>\s*", re.I)
COUNTER_IMG_RE = re.compile(r"<p>\s*<img\b[^>]*cnxweb\.com[^>]*>\s*</p>\s*|<img\b[^>]*cnxweb\.com[^>]*>", re.I)
# menu.inc rollover preloader: never called, and preloads six *-over.gif images that do not exist.
PRELOAD_RE = re.compile(r"<SCRIPT LANGUAGE=\"JavaScript\">\s*<!--\s*function newImage.*?</SCRIPT>\s*", re.S)
FTP_CREDS_RE = re.compile(r"(?i)\b(ftp://)[^\s:/@\"'<>]+:[^\s/@\"'<>]+@")


def inline_includes(ctx, text, rel):
    def inc(m):
        p = ctx.site / os.path.dirname(rel) / m.group(1)
        if not p.is_file():
            ctx.warn("%s: include %s not found" % (rel, m.group(1)))
            return ""
        return read_text(p).rstrip("\r\n")
    return INCLUDE_RE.sub(inc, text)


def drop_counters(ctx, text):
    n = 0
    for rx in (COUNTER_SCRIPT_RE, COUNTER_NOSCRIPT_RE, COUNTER_IMG_RE):
        text, k = rx.subn("", text)
        n += k
    ctx.counters += n
    return text


def rewrite_url(u, ctx):
    m = re.match(r"(?i)^https?://%s(/.*)?$" % HOSTS_SELF, u)
    if m:
        own = (m.group(1) or "/").lstrip("/")
        return SELF_HOME if own == "" else "/" + own
    if re.match(r"(?i)^[a-z][a-z0-9+.-]*:|^//", u):
        return u                        # external / mailto: / javascript:
    u2, sep, frag = u.partition("#")
    path, qsep, query = u2.partition("?")
    base = path.rsplit("/", 1)[-1]
    if base.lower() in ASP_PAGES:
        path = path[:len(path) - len(base)] + ASP_PAGES[base.lower()]
        qsep = query = ""               # ?f= / ?d= were admin actions
    return path + qsep + query + (sep + frag if sep else "")


MAILTO_A_RE = re.compile(r"<a\b[^>]*href\s*=\s*[\"']?mailto:[^>]*>(.*?)</a\s*>", re.I | re.S)
EMAIL_RE = re.compile(r"([A-Za-z0-9._+-]+)@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)")


def redact_emails(text):
    """mailto: links become plain text; `local@domain` becomes `local@????` (layout kept, domain masked)."""
    text = MAILTO_A_RE.sub(lambda m: m.group(1), text)
    text = re.sub(r"(?i)mailto:", "", text)
    return EMAIL_RE.sub(lambda m: m.group(1) + "@" + MASK, text)


def strip_ftp_creds(ctx, text):
    text, n = FTP_CREDS_RE.subn(r"\1", text)
    ctx.ftp_creds += n
    return text


FACE_VERDANA_RE = re.compile(r"""(?i)(\bface\s*=\s*)(["']?)(verdana\b[^"'>]*)(\2)""")
FONT_FALLBACK = ", DejaVu Sans, Geneva, sans-serif"


def add_font_fallback(text):
    """face="verdana" alone falls back to a serif font where Verdana is missing: append
    sans-serif fallbacks to the existing attribute (no CSS, same layout)."""
    def fn(m):
        value = m.group(3)
        if "sans-serif" in value.lower():
            return m.group(0)
        return m.group(1) + m.group(2) + value.rstrip() + FONT_FALLBACK + m.group(4)
    return FACE_VERDANA_RE.sub(fn, text)


# Notes added to the archive (not in the original), each inserted right after an anchor text
# of the raw page and marked as an addition. The build fails if the anchor is not found.
ADDITIONS = {
    "bilan.shtml": (
        "year for the LTP5.</FONT></p>",
        '\r\n\t\t\t\t\t\t\t<p align="center"><FONT face="Verdana, Arial, Helvetica, sans-serif" size="2" color="#999999">'
        "<I>P.S. (added in 2026): there never was an LTP5. When the bank accounts of Orange Juice "
        "were closed, all the money left was given to help organise other French demoparties.</I>"
        "</FONT></p>",
    ),
}


# Exact replacements (anchor must be found exactly once), applied after the other conversions.
TEXT_FIXES = {
    "index.htm": [
        # dead hosts of Orange Juice: their archives (README "To Do")
        ('href="http://www.ojuice.net"', 'href="https://orangejuicev3.sauthier.family"'),
        ('href="http://www.ojuice.net/tshirts.htm"', 'href="https://orangejuicev3.sauthier.family/tshirts.htm"'),
        ('href="http://nectarine.ojuice.net"', 'href="https://nectarine.sauthier.family"'),
    ],
    "index2.asp": [
        # personal dynamic-DNS host: not published
        ("or ftp://quad.no-ip.com/pub/LTP4/ or ftp://ftp.chscene.ch/", "or ftp://ftp.chscene.ch/"),
    ],
    # check.zip never existed (404 since 2000): the checker source is shipped as check11.c
    "fastcode.html": [('href="./check.zip"', 'href="check11.c"')],
}


def fix_texts(text, rel):
    for old, new in TEXT_FIXES.get(rel, []):
        if text.count(old) != 1:
            raise RuntimeError("%s: text fix anchor not found exactly once: %r" % (rel, old))
        text = text.replace(old, new)
    return text


def add_notes(ctx, text, rel):
    if rel not in ADDITIONS:
        return text
    anchor, note = ADDITIONS[rel]
    if text.count(anchor) != 1:
        raise RuntimeError("%s: anchor of the added note not found exactly once: %r" % (rel, anchor))
    return text.replace(anchor, anchor + note)


def convert_html(ctx, text, rel):
    text = add_notes(ctx, text, rel)
    text = fix_texts(text, rel)
    text = inline_includes(ctx, text, rel)
    text = PRELOAD_RE.sub("", text)
    text = drop_counters(ctx, text)
    text = FORM_RE.sub(lambda m: archived_inline(), text)
    text = strip_ftp_creds(ctx, text)
    if not ctx.opts.keep_emails:
        text = redact_emails(text)

    def attr(m):
        val = m.group(3) if m.group(3) is not None else m.group(4)
        q = m.group(2) or ""
        return "%s=%s%s%s" % (m.group(1), q, rewrite_url(val, ctx), q)
    text = ATTR_RE.sub(attr, text)
    return add_font_fallback(text)


def declare_charset(text):
    if re.search(r"(?i)charset\s*=", text):
        return text
    m = re.search(r"(?i)<head[^>]*>", text) or re.search(r"(?i)<html[^>]*>", text)
    if m:
        return text[:m.end()] + "\n" + META_CHARSET + text[m.end():]
    return META_CHARSET + "\n" + text


# ------------------------------------------------------------------------- main
PAGE_EXT = (".htm", ".html", ".shtml")
TEXT_EXT = (".txt", ".c")


def run(ctx):
    site, out = ctx.site, ctx.out
    outputs = {}   # rel -> text
    for root, dirs, files in os.walk(site):
        dirs.sort()
        for fn in sorted(files):
            full = Path(root) / fn
            rel = full.relative_to(site).as_posix()
            low = fn.lower()
            if rel.lower() in ASP_PAGES:
                new = ASP_PAGES[rel.lower()]
                outputs[new] = declare_charset(convert_html(ctx, render_asp(ctx, rel, read_text(full)), rel))
                ctx.rendered.append((rel, new))
                ctx.redirects.append(("/" + rel, "/" + new))
                continue
            if is_excluded(rel, ctx.globs):
                ctx.excluded.append(rel)
                continue
            if low.endswith(PAGE_EXT):
                outputs[rel] = declare_charset(convert_html(ctx, read_text(full), rel))
                continue
            dst = out / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            if low.endswith(TEXT_EXT) and not ctx.opts.keep_emails:
                write_text(dst, strip_ftp_creds(ctx, redact_emails(read_text(full))))
            else:
                shutil.copy2(full, dst)
            ctx.copied += 1

    for new_rel, text in outputs.items():
        write_text(out / new_rel, limit_width(add_removal_note(text) if is_people_page(new_rel) else text))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--site", "--raw", dest="site", default=str(RAW_DEFAULT),
                    help="raw original tree (default: $LTP4PP_RAW or private/site-raw)")
    ap.add_argument("--forum", default=str(FORUM_DEFAULT),
                    help="flat files of forum.asp (default: $LTP4PP_FORUM or private/ltpdata/forum)")
    ap.add_argument("--out", default=str(REPO / "site"), help="published tree: committed and deployed (default: <repo>/site)")
    ap.add_argument("--no-clean", action="store_true", help="keep existing files in the output folder (default: it is emptied first)")
    ap.add_argument("--exclude-file", action="append", default=None,
                    help="exclusion globs file (default: scripts/exclude-globs.txt)")
    ap.add_argument("--meta-dir", default=str(REPO / "build-meta"), help="where redirects.tsv and excluded.txt are written")
    ap.add_argument("--keep-emails", action="store_true",
                    help="do NOT redact e-mail addresses (default: mailto: links removed, '@domain' masked in html/txt/c)")
    opts = ap.parse_args(argv)

    site, out, forum = Path(opts.site).resolve(), Path(opts.out).resolve(), Path(opts.forum).resolve()
    if not site.is_dir():
        ap.error("site folder not found: %s" % site)
    if out == site or site in out.parents or out in site.parents:
        ap.error("--out must be a separate folder, outside the source tree")
    ctx = Ctx(site, forum, out, opts)
    for f in opts.exclude_file or [REPO / "scripts" / "exclude-globs.txt"]:
        g = load_globs(Path(f))
        if g:
            print("exclusions: %d globs from %s" % (len(g), f))
        ctx.globs += g
    if out == REPO or out in REPO.parents or (out / ".git").exists() or out in (Path.home(), Path("/")):
        ap.error("refusing to empty %s (not a dedicated output folder)" % out)
    if not opts.no_clean and out.exists():
        for _ in range(3):  # Finder may drop a .DS_Store while we delete
            shutil.rmtree(out, ignore_errors=True)
            if not out.exists():
                break
    out.mkdir(parents=True, exist_ok=True)

    run(ctx)

    meta = Path(opts.meta_dir)
    meta.mkdir(parents=True, exist_ok=True)
    lines = ["%s\t%s" % r for r in ctx.redirects]
    (meta / "redirects.tsv").write_text("\n".join(lines) + "\n", encoding="ascii", errors="replace")
    (meta / "excluded.txt").write_text("\n".join(ctx.excluded) + "\n", encoding="utf-8")

    print("rendered %d ASP pages (forum: %d messages); copied %d files; excluded %d; "
          "counters removed: %d; ftp credentials stripped: %d"
          % (len(ctx.rendered), ctx.forum_posts, ctx.copied, len(ctx.excluded), ctx.counters, ctx.ftp_creds))
    for w in ctx.warnings:
        print("WARNING:", w, file=sys.stderr)
    # Crawlers and frames: sitemap.xml, robots.txt and the frame-restore script tag (scripts/seo.py).
    subprocess.run([sys.executable, "-I", str(REPO / "scripts" / "seo.py"), "--site", str(out)], check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Local preview of site/ (python3 scripts/preview.py [port]).

Like `python3 -m http.server`, but serves the pages as bunny.net does with the edge
rules of infra/main.tf: .htm/.html/.shtml (any case, e.g. LTP4FINRES.SHTML) and
.txt/.c as ISO-8859-1 text, so they display instead of being downloaded.
"""
import functools
import http.server
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".htm": "text/html; charset=iso-8859-1",
        ".html": "text/html; charset=iso-8859-1",
        ".shtml": "text/html; charset=iso-8859-1",
        ".txt": "text/plain; charset=iso-8859-1",
        ".c": "text/plain; charset=iso-8859-1",
    }

    def guess_type(self, path):
        return self.extensions_map.get(Path(str(path)).suffix.lower()) or super().guess_type(path)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Handler, directory=str(SITE))).serve_forever()

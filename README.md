# LTP4-postparty

**Lucky & Tigrou Party 4, after the party.** LTP was a French demoparty series; LTP4 took place
on 25-27 August 2000. This is its website as it stood after the party: the 2001 home page
("L.T.P. 5 delayed" and the tribute to LTP memories) and the September 2000 pages with the final
results, the organizers' words, the attenders' words, the financial balance and Skal's fast code
compo. The pre-party (registration) version of the site is a separate archive, `LTP4`.

Archive of an old dynamic website (classic ASP and SSI pages, flat `.txt` files), published as a
**100 % static, read-only site** on bunny.net at the hostname of [`site.json`](site.json).
Kept online for history, no longer developed. Visitors can never write anything: the pages are
the cleaned, redacted static pages committed in `site/`, the CDN only serves files, and every
method except GET/HEAD/OPTIONS is refused at the edge.

## Search engines

`scripts/seo.py` writes `robots.txt` (allow everything, with the `Sitemap:` line) and `sitemap.xml` (indexable pages only) into `site/`; `statify.py` runs it at the end of the build (alone: `python3 -I scripts/seo.py`).

## Layout

| Path | Content |
| --- | --- |
| `site/` | The cleaned, redacted static site, exactly as served |
| `private/` | Raw originals (git-ignored, never published): `site-raw/` (the `http/` folder) and `ltpdata/` (forum flat files) |
| `hosting/404.html` | Custom 404 page, deployed next to `site/` |
| `site.json` | The only site-specific settings: repository, storage zone, pull zone, hostname, 404 page |
| `infra/` | OpenTofu: storage zone, pull zone, hostname, hardening edge rules (state encrypted, committed) |
| `infra/secrets.env` | Proton Pass **references** to the secrets (vault `OldSites`), no secret values |
| `scripts/statify.py` | Raw originals (`private/`) → cleaned `site/` (run locally) |
| `scripts/verify_build.py` | Checks `site/`: no ASP/SSI, forms, counters, e-mails, credentials, new broken links |
| `scripts/check_excludes.py` | Fails if `site/` holds a path of `scripts/exclude-globs.txt` |
| `scripts/preview.py` | Local preview with the charsets of the edge rules (`.SHTML` shown as HTML) |
| `scripts/deploy.py` | Sync `site/` to the storage zone, purge the CDN |
| `scripts/smoke_test.py` | Check the public site: pages as in `site/`, POST refused, security headers, charset, 404 |
| `scripts/bootstrap.sh` | One-time setup (`new` for this site, `github` for the repository and secrets) |

DNS is not managed here: the hostname is a CNAME to `<pull zone>.b-cdn.net` at Infomaniak.

## What was changed from the original

Source: `Sites web/ltp/http/` on the NAS (the site root) and `Sites web/ltp/ltpdata/forum/`
(the forum flat files), copied into `private/`.

- **URLs kept.** `index.htm` (home, 2001), `LTP4FINRES.SHTML`, `ORGWORDEND.SHTML` (upper case, as
  linked), `bilan.shtml`, `fastresults.html`, `fastcode.html`, the compo files: same names. The
  SSI include of `menu.inc` is inlined; the `.shtml` pages are now plain HTML served as
  `text/html`.
- **ASP pages rendered once.** `index2.asp` (results hub) → `index2.html`; `forum.asp` ("Small
  words from Attenders", 75 messages of 2000-08-29 to 2000-09-13 and 2 answers of the organizers)
  → `forum.html`, rendered from the flat files with the original word wrapping, newest first.
  Its posting form is replaced by an "archived, read-only" notice; the admin answer/delete
  links are gone. `build-meta/redirects.tsv` lists the old → new names.
- **Home page**: unchanged, except the "LTP party" link, which pointed to the site's own dead
  host `http://ltp.ojuice.net`: it now opens `index2.html`, the only way to reach the 2000
  results from the 2001 home page. `face="verdana"` gets sans-serif fallbacks (`DejaVu Sans,
  Geneva, sans-serif`) for systems without Verdana (also on the other pages).
- **Added**: a post-scriptum at the end of `bilan.shtml`, in grey italics and marked
  "P.S. (added in 2026)": the page says the money left will be used for LTP5, which never took
  place; the money was given to help organise other French demoparties when the Orange Juice
  bank accounts were closed (`ADDITIONS` in `scripts/statify.py`).
- **Removed**: the cnxweb.com hit counter (script, `<noscript>` and image, 7 occurrences), the
  rollover preloader of `menu.inc` (never called; it requested six images that never existed),
  the FTP credentials of the release server (`ftp://ltp:…@ftp.ojuice.net/` → `ftp://ftp.ojuice.net/`,
  plain text, not a link).
- **Removed**: the dynamic-DNS FTP host (`quad.no-ip.com`) in the text of `index2.html`.
- **Redacted**: e-mail domains (`nick@????`) in pages, `.txt` and `.c` files (only Skal's address in
  `check11.c`). The zip archives are published unchanged.
- **Not published** (`scripts/exclude-globs.txt`): `img/ltpintro.swf`, every `.asp` source (`getadmin.asp`, `m.asp`,
  `forumltp.asp`, ...), `menu.inc`, `*.bak`, `.DS_Store`, the pre-party entry page
  (`img/index.htm`, `img/index.asp`) and entrance order form (`ltpform.txt`, `ltpform.zip`), and
  `check.c` (an older, unlinked copy of the compo checker; `check11.c` and `search.c` are linked
  from the results and published). `forumltp.asp` and `ltpdata/Archivesforum/` are the
  pre-party Q&A forum (other layout, missing images): they belong to the `LTP4` archive. The
  logins folders of `ltpdata/` were never copied.
- **Fixed links**: `www.ojuice.net`, `ojuice.net/tshirts.htm` and `nectarine.ojuice.net` on the home page point to their
  archives on `sauthier.family`; `check.zip` (never existed) in `fastcode.html` points to
  `check11.c`, the checker source.
- **Layout**: every page is limited to 1024 px and centred (a wrapper `div` added by `statify.py`).
- **Left as they were**: other dead external links (`ojuice.net/piclib/...`,
  sponsors) and `../img/fond2.gif` in `fastcode.ltp3.html` (broken in 2000). Unlinked images of
  the server (`img/`, `slices/`) are published as they were, except the Flash intro
  `img/ltpintro.swf`, which belongs to the `LTP4` archive and is not published here.

## Regenerating `site/`

`site/` is generated: never edit it by hand, fix `scripts/statify.py` and regenerate. The raw
originals live in `private/` (git-ignored; `$LTP4PP_RAW` and `$LTP4PP_FORUM` override the
paths); the build never reads the NAS. Keep `private/`, it is the working copy.

```bash
python3 scripts/statify.py && python3 scripts/verify_build.py && python3 scripts/check_excludes.py
```

```bash
python3 scripts/preview.py 3544
```

## Hardening (`infra/main.tf`)

- Edge rule 1: any method other than GET, HEAD, OPTIONS is blocked at the edge, before the
  origin (bunny.net answers 403; edge rules cannot return 405). `block_post_requests` is also on.
- Edge rule 2: `Content-Security-Policy` (same-origin, inline script/style allowed, images from
  the site only, `form-action 'none'`), `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy`, HSTS, `Permissions-Policy`.
- Edge rules 3-4: `Content-Type` with `charset=iso-8859-1` for `.htm/.html/.shtml/.SHTML` and
  `.txt/.c` (the pages are ISO-8859-1).
- Edge rule 5: browser cache 7 days for images and archives, 1 hour for pages; CDN cache 30
  days, purged on each deployment.
- Archives (`zip swf`): `application/octet-stream` + `Content-Disposition: attachment`.
- COOP/CORP `same-origin`. Search engines are allowed (no `X-Robots-Tag`; `robots.txt` and `sitemap.xml` allow everything).
- CI (deploy workflow), before upload: excluded-paths check, `scripts/verify_build.py --build site`
  and a ClamAV scan of `site/`.
- Cookies are stripped before the origin; TLS "Compatible"; forced HTTPS.
- Custom 404: `hosting/404.html` (`not_found_page` in `site.json`).

## Removal requests

Pages that link a file holding a family name or e-mail (`fastresults.html`, `index2.html`: the fast code zips) end with a small footer, "To be removed from this page, contact me." (a `mailto:` link). `scripts/statify.py` adds it (`is_people_page`), so it survives rebuilds; `scripts/verify_build.py` leaves it out of its `mailto:` and e-mail checks.

## Deploying

- **Website**: push a change under `site/` or `hosting/` to `main` → workflow *Website: deploy*
  runs the checks, uploads the changed files, deletes the removed ones, purges the CDN and
  runs the smoke test. A manual run allows a dry run.
- **Infra**: pull requests touching `infra/` show the plan; apply is a manual run of
  *Infra: bunny.net* (action `apply`, from `main`), which commits the encrypted state, deploys
  `site/` and runs the smoke test.

GitHub secrets: `BUNNY_API_KEY` (bunny.net account API key) and `TF_VAR_STATE_PASSPHRASE`
(state encryption), both from Proton Pass vault `OldSites`.

Locally (Proton Pass CLI logged in):

```bash
pass-cli run --env-file infra/secrets.env -- python3 scripts/deploy.py --dry-run
```

```bash
cd infra && pass-cli run --env-file secrets.env -- tofu plan
```

## First setup (done on 2026-11-23, kept as a record)

1. Write `site.json` and validate offline (done on 2026-11-23; secrets are the shared ones of
   the other old sites: same Proton Pass references):

   ```bash
   scripts/bootstrap.sh new LTP4-postparty ltp4-postparty ltp4-postparty ltp4-postparty.sauthier.family
   ```

2. Create the GitHub repository and its secrets, push, open the PR (done on 2026-11-23):

   ```bash
   scripts/bootstrap.sh github
   ```

3. After merge, run the *Infra: bunny.net* workflow with action `apply` (done on 2026-11-23): it creates the zones,
   hostname and edge rules, deploys `site/` and runs the smoke test.
4. At Infomaniak (Manager > Domaines > sauthier.family > Zone DNS), add a CNAME (done on 2026-11-23)
   `ltp4-postparty` → `ltp4-postparty.b-cdn.net`. The certificate is issued once DNS answers;
   re-run the smoke test (*Monitoring: weekly smoke test*, manual run) after a few minutes.

## Manual steps in the bunny.net dashboard (only if the apply cannot do it)

If the apply rejects an edge rule or the 404 path, set it by hand (CDN > pull zone
`ltp4-postparty`):

1. *Edge rules* > *Add Edge Rule*: condition *Request Method* is none of `GET`, `HEAD`,
   `OPTIONS` → action *Block Request*.
2. *Edge rules* > *Add Edge Rule*: condition *URL* `*` → one *Set Response Header* action per
   header listed above (values in `infra/main.tf`, `local.csp` and the rule 2 block).
3. *Edge rules*: condition *URL Extension* `htm`, `html`, `shtml`, `SHTML` → *Set Response Header*
   `Content-Type: text/html; charset=iso-8859-1`.
4. Storage > storage zone `ltp4-postparty` > *Error pages*: set the 404 file to `/404.html`.

## To Do

Cross-links still to fix in a batch pass (the targets are archived on `sauthier.family`):

- Two `ojuice.net/piclib/index.asp?...` links (`ORGWORDEND.SHTML`): no equivalent in Orange
  Juice v3 (https://orangejuicev3.sauthier.family) yet.

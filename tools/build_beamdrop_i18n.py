# -*- coding: utf-8 -*-
"""Build the static multilingual BeamDrop support pages.

    python tools/build_beamdrop_i18n.py

Edit only:
  i18n/beamdrop-support.json            (all copy, captions, SEO metadata)
  i18n/beamdrop-support.template.html   (markup)
Then rerun this script and commit the generated files:
  beamdrop-support.html, {fr,es,ar,ja,ko}/beamdrop-support.html,
  assets/beamdrop/demo.{en,fr,es,ar,ja,ko}.vtt

Every generated page is a fully rendered static HTML file (no JS needed for
content), so crawlers see the translated text, titles, hreflang and JSON-LD.
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "i18n" / "beamdrop-support.json"
TEMPLATE = ROOT / "i18n" / "beamdrop-support.template.html"
SUPPORT_EMAIL = "wangning.engineer@outlook.com"
APP_STORE = "https://apps.apple.com/app/beamdrop/id6776451257"
URL_EXAMPLE = "http://172.20.10.1:8080"

data = json.loads(PACK.read_text(encoding="utf-8"))
template = TEMPLATE.read_text(encoding="utf-8")
site = data["site"].rstrip("/")
page = data["page"]
langs = data["languages"]
strings = data["strings"]
en = strings["en"]

for lang in langs:
    missing = [k for k in en if k not in strings[lang]]
    if missing:
        print("[warn] %s: %d untranslated keys -> English fallback: %s"
              % (lang, len(missing), ", ".join(missing)))
    if len(data["captions"][lang]) != len(data["caption_cues"]):
        raise SystemExit("[error] %s: caption count mismatch" % lang)


def raw(lang, key):
    return strings[lang].get(key, en.get(key, ""))


def attr(value):
    # Apostrophes are safe inside double-quoted attributes; keep them readable.
    return html.escape(str(value), quote=True).replace('&#x27;', "'")


def text(value):
    return html.escape(str(value), quote=False)


def jstr(obj):
    return json.dumps(obj, ensure_ascii=False, indent=4).replace("<", "\\u003c")


def url_of(lang):
    return "%s/%s%s" % (site, langs[lang]["prefix"], page)


def link_from(current, target):
    """Relative link between two generated pages (works on file:// too)."""
    cur, tgt = langs[current]["prefix"], langs[target]["prefix"]
    if cur == tgt:
        return page
    if not cur:
        return tgt + page
    return "../" + tgt + page


hreflang_tags = "\n".join(
    '    <link rel="alternate" hreflang="%s" href="%s" />' % (code, url_of(code))
    for code in langs
) + '\n    <link rel="alternate" hreflang="x-default" href="%s" />' % url_of("en")

BANNER = """    <aside id="langSuggest" class="langSuggest" hidden>
        <span id="langSuggestText"></span>
        <a id="langSuggestLink" class="btn btnPrimary btnSmall" href="#"></a>
        <button id="langSuggestDismiss" class="btn btnGhost btnSmall" type="button"></button>
    </aside>"""


def switcher(current):
    items = "".join(
        '<a href="%s" hreflang="%s" lang="%s"%s>%s</a>'
        % (link_from(current, code), code, code,
           ' aria-current="page"' if code == current else "", text(meta["name"]))
        for code, meta in langs.items()
    )
    return (
        '<details class="langSwitch">'
        '<summary aria-label="%s"><svg viewBox="0 0 24 24" aria-hidden="true">'
        '<circle cx="12" cy="12" r="9"></circle>'
        '<path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18"></path>'
        '</svg><span>%s</span></summary>'
        '<div class="langMenu">%s</div>'
        '</details>'
    ) % (attr(raw(current, "lang_switch")), text(langs[current]["name"]), items)


def suggest_data():
    payload = {}
    for code, entry in data["suggest"].items():
        payload[code] = dict(entry, url=link_from("en", code))
    return '    <script type="application/json" id="langSuggestData">\n    %s\n    </script>' % jstr(payload)


def vtt(lang):
    lines = ["WEBVTT", ""]
    for i, (start, end) in enumerate(data["caption_cues"]):
        lines += [str(i + 1), "%s --> %s" % (start, end), data["captions"][lang][i], ""]
    return "\n".join(lines)


written = []
for lang, meta in langs.items():
    base = "../" if meta["prefix"] else ""
    img_prefix = "%sassets/beamdrop/%s" % (base, meta.get("asset_prefix", ""))
    canonical = url_of(lang)

    # Trusted inline HTML fragments shared by all copy (UI strings stay in English).
    common = {
        "privacy_link": '<a href="%sbeamdrop-privacy.html">%s</a>'
                        % (base, text(raw(lang, "privacy_label"))),
        "email_link": '<a href="mailto:%s">%s</a>' % (SUPPORT_EMAIL, SUPPORT_EMAIL),
        "url": "<code>%s</code>" % URL_EXAMPLE,
        "select_label": '<span class="kbd">Select Photos or Videos</span>',
        "download_all": '<span class="kbd">Download All</span>',
    }

    def T(key):
        out = text(raw(lang, key))
        for placeholder, fragment in common.items():
            out = out.replace("{{" + placeholder + "}}", fragment)
        return out

    def A(key):
        return attr(raw(lang, key))

    app_ld = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": "BeamDrop",
        "operatingSystem": "iOS 17+",
        "applicationCategory": "UtilitiesApplication",
        "url": canonical,
        "downloadUrl": APP_STORE,
        "description": raw(lang, "app_description"),
        "inLanguage": lang,
        "offers": {"@type": "Offer", "price": "0.99", "priceCurrency": "USD"},
        "aggregateRating": {"@type": "AggregateRating", "ratingValue": "5", "ratingCount": "1"},
    }
    faq_ld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": raw(lang, "q%d" % i),
                "acceptedAnswer": {"@type": "Answer", "text": raw(lang, "a%d" % i)},
            }
            for i in (1, 2, 3, 5)
        ],
    }

    values = {
        "lang": lang,
        "dir": meta["dir"],
        "site": site,
        "base": base,
        "img_prefix": img_prefix,
        "canonical": canonical,
        "hreflang_tags": hreflang_tags,
        "title": A("title"),
        "description": A("description"),
        "keywords": A("keywords"),
        "og_locale": meta["locale"],
        "og_title": A("og_title"),
        "og_description": A("og_description"),
        "og_url": canonical,
        "jsonld_app": jstr(app_ld),
        "jsonld_faq": jstr(faq_ld),
        "suggest_data": suggest_data() if lang == "en" else "",
        "suggest_banner": BANNER if lang == "en" else "",
        "lang_switch": switcher(lang),
    }
    for key in en:
        if key not in values:
            values[key] = T(key)
    values["track_label"] = A("track_label")
    values["privacy_label"] = T("privacy_label")
    values["nav_privacy"] = T("nav_privacy")
    values["footer_contact"] = T("footer_contact")
    values["footer_home"] = T("footer_home")
    values["rights"] = T("rights")

    out = template
    for key, value in values.items():
        out = out.replace("{{" + key + "}}", str(value))
    if "{{" in out:
        leftovers = sorted(set(t.split("}}")[0] for t in out.split("{{")[1:]))
        raise SystemExit("[error] %s: unresolved placeholders: %s" % (lang, leftovers))

    dest = ROOT / meta["prefix"] / page if meta["prefix"] else ROOT / page
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(out)
    written.append(str(dest.relative_to(ROOT)))

    vtt_path = ROOT / "assets" / "beamdrop" / ("demo.%s.vtt" % lang)
    content = vtt(lang)
    # Avoid touching unchanged files (keeps the original demo.en.vtt byte-identical).
    if not vtt_path.exists() or vtt_path.read_text(encoding="utf-8") != content:
        with vtt_path.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        written.append(str(vtt_path.relative_to(ROOT)))

# Post-build checks: every relative asset link must exist and every JSON-LD
# / suggestion JSON block must parse.
broken = []
for name in written:
    if not name.endswith(".html"):
        continue
    path = ROOT / name
    content = path.read_text(encoding="utf-8")
    for target in re.findall(r'(?:href|src|poster)="([^"]+)"', content):
        if target.startswith(("http", "mailto:", "#")):
            continue
        if not (path.parent / target).exists():
            broken.append((name, target))
    for block in re.findall(r'<script type="application/(?:ld\+json|json)"[^>]*>(.*?)</script>',
                            content, re.S):
        json.loads(block)
if broken:
    raise SystemExit("[error] broken local links: %s" % broken)

print("Wrote %d files this run (all local links resolve, JSON blocks valid):" % len(written))
for name in written:
    print("  " + name)

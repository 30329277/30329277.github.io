# -*- coding: utf-8 -*-
"""Generic builder for multilingual static support pages.

    python tools/build_i18n.py

Every app is described by a pack file  i18n/<slug>.json  plus a template
i18n/<slug>.template.html  (pack key "template"). The builder renders one
fully static HTML page per language (en at repo root, others under <lang>/),
so crawlers see translated titles/copy/hreflang/JSON-LD without executing JS.

Pack schema (see i18n/beamdrop-support.json for a complete example):
  site, page, template, privacy_page, og_image, asset_dir, support_email,
  languages (optional, defaults to en/fr/es/ar/ja/ko),
  app {name, operating_system, application_category, download_url, price,
       price_currency, rating{value,count}, faq_schema:[q indices], extra{}},
  fragments {name: trusted inline HTML, {{base}} allowed},
  suggest (optional override of the language-suggestion banner copy),
  caption_cues + captions (optional, per-language video subtitles),
  strings {en, fr, es, ar, ja, ko}  -- every user-facing string.
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
I18N_DIR = ROOT / "i18n"

DEFAULT_SITE = "https://30329277.github.io"
DEFAULT_EMAIL = "wangning.engineer@outlook.com"
DEFAULT_LANGS = {
    "en": {"name": "English", "locale": "en_US", "dir": "ltr", "prefix": "", "asset_prefix": ""},
    "de": {"name": "Deutsch", "locale": "de_DE", "dir": "ltr", "prefix": "de/", "asset_prefix": ""},
    "fr": {"name": "Français", "locale": "fr_FR", "dir": "ltr", "prefix": "fr/", "asset_prefix": ""},
    "es": {"name": "Español", "locale": "es_ES", "dir": "ltr", "prefix": "es/", "asset_prefix": ""},
    "ar": {"name": "العربية", "locale": "ar_AR", "dir": "rtl", "prefix": "ar/", "asset_prefix": ""},
    "ja": {"name": "日本語", "locale": "ja_JP", "dir": "ltr", "prefix": "ja/", "asset_prefix": ""},
    "ko": {"name": "한국어", "locale": "ko_KR", "dir": "ltr", "prefix": "ko/", "asset_prefix": ""},
}
DEFAULT_SUGGEST = {
    "de": {
        "message": "Ihr Browser ist auf Deutsch eingestellt. Möchten Sie diese Seite auf Deutsch lesen?",
        "cta": "Auf Deutsch wechseln", "dismiss": "Auf Englisch bleiben",
        "tz": ["Europe/Berlin", "Europe/Vienna", "Europe/Zurich", "Europe/Luxembourg"],
    },
    "fr": {
        "message": "Votre navigateur est configuré en français. Préférez-vous lire cette page en français ?",
        "cta": "Passer en français", "dismiss": "Rester en anglais",
        "tz": ["Europe/Paris", "Europe/Brussels", "Europe/Luxembourg", "Europe/Geneva",
               "Africa/Casablanca", "Africa/Algiers", "Africa/Tunis"],
    },
    "es": {
        "message": "Tu navegador está configurado en español. ¿Quieres leer esta página en español?",
        "cta": "Cambiar a español", "dismiss": "Seguir en inglés",
        "tz": ["Europe/Madrid", "America/Mexico_City", "America/Bogota", "America/Lima",
               "America/Argentina/Buenos_Aires", "America/Santiago"],
    },
    "ar": {
        "message": "متصفحك مضبوط على العربية. هل تفضل قراءة هذه الصفحة بالعربية؟",
        "cta": "التبديل إلى العربية", "dismiss": "البقاء بالإنجليزية",
        "tz": ["Asia/Riyadh", "Asia/Dubai", "Asia/Kuwait", "Asia/Qatar", "Asia/Baghdad",
               "Africa/Cairo", "Africa/Khartoum", "Asia/Amman", "Asia/Beirut"],
    },
    "ja": {
        "message": "ブラウザーの言語が日本語に設定されています。このページを日本語で表示しますか？",
        "cta": "日本語で表示", "dismiss": "英語のまま", "tz": ["Asia/Tokyo"],
    },
    "ko": {
        "message": "브라우저 언어가 한국어로 설정되어 있습니다. 이 페이지를 한국어로 읽으시겠어요?",
        "cta": "한국어로 보기", "dismiss": "영어로 계속 보기", "tz": ["Asia/Seoul"],
    },
}

BANNER = """    <aside id="langSuggest" class="langSuggest" hidden>
        <span id="langSuggestText"></span>
        <a id="langSuggestLink" class="btn btnPrimary btnSmall" href="#"></a>
        <button id="langSuggestDismiss" class="btn btnGhost btnSmall" type="button"></button>
    </aside>"""


def attr(value):
    # Apostrophes are safe inside double-quoted attributes; keep them readable.
    return html.escape(str(value), quote=True).replace('&#x27;', "'")


def text(value):
    return html.escape(str(value), quote=False)


def jstr(obj):
    return json.dumps(obj, ensure_ascii=False, indent=4).replace("<", "\\u003c")


def build_pack(pack_path, written):
    data = json.loads(pack_path.read_text(encoding="utf-8"))
    name = pack_path.stem
    template = (ROOT / data["template"]).read_text(encoding="utf-8")
    site = data.get("site", DEFAULT_SITE).rstrip("/")
    page = data["page"]
    privacy_page = data.get("privacy_page", "privacy.html")
    langs = data.get("languages", DEFAULT_LANGS)
    strings = data["strings"]
    en = strings["en"]
    email = data.get("support_email", DEFAULT_EMAIL)
    suggest = data.get("suggest", DEFAULT_SUGGEST)
    app_meta = data.get("app", {})
    asset_dir = data.get("asset_dir", "")

    for lang in langs:
        miss = [k for k in en if k not in strings[lang]]
        if miss:
            print("[warn] %s/%s: %d untranslated keys -> English fallback: %s"
                  % (name, lang, len(miss), ", ".join(miss[:8]) + ("..." if len(miss) > 8 else "")))
    if data.get("caption_cues"):
        for lang in langs:
            if len(data["captions"][lang]) != len(data["caption_cues"]):
                raise SystemExit("[error] %s: %s caption count mismatch" % (name, lang))

    def raw(lang, key):
        # Pack strings are plain text; an "&amp;" there is a markup artifact and
        # would be double-escaped downstream (title/meta/JSON-LD).
        return strings[lang].get(key, en.get(key, "")).replace("&amp;", "&")

    def plain(lang, key):
        # FAQ JSON-LD must stay valid JSON: resolve fragment placeholders to
        # plain text instead of letting HTML markup leak inside the JSON.
        out = raw(lang, key)
        out = out.replace("{{privacy_link}}", strings[lang].get("privacy_label", en.get("privacy_label", "Privacy Policy")))
        out = out.replace("{{email_link}}", email)
        return re.sub(r"\{\{\w+\}\}", "", out)

    def url_of(lang):
        return "%s/%s%s" % (site, langs[lang]["prefix"], page)

    def link_from(current, target):
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
        for code, entry in suggest.items():
            payload[code] = dict(entry, url=link_from("en", code))
        return '    <script type="application/json" id="langSuggestData">\n    %s\n    </script>' % jstr(payload)

    def vtt(lang):
        lines = ["WEBVTT", ""]
        for i, (start, end) in enumerate(data["caption_cues"]):
            lines += [str(i + 1), "%s --> %s" % (start, end), data["captions"][lang][i], ""]
        return "\n".join(lines)

    app_ld = {"@context": "https://schema.org", "@type": "SoftwareApplication"}
    app_ld["name"] = app_meta.get("name", "App")
    if app_meta.get("operating_system"):
        app_ld["operatingSystem"] = app_meta["operating_system"]
    if app_meta.get("application_category"):
        app_ld["applicationCategory"] = app_meta["application_category"]
    if app_meta.get("download_url"):
        app_ld["downloadUrl"] = app_meta["download_url"]
    if app_meta.get("price"):
        app_ld["offers"] = {"@type": "Offer", "price": app_meta["price"],
                            "priceCurrency": app_meta.get("price_currency", "USD")}
    if app_meta.get("rating"):
        app_ld["aggregateRating"] = {"@type": "AggregateRating",
                                     "ratingValue": app_meta["rating"].get("value", "5"),
                                     "ratingCount": app_meta["rating"].get("count", "1")}
    if app_meta.get("extra"):
        app_ld.update(app_meta["extra"])

    faq_schema = app_meta.get("faq_schema") or []

    for lang, meta in langs.items():
        base = "../" if meta["prefix"] else ""
        img_prefix = "%s%s/%s" % (base, asset_dir, meta.get("asset_prefix", "")) if asset_dir else ""
        canonical = url_of(lang)

        fragments = {
            "privacy_link": '<a href="%s%s">%s</a>' % (base, privacy_page, text(raw(lang, "privacy_label"))),
            "email_link": '<a href="mailto:%s">%s</a>' % (email, email),
        }
        for fname, fval in data.get("fragments", {}).items():
            if isinstance(fval, dict):
                fval = fval.get(lang, fval.get("en", ""))
            fragments[fname] = str(fval).replace("{{base}}", base)

        def T(key):
            out = text(raw(lang, key))
            for placeholder, fragment in fragments.items():
                out = out.replace("{{" + placeholder + "}}", fragment)
            return out

        def A(key):
            return attr(raw(lang, key))

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
            "og_image": attr(data.get("og_image", "")),
            "jsonld_app": jstr(dict(app_ld, url=canonical, description=raw(lang, "app_description"),
                                    inLanguage=lang)),
            "jsonld_faq": jstr({
                "@context": "https://schema.org",
                "@type": "FAQPage",
                "mainEntity": [
                    {"@type": "Question", "name": plain(lang, "q%d" % i),
                     "acceptedAnswer": {"@type": "Answer", "text": plain(lang, "a%d" % i)}}
                    for i in faq_schema
                ],
            }) if faq_schema else "",
            "suggest_data": suggest_data() if lang == "en" else "",
            "suggest_banner": BANNER if lang == "en" else "",
            "lang_switch": switcher(lang),
        }
        if data.get("caption_cues"):
            values["track_label"] = A("track_label")
        for key in en:
            if key not in values:
                values[key] = T(key)

        out = template
        for key, value in values.items():
            out = out.replace("{{" + key + "}}", str(value))
        for fname, fval in fragments.items():
            out = out.replace("{{" + fname + "}}", fval)
        if "{{" in out:
            leftovers = sorted(set(t.split("}}")[0] for t in out.split("{{")[1:]))
            raise SystemExit("[error] %s/%s: unresolved placeholders: %s" % (name, lang, leftovers))

        dest = ROOT / meta["prefix"] / page if meta["prefix"] else ROOT / page
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(out)
        written.append(dest)

        if data.get("caption_cues") and asset_dir:
            vtt_path = ROOT / asset_dir / ("demo.%s.vtt" % lang)
            content = vtt(lang)
            # Avoid touching unchanged files (keeps originals byte-identical).
            if not vtt_path.exists() or vtt_path.read_text(encoding="utf-8") != content:
                with vtt_path.open("w", encoding="utf-8", newline="\n") as fh:
                    fh.write(content)
                written.append(vtt_path)


def main():
    packs = sorted(I18N_DIR.glob("*.json"))
    if not packs:
        raise SystemExit("[error] no packs found in i18n/")
    written = []
    for pack_path in packs:
        try:
            build_pack(pack_path, written)
            print("[ok] %s" % pack_path.name)
        except KeyError as exc:
            raise SystemExit("[error] %s: missing key %s" % (pack_path.name, exc))

    # Post-build checks: every relative asset link must exist and every JSON
    # block must parse.
    broken = []
    for path in written:
        if path.suffix != ".html":
            continue
        content = path.read_text(encoding="utf-8")
        for target in re.findall(r'(?:href|src|poster)="([^"]+)"', content):
            if target.startswith(("http", "mailto:", "#")):
                continue
            if not (path.parent / target.split("?", 1)[0]).exists():
                broken.append((str(path.relative_to(ROOT)), target))
        for block in re.findall(r'<script type="application/(?:ld\+json|json)"[^>]*>(.*?)</script>',
                                content, re.S):
            json.loads(block)
    if broken:
        raise SystemExit("[error] broken local links: %s" % broken)

    print("Built %d files (all local links resolve, JSON blocks valid)." % len(written))


if __name__ == "__main__":
    main()

(function () {
    'use strict';

    // Set to true only if you want a silent redirect instead of a suggestion.
    // Not recommended: Google advises against automatic locale redirects, and
    // hreflang already serves the right page to search users.
    var AUTO_REDIRECT = false;
    var STORAGE_KEY = 'beamdrop-lang-choice';

    // Close the language dropdown when clicking outside (all language pages).
    var sw = document.querySelector('.langSwitch');
    if (sw) {
        document.addEventListener('click', function (e) {
            if (!sw.contains(e.target)) sw.open = false;
        });
    }

    var dataEl = document.getElementById('langSuggestData');
    var banner = document.getElementById('langSuggest');
    if (!dataEl || !banner) return; // only the default English page has a suggestion

    var suggest;
    try {
        suggest = JSON.parse(dataEl.textContent);
    } catch (e) {
        return;
    }

    // Browser UI language (no permission, no network, no cookie).
    function detect() {
        var prefs = navigator.languages || [navigator.language || ''];
        for (var i = 0; i < prefs.length; i++) {
            var code = String(prefs[i]).toLowerCase().split('-')[0];
            if (suggest[code]) return code;
        }
        // Region fallback: timezone is local browser data, never a geolocation prompt.
        try {
            var tz = (Intl.DateTimeFormat().resolvedOptions().timeZone || '').toLowerCase();
            for (var lang in suggest) {
                if (!Object.prototype.hasOwnProperty.call(suggest, lang)) continue;
                var zones = suggest[lang].tz || [];
                for (var j = 0; j < zones.length; j++) {
                    if (tz.indexOf(String(zones[j]).toLowerCase()) === 0) return lang;
                }
            }
        } catch (e) {}
        return null;
    }

    var lang = detect();
    if (!lang) return; // unsupported locale -> stay on English
    try {
        if (localStorage.getItem(STORAGE_KEY) === 'declined') return;
    } catch (e) {}

    var entry = suggest[lang];
    var textEl = document.getElementById('langSuggestText');
    var linkEl = document.getElementById('langSuggestLink');
    var dismissEl = document.getElementById('langSuggestDismiss');
    if (!entry || !textEl || !linkEl || !dismissEl) return;

    linkEl.href = entry.url;
    linkEl.hreflang = lang;

    if (AUTO_REDIRECT) {
        location.replace(entry.url);
        return;
    }

    textEl.textContent = entry.message;
    linkEl.textContent = entry.cta;
    dismissEl.textContent = entry.dismiss;
    banner.hidden = false;

    dismissEl.addEventListener('click', function () {
        banner.hidden = true;
        // Optional, first-party, functional preference. Remove these two lines
        // for zero storage at all.
        try {
            localStorage.setItem(STORAGE_KEY, 'declined');
        } catch (e) {}
    });
})();

"""TÜBA Türkçe Bilim Terimleri istemcisi.

Sözlük ``tubaterim.gov.tr`` kabuğunun açtığı ``terim.tuba.gov.tr``
uygulamasındadır. ``Arama Sonucu`` bölümündeki kalın başlık madde
başlığıdır. ``İlgili Sonuçlar`` ayrı maddelerdir.
"""

from __future__ import annotations

import re
import urllib.parse
from typing import Any

import httpx
import truststore
from bs4 import BeautifulSoup

from .search_cache import SearchCache

truststore.inject_into_ssl()

SEARCH_URL = "https://terim.tuba.gov.tr/ATS/index.php/w_anasayfa/search/"
SITE_URL = "https://terim.tuba.gov.tr/ATS/index.php/w_anasayfa"

DICTIONARIES = {
    "37": "Sosyal Bilimler Terimleri Sözlüğü",
    "38": "Doğa Bilimleri Terimleri Sözlüğü",
    "39": "Mühendislik Terimleri Sözlüğü",
}
SHORT_LABELS = {
    "doğa.": "Doğa Bilimleri Terimleri Sözlüğü",
    "müh.": "Mühendislik Terimleri Sözlüğü",
    "sos.": "Sosyal Bilimler Terimleri Sözlüğü",
}
MATCH_MODES = {
    "exact": "1",
    "prefix": "2",
    "suffix": "3",
    "contains": "4",
}

EXACT_NOTE = (
    "Kayıtlar bu sorgu için TÜBA Türkçe Bilim Terimleri Sözlüğü'nden açıldı. "
    "Madde başlığı yalnız `sozcuk` alanıdır. Sorgu metni bu başlıkla aynı değilse terim diye yazılmaz. "
    "Yazarken maddeyi yeniden sorgula; önceki oturumun sonucunu taşıma."
)
FOREIGN_NOTE = (
    "Sorgu bir madde başlığı değil. Eşleşen maddenin başlığı `sozcuk` alanıdır; "
    "yazılacak terim odur. Yazarken o başlıkla yeniden sorgula."
)
MISS_NOTE = (
    "Bu dizgi TÜBA Türkçe Bilim Terimleri Sözlüğü'nde madde başlığı değil. "
    "`other_headings` ayrı maddelerdir ve bu sorgunun tanımı değildir. "
    "Tanım için tam başlıkla yeniden sorgula."
)
LONGER_NOTE = "Bunlar ayrı madde başlıklarıdır. Bu sorgunun başlığı değildir."

_LANG = re.compile(r"\(Alm\.\s*(.*?);\s*Fr\.\s*(.*?);\s*İng\.\s*(.*?)\)", re.IGNORECASE)
_TERM_ID = re.compile(r"(?:js_sonuc_tanim|yorum_container_|yorum_snc_|yorum_input_)\(?(\d+)\)?")


class TubaError(Exception):
    """TÜBA isteği sonuç üretemedi."""


def turkish_fold(value: str) -> str:
    return value.strip().replace("İ", "i").replace("I", "ı").casefold()


def same_heading(query: str, heading: str) -> bool:
    folded = turkish_fold(query)
    return bool(folded) and folded == turkish_fold(heading)


def dictionary_ids(dictionary: str | None) -> str:
    if not dictionary or not dictionary.strip() or turkish_fold(dictionary) in {"hepsi", "tümü", "tumu", "*"}:
        return "37,38,39"
    picked = _pick_dictionaries(turkish_fold(dictionary))
    if not picked:
        known = ", ".join(DICTIONARIES.values())
        raise TubaError(f"Bilinmeyen sözlük: {dictionary}. Sözlükler: {known}.")
    return ",".join(picked)


def _pick_dictionaries(folded: str) -> list[str]:
    if folded in {"38", "doğa", "doga", "doğa bilimleri", "doga bilimleri"}:
        return ["38"]
    if folded in {"39", "mühendislik", "muhendislik", "müh", "muh"}:
        return ["39"]
    if folded in {"37", "sosyal", "sos"}:
        return ["37"]
    matched = [code for code, name in DICTIONARIES.items() if folded in turkish_fold(name)]
    return matched


def reopen_url(heading: str) -> str:
    return SEARCH_URL + "?" + urllib.parse.urlencode(
        {"q": heading, "arama_options": "1", "szl": "37,38,39", "lng": "1,2,3"}
    )


def parse_search(html: str, query: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find(id="arama_sonucu_container")
    if container is None:
        raise TubaError("TÜBA arama sonucu sayfada yok.")
    total_tag = container.find("u")
    total_text = total_tag.get_text(strip=True) if total_tag else ""
    total = int(total_text) if total_text.isdigit() else 0
    primary_blocks = []
    related_blocks = []
    for block in container.select("div.arama_sonucu_content_tumu"):
        title = block.find_previous("div", class_="title6")
        if title is not None and "İlgili" in title.get_text():
            related_blocks.append(block)
        else:
            primary_blocks.append(block)
    primary = [card for card in (_card(block) for block in primary_blocks) if card["sozcuk"]]
    related = [card for card in (_card(block) for block in related_blocks) if card["sozcuk"]]
    exact = [card for card in primary if same_heading(query, card["sozcuk"])]
    other_primary = [card for card in primary if card not in exact]
    other_headings = []
    seen = {turkish_fold(card["sozcuk"]) for card in exact}
    seen.update(turkish_fold(card["sozcuk"]) for card in other_primary)
    for card in related:
        key = turkish_fold(card["sozcuk"])
        if not key or key in seen or same_heading(query, card["sozcuk"]):
            continue
        seen.add(key)
        other_headings.append(
            {
                "sozcuk": card["sozcuk"],
                "sozluk": card.get("sozluk", ""),
                "reopen_url": card["reopen_url"],
            }
        )
    is_heading = bool(exact)
    if is_heading:
        note = EXACT_NOTE
    elif other_primary:
        note = FOREIGN_NOTE
    else:
        note = MISS_NOTE
    result: dict[str, Any] = {
        "query": query,
        "source": "TÜBA Türkçe Bilim Terimleri Sözlüğü",
        "is_heading": is_heading,
        "total": total,
        "entries": exact,
        "reopen_url": reopen_url(query),
        "note": note,
    }
    if other_primary and not is_heading:
        result["matched_entries"] = other_primary
    if other_headings:
        result["other_headings"] = other_headings[:12]
        result["other_headings_note"] = LONGER_NOTE
        if len(other_headings) > 12:
            result["other_headings_omitted"] = len(other_headings) - 12
    return result


def _card(block: Any) -> dict[str, Any]:
    head = block.select_one("div.sonuc_terim")
    bold = head.find("b") if head is not None else None
    heading = bold.get_text(" ", strip=True) if bold else ""
    label = ""
    if head is not None:
        span = head.select_one("span.sozluk_kisa_tanim")
        if span is not None:
            label = span.get_text(" ", strip=True).strip("()").strip()
    senses = _senses(block)
    card: dict[str, Any] = {
        "sozcuk": heading,
        "sozluk": SHORT_LABELS.get(label, label),
        "anlamlar": senses,
        "reopen_url": reopen_url(heading) if heading else "",
    }
    term_id = _term_id(block)
    if term_id:
        card["terim_id"] = term_id
    if label:
        card["sozluk_kisa"] = label
    ingiliz = _english(senses)
    if ingiliz:
        card["ingiliz"] = ingiliz
    return card


def _senses(block: Any) -> list[str]:
    senses: list[str] = []
    for div in block.find_all("div"):
        if div.find("div"):
            continue
        classes = " ".join(div.get("class") or [])
        if "yorum" in classes or "sonuc_terim" in classes:
            continue
        text = div.get_text(" ", strip=True)
        if not text or text.startswith("Lütfen bu terim") or text == "Yorum ekle":
            continue
        senses.append(text)
    return senses


def _english(senses: list[str]) -> str:
    for sense in senses:
        match = _LANG.search(sense)
        if match:
            return match.group(3).strip().rstrip(".")
    return ""


def _term_id(block: Any) -> str:
    blob = " ".join(
        filter(
            None,
            [
                block.get("id", ""),
                " ".join(block.get("class") or []),
                str(block),
            ],
        )
    )
    match = _TERM_ID.search(blob)
    return match.group(1) if match else ""


class TubaClient:
    def __init__(self, timeout: float = 40.0) -> None:
        self.cache = SearchCache("tuba-terim")
        self._client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/json",
            },
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def search(self, query: str, dictionary: str | None = None, match: str = "exact") -> dict[str, Any]:
        text = query.strip()
        if not text:
            raise TubaError("Arama metni boş.")
        mode = MATCH_MODES.get(match)
        if mode is None:
            raise TubaError("match tam sözcük (exact), prefix, suffix veya contains olmalı.")
        cache_key = self.cache.key("search", text, dictionary, match)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        params = {
            "q": text,
            "arama_options": mode,
            "szl": dictionary_ids(dictionary),
            "lng": "1,2,3",
        }
        html = await self._get_text(params)
        result = parse_search(html, text)
        result["match"] = match
        if dictionary and dictionary.strip():
            result["dictionary"] = dictionary
        result["cache"] = "miss"
        self.cache.set(cache_key, result)
        return result

    async def list_dictionaries(self) -> dict[str, Any]:
        return {
            "source": "TÜBA Türkçe Bilim Terimleri Sözlüğü",
            "site": SITE_URL,
            "dictionaries": [
                {"id": code, "ad": name} for code, name in DICTIONARIES.items()
            ],
        }

    async def _get_text(self, params: dict[str, str]) -> str:
        last_error: Exception | None = None
        for _ in range(3):
            try:
                response = await self._client.get(SEARCH_URL, params=params)
                response.raise_for_status()
                return response.text
            except httpx.HTTPError as exc:
                last_error = exc
        raise TubaError(f"TÜBA sözlüğüne ulaşılamadı: {last_error}") from last_error

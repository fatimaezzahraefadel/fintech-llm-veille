"""Nettoyage et normalisation des données textuelles."""

from __future__ import annotations

import re
import unicodedata
from html.parser import HTMLParser


class _HTMLStripper(HTMLParser):
    """Parser HTML minimaliste pour extraire le texte brut."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(self._parts)


def strip_html(text: str) -> str:
    """Supprime les balises HTML d'un texte."""
    if not text:
        return ""
    stripper = _HTMLStripper()
    stripper.feed(text)
    return stripper.get_text()


def normalize_whitespace(text: str) -> str:
    """Normalise les espaces et sauts de ligne."""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_unicode(text: str) -> str:
    """Normalise l'encodage Unicode (NFC)."""
    return unicodedata.normalize("NFC", text)


def remove_boilerplate(text: str) -> str:
    """
    Supprime les patterns boilerplate courants dans les articles financiers.
    (disclaimers, mentions légales, etc.)
    """
    boilerplate_patterns = [
        r"This article is for informational purposes only.*",
        r"Past performance is not indicative.*",
        r"This is not financial advice.*",
        r"\[.*?\]",  # Références entre crochets
        r"©.*?\d{4}",  # Copyright
    ]
    for pattern in boilerplate_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.DOTALL)
    return text


def clean_article_text(text: str) -> str:
    """
    Pipeline complet de nettoyage pour un article de presse.

    Étapes: HTML stripping → Unicode → boilerplate → whitespace.
    """
    if not text:
        return ""
    text = strip_html(text)
    text = normalize_unicode(text)
    text = remove_boilerplate(text)
    text = normalize_whitespace(text)
    return text


def clean_pdf_text(text: str) -> str:
    """
    Nettoyage spécifique pour les textes extraits de PDF SEC.

    Supprime les numéros de page, en-têtes répétitifs, etc.
    """
    if not text:
        return ""
    # Supprimer les numéros de page isolés
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)
    # Supprimer les lignes de tirets/séparateurs
    text = re.sub(r"^[-─═]+$", "", text, flags=re.MULTILINE)
    text = normalize_unicode(text)
    text = normalize_whitespace(text)
    return text


def truncate_text(text: str, max_chars: int = 4000) -> str:
    """Tronque un texte à max_chars caractères en respectant les mots."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > max_chars * 0.8:
        truncated = truncated[:last_space]
    return truncated + "..."

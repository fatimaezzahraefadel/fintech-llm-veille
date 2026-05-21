"""Collecteur de rapports SEC EDGAR (10-K, 10-Q)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import httpx
import pdfplumber
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential


# CIK connus pour les tickers les plus courants
TICKER_TO_CIK: dict[str, str] = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "GOOGL": "0001652044",
    "AMZN": "0001018724",
    "NVDA": "0001045810",
    "TSLA": "0001318605",
    "META": "0001326801",
}

EDGAR_BASE_URL = "https://data.sec.gov"
EDGAR_HEADERS = {
    "User-Agent": "FinTechLLMVeille contact@fintech-veille.local",
    "Accept-Encoding": "gzip, deflate",
}


class SECEdgarCollector:
    """Télécharge et parse les rapports 10-K et 10-Q depuis SEC EDGAR."""

    def __init__(self, output_dir: str = "./data/pdfs") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_cik(self, ticker: str) -> Optional[str]:
        """Résout le CIK depuis le ticker (lookup local puis API EDGAR)."""
        ticker = ticker.upper()
        if ticker in TICKER_TO_CIK:
            return TICKER_TO_CIK[ticker]

        # Fallback: recherche via l'API EDGAR
        try:
            url = f"{EDGAR_BASE_URL}/submissions/CIK{ticker}.json"
            with httpx.Client(headers=EDGAR_HEADERS, timeout=15) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("cik")
        except Exception as e:
            logger.warning(f"[EDGAR] Impossible de résoudre le CIK pour {ticker}: {e}")
        return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=20),
        reraise=True,
    )
    def fetch_filings_list(
        self,
        ticker: str,
        form_type: str = "10-K",
        max_filings: int = 5,
    ) -> list[dict]:
        """
        Récupère la liste des dépôts SEC pour un ticker.

        Args:
            ticker: Symbole boursier.
            form_type: Type de formulaire ('10-K' ou '10-Q').
            max_filings: Nombre maximum de dépôts à retourner.

        Returns:
            Liste de métadonnées de dépôts.
        """
        cik = self._get_cik(ticker)
        if not cik:
            logger.error(f"[EDGAR] CIK introuvable pour {ticker}")
            return []

        cik_padded = cik.lstrip("0").zfill(10)
        url = f"{EDGAR_BASE_URL}/submissions/CIK{cik_padded}.json"

        logger.info(f"[EDGAR] Récupération des dépôts {form_type} pour {ticker} (CIK: {cik})")

        with httpx.Client(headers=EDGAR_HEADERS, timeout=30) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()

        filings = data.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        dates = filings.get("filingDate", [])
        accession_numbers = filings.get("accessionNumber", [])

        results = []
        for form, filing_date, accession in zip(forms, dates, accession_numbers):
            if form == form_type and len(results) < max_filings:
                results.append(
                    {
                        "ticker": ticker,
                        "cik": cik_padded,
                        "form_type": form,
                        "filing_date": filing_date,
                        "accession_number": accession,
                    }
                )

        logger.info(f"[EDGAR] {len(results)} dépôts {form_type} trouvés pour {ticker}")
        return results

    def download_filing_document(self, filing_meta: dict) -> Optional[Path]:
        """
        Télécharge le document principal d'un dépôt SEC.

        Returns:
            Chemin vers le fichier téléchargé, ou None en cas d'échec.
        """
        ticker = filing_meta["ticker"]
        cik = filing_meta["cik"]
        accession = filing_meta["accession_number"].replace("-", "")
        form_type = filing_meta["form_type"].replace("-", "")
        filing_date = filing_meta["filing_date"]

        output_path = self.output_dir / f"{ticker}_{form_type}_{filing_date}.txt"
        if output_path.exists():
            logger.info(f"[EDGAR] Fichier déjà téléchargé: {output_path}")
            return output_path

        index_url = (
            f"{EDGAR_BASE_URL}/Archives/edgar/data/{int(cik)}/{accession}/{accession}-index.json"
        )

        try:
            with httpx.Client(headers=EDGAR_HEADERS, timeout=30) as client:
                resp = client.get(index_url)
                resp.raise_for_status()
                index_data = resp.json()

            # Chercher le document principal (htm ou txt)
            doc_url = None
            for doc in index_data.get("directory", {}).get("item", []):
                name = doc.get("name", "")
                if name.endswith((".htm", ".html", ".txt")) and form_type.lower() in name.lower():
                    doc_url = (
                        f"{EDGAR_BASE_URL}/Archives/edgar/data/{int(cik)}/{accession}/{name}"
                    )
                    break

            if not doc_url:
                logger.warning(f"[EDGAR] Document principal introuvable pour {ticker}")
                return None

            time.sleep(0.5)  # Respecter le rate limit EDGAR
            with httpx.Client(headers=EDGAR_HEADERS, timeout=60) as client:
                doc_resp = client.get(doc_url)
                doc_resp.raise_for_status()

            output_path.write_bytes(doc_resp.content)
            logger.success(f"[EDGAR] Téléchargé: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"[EDGAR] Erreur téléchargement pour {ticker}: {e}")
            return None

    @staticmethod
    def extract_text_from_pdf(pdf_path: Path) -> str:
        """Extrait le texte d'un fichier PDF avec pdfplumber."""
        text_parts: list[str] = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"[EDGAR] Erreur extraction PDF {pdf_path}: {e}")
            return ""

    def collect_reports(
        self,
        tickers: list[str],
        form_types: list[str] | None = None,
        max_per_ticker: int = 3,
    ) -> dict[str, list[dict]]:
        """
        Collecte les rapports pour une liste de tickers.

        Returns:
            Dictionnaire {ticker: [{"path": Path, "meta": dict}, ...]}.
        """
        if form_types is None:
            form_types = ["10-K", "10-Q"]

        results: dict[str, list[dict]] = {}
        for ticker in tickers:
            ticker_docs = []
            for form_type in form_types:
                filings = self.fetch_filings_list(ticker, form_type, max_per_ticker)
                for filing in filings:
                    path = self.download_filing_document(filing)
                    if path:
                        ticker_docs.append({"path": path, "meta": filing})
                    time.sleep(0.3)
            results[ticker] = ticker_docs
        return results

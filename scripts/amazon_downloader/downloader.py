from __future__ import annotations

import argparse
import gzip
import io
import os
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, unquote, urlparse

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_DIR = PROJECT_ROOT / "scripts" / "amazon_downloader"
FBA_INGEST_SCRIPTS_DIR = Path("/Users/melodylu/.claude/skills/fba-ingest/scripts")

if str(FBA_INGEST_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(FBA_INGEST_SCRIPTS_DIR))

from account_map import ACCOUNT_MAP  # type: ignore  # noqa: E402
from amazon_sp_api_client import AmazonSPAPIClient  # type: ignore  # noqa: E402
from credential_manager import CredentialManager  # type: ignore  # noqa: E402


DEFAULT_ACCOUNT_ID = 15
DEFAULT_COUNTRY = "UK"
REPORT_TYPE_ALL = "GET_MERCHANT_LISTINGS_ALL_DATA"
REPORT_TYPE_CATEGORY = "GET_MERCHANT_LISTINGS_DATA"
POLL_INTERVAL_SECONDS = 10
POLL_TIMEOUT_SECONDS = 10 * 60


class AmazonReportDownloader:
    def __init__(
        self,
        account_id: int = DEFAULT_ACCOUNT_ID,
        country: str = DEFAULT_COUNTRY,
        upload_dir: Path = UPLOAD_DIR,
    ) -> None:
        self.account_id = account_id
        self.country = country.upper().strip()
        self.upload_dir = Path(upload_dir)
        self.credential_manager = CredentialManager()
        self.marketplace_id = self._resolve_marketplace_id()
        self.client = self._build_client()

    def _resolve_marketplace_id(self) -> str:
        account_info = ACCOUNT_MAP.get(self.account_id)
        if not account_info:
            raise ValueError(f"Unknown account_id: {self.account_id}")

        marketplace_id = str(account_info.get("marketplace_id") or "").strip()
        if not marketplace_id:
            raise RuntimeError(f"Account {self.account_id} does not have a marketplace_id configured")

        if self.country != str(account_info.get("country", "")).upper():
            print(
                f"Warning: requested country={self.country}, but account {self.account_id} is mapped to "
                f"{account_info.get('country')}. Using the account marketplace anyway.",
                flush=True,
            )
        return marketplace_id

    def _build_client(self) -> AmazonSPAPIClient:
        print(f"Loading SP-API credentials for account_id={self.account_id}...", flush=True)
        creds = self.credential_manager.get_credentials_by_account_id(self.account_id)
        if not creds:
            raise RuntimeError(f"Could not load SP-API credentials for account_id={self.account_id}")

        required_fields = ("client_id", "client_secret", "refresh_token")
        missing = [field for field in required_fields if not creds.get(field)]
        if missing:
            raise RuntimeError(
                f"Credentials for account_id={self.account_id} are incomplete: missing {', '.join(missing)}"
            )

        marketplace_id = str(creds.get("marketplace_id") or self.marketplace_id)
        client = AmazonSPAPIClient(
            refresh_token=str(creds["refresh_token"]),
            client_id=str(creds["client_id"]),
            client_secret=str(creds["client_secret"]),
            marketplace_id=marketplace_id,
        )
        print(
            f"SP-API client ready for account_id={self.account_id}, marketplace_id={marketplace_id}",
            flush=True,
        )
        return client

    def create_report(self, report_type: str) -> str:
        payload = {
            "reportType": report_type,
            "marketplaceIds": [self.marketplace_id],
        }
        print(f"Creating report {report_type}...", flush=True)
        response = self.client._make_request("POST", "/reports/2021-06-30/reports", data=payload)
        report_id = response.get("reportId")
        if not report_id:
            raise RuntimeError(f"SP-API did not return reportId for reportType={report_type}: {response}")
        print(f"Created reportId={report_id}", flush=True)
        return str(report_id)

    def wait_for_report(self, report_id: str) -> dict[str, Any]:
        deadline = time.time() + POLL_TIMEOUT_SECONDS
        attempt = 0
        print(
            f"Polling report status every {POLL_INTERVAL_SECONDS}s for up to {POLL_TIMEOUT_SECONDS // 60} minutes...",
            flush=True,
        )
        while time.time() < deadline:
            attempt += 1
            response = self.client._make_request("GET", f"/reports/2021-06-30/reports/{report_id}")
            status = str(response.get("processingStatus") or "UNKNOWN")
            print(f"[poll {attempt}] reportId={report_id} status={status}", flush=True)
            if status == "DONE":
                return response
            if status in {"CANCELLED", "FATAL"}:
                raise RuntimeError(f"Report {report_id} finished with status={status}: {response}")
            time.sleep(POLL_INTERVAL_SECONDS)
        raise TimeoutError(f"Timed out waiting for report {report_id} after {POLL_TIMEOUT_SECONDS} seconds")

    def get_report_document(self, report_document_id: str) -> dict[str, Any]:
        print(f"Fetching report document metadata for {report_document_id}...", flush=True)
        response = self.client._make_request(
            "GET",
            f"/reports/2021-06-30/documents/{report_document_id}",
        )
        if not response.get("url"):
            raise RuntimeError(f"SP-API did not return a download URL for reportDocumentId={report_document_id}")
        return response

    def download_document_bytes(self, document: dict[str, Any]) -> tuple[bytes, str]:
        url = str(document["url"])
        compression = str(document.get("compressionAlgorithm") or "").upper()
        print(f"Downloading report document from pre-signed URL...", flush=True)
        response = requests.get(url, timeout=120)
        response.raise_for_status()

        content = response.content
        if compression == "GZIP":
            print("Decompressing GZIP payload...", flush=True)
            content = gzip.decompress(content)

        filename = self._extract_original_filename(response=response, url=url)
        print(f"Downloaded {len(content)} bytes, source filename={filename}", flush=True)
        return content, filename

    def download_all_listings_report(self) -> list[Path]:
        report_id = self.create_report(REPORT_TYPE_ALL)
        report = self.wait_for_report(report_id)
        report_document_id = report.get("reportDocumentId")
        if not report_document_id:
            raise RuntimeError(f"Report {report_id} is DONE but reportDocumentId is missing")

        document = self.get_report_document(str(report_document_id))
        content, original_filename = self.download_document_bytes(document)

        timestamp = self._timestamp()
        safe_original = self._sanitize_filename(original_filename or "all_listings.txt")
        if not safe_original.lower().endswith(".txt"):
            safe_original = f"{safe_original}.txt"

        target = self.upload_dir / f"{self.country}_all_listings_{timestamp}_{safe_original}"
        self._ensure_upload_dir()
        target.write_bytes(content)
        print(f"Saved All Listings report to {target}", flush=True)
        return [target]

    def download_category_listings_report(self) -> list[Path]:
        report_id = self.create_report(REPORT_TYPE_CATEGORY)
        report = self.wait_for_report(report_id)
        report_document_id = report.get("reportDocumentId")
        if not report_document_id:
            raise RuntimeError(f"Report {report_id} is DONE but reportDocumentId is missing")

        document = self.get_report_document(str(report_document_id))
        content, original_filename = self.download_document_bytes(document)
        timestamp = self._timestamp()
        self._ensure_upload_dir()

        if zipfile.is_zipfile(io.BytesIO(content)):
            print("Category report is a ZIP archive; extracting contained files...", flush=True)
            return self._save_category_from_zip(content=content, timestamp=timestamp)

        # Note: SP-API may return a single combined category listings workbook, while Seller Central UI
        # can expose multiple per-product-type workbooks (for example APPAREL-DRESS / DRESS / DRESS-UNDERGARMENT_SLIP).
        # If that happens, this downloader saves the single API response as-is.
        safe_original = self._sanitize_filename(original_filename or "category_listings.xlsm")
        target = self.upload_dir / f"{self.country}_category_{timestamp}_0_{safe_original}"
        target.write_bytes(content)
        print(f"Saved Category Listings report to {target}", flush=True)
        return [target]

    def download(self, report_type: str) -> list[Path]:
        if report_type == "all":
            return self.download_all_listings_report()
        if report_type == "category":
            return self.download_category_listings_report()
        if report_type == "both":
            return self.download_all_listings_report() + self.download_category_listings_report()
        raise ValueError(f"Unsupported report_type: {report_type}")

    def _save_category_from_zip(self, content: bytes, timestamp: str) -> list[Path]:
        saved_paths: list[Path] = []
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            members = [info for info in archive.infolist() if not info.is_dir()]
            if not members:
                raise RuntimeError("ZIP archive is empty")

            for index, member in enumerate(members):
                original_name = Path(member.filename).name or f"category_{index}.xlsm"
                safe_original = self._sanitize_filename(original_name)
                target = self.upload_dir / f"{self.country}_category_{timestamp}_{index}_{safe_original}"
                target.write_bytes(archive.read(member))
                saved_paths.append(target)
                print(f"Extracted {member.filename} -> {target}", flush=True)
        return saved_paths

    def _ensure_upload_dir(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _timestamp() -> str:
        return datetime.now().strftime("%Y%m%d%H%M%S")

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        return filename.replace("/", "_").replace("\\", "_").strip() or "report.bin"

    @staticmethod
    def _extract_original_filename(response: requests.Response, url: str) -> str:
        content_disposition = response.headers.get("content-disposition", "")
        for part in content_disposition.split(";"):
            part = part.strip()
            if part.lower().startswith("filename="):
                return unquote(part.split("=", 1)[1].strip('"'))
            if part.lower().startswith("filename*="):
                value = part.split("=", 1)[1]
                return unquote(value.split("''", 1)[-1].strip('"'))

        parsed = urlparse(url)
        query_names = parse_qs(parsed.query).get("filename")
        if query_names:
            return unquote(query_names[0])

        path_name = Path(parsed.path).name
        return unquote(path_name or "report.bin")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download Amazon SP-API All Listings and Category Listings reports.",
    )
    parser.add_argument("--country", default=DEFAULT_COUNTRY, help="Marketplace country code. Only UK is supported.")
    parser.add_argument(
        "--report-type",
        default="both",
        choices=["all", "category", "both"],
        help="Which report(s) to download.",
    )
    parser.add_argument(
        "--account-id",
        type=int,
        default=DEFAULT_ACCOUNT_ID,
        help="Amazon account_id to use. Defaults to EPUK account_id=15.",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    country = str(args.country).upper().strip()
    if country != "UK":
        parser.error("Only --country UK is supported in this downloader.")

    try:
        downloader = AmazonReportDownloader(account_id=args.account_id, country=country)
        paths = downloader.download(args.report_type)
    except Exception as error:
        print(f"Download failed: {error}", file=sys.stderr, flush=True)
        return 1

    print("Download complete. Saved files:", flush=True)
    for path in paths:
        print(f"  - {path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

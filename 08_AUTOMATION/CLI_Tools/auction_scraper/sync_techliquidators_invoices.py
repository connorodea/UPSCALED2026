#!/usr/bin/env python3
import argparse
import csv
import os
import re
from pathlib import Path
from typing import Optional

from pypdf import PdfReader


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse TechLiquidators invoice PDFs.")
    parser.add_argument(
        "--invoices-dir",
        default="upscaled-tl/TL-invoices",
        help="Directory containing TL invoice PDFs",
    )
    parser.add_argument(
        "--out",
        default="upscaled-tl/tl_invoices.csv",
        help="Output CSV path",
    )
    return parser.parse_args()


def find_project_root(start: str) -> Optional[str]:
    current = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(current, "01_SOURCING")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None


def resolve_path(path: str) -> str:
    if os.path.isabs(path):
        return path
    root = find_project_root(os.getcwd()) or find_project_root(os.path.dirname(__file__))
    if root:
        return os.path.join(root, path)
    return path


def to_float(value: str) -> float:
    try:
        return float(value.replace(",", "").strip())
    except ValueError:
        return 0.0


def extract_text(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def parse_invoice(text: str) -> dict:
    invoice = {
        "invoice_number": "",
        "invoice_date": "",
        "due_date": "",
        "order_ref": "",
        "customer_id": "",
        "total_due": "",
        "payments_applied": "",
        "status": "Unpaid",
    }
    if match := re.search(r"Invoice #:\s*([A-Z0-9-]+)", text):
        invoice["invoice_number"] = match.group(1).strip()
    if match := re.search(r"Invoice Date:\s*(\d{2}/\d{2}/\d{4})", text):
        invoice["invoice_date"] = match.group(1).strip()
    if match := re.search(r"Due Date:\s*(\d{2}/\d{2}/\d{4})", text):
        invoice["due_date"] = match.group(1).strip()
    if match := re.search(r"Order Ref:\s*([^\n]+)", text):
        invoice["order_ref"] = match.group(1).strip()
    if match := re.search(r"Customer Id:\s*([A-Z0-9-]+)", text):
        invoice["customer_id"] = match.group(1).strip()
    if match := re.search(r"Payments/Credits Applied\s*\$-?([\d,\.]+)", text):
        invoice["payments_applied"] = match.group(1).strip()
    if match := re.search(r"Total Due:\s*\$?([\d,\.]+)", text):
        invoice["total_due"] = match.group(1).strip()

    total_due = to_float(invoice["total_due"])
    payments = to_float(invoice["payments_applied"])
    if total_due <= 0.01:
        invoice["status"] = "Paid"
    elif payments > 0:
        invoice["status"] = "Partially Paid"
    return invoice


def main() -> int:
    args = parse_args()
    invoices_dir = Path(resolve_path(args.invoices_dir))
    out_path = Path(resolve_path(args.out))
    out_path.parent.mkdir(parents=True, exist_ok=True)

    rows = [
        [
            "Invoice Number",
            "Order Ref",
            "Customer ID",
            "Invoice Date",
            "Due Date",
            "Total Due",
            "Payments Applied",
            "Status",
            "Source File",
            "Payments Applied (Raw)",
        ]
    ]

    for path in sorted(invoices_dir.glob("*.pdf")):
        text = extract_text(path)
        invoice = parse_invoice(text)
        rows.append(
            [
                invoice["invoice_number"],
                invoice["order_ref"],
                invoice["customer_id"],
                invoice["invoice_date"],
                invoice["due_date"],
                invoice["total_due"],
                invoice["payments_applied"],
                invoice["status"],
                path.name,
                invoice["payments_applied"],
            ]
        )

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    print(f"Wrote {len(rows) - 1} invoices to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

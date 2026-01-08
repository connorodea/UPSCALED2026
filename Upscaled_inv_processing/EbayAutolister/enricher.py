#!/usr/bin/env python3
"""
CSV enricher for product metadata via OpenAI web search.
Adds title, retail/used prices, source URL, confidence, and downloads a stock image per row.
"""

import json
import logging
import os
import time
from typing import Any, Dict, Optional, Union

import pandas as pd
import requests
from openai import OpenAI
from urllib.parse import urlparse

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")
RATE_LIMIT_SECONDS = float(os.getenv("OPENAI_RATE_LIMIT_SECONDS", "1.2"))


class EnrichmentError(Exception):
    """Raised when enrichment fails for a row."""


def _infer_extension(url: str) -> str:
    try:
        path = urlparse(url).path
        ext = path.split(".")[-1].lower()
        if ext in {"jpg", "jpeg", "png", "webp"}:
            return f".{ext}"
    except Exception:
        pass
    return ".jpg"


def _download_image(url: str, dest_dir: str, base_name: str) -> Optional[str]:
    if not url:
        return None

    os.makedirs(dest_dir, exist_ok=True)
    ext = _infer_extension(url)
    filename = base_name.replace(" ", "_") + ext
    filepath = os.path.join(dest_dir, filename)

    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(response.content)
            return filename
    except Exception as exc:
        logging.warning("Image download failed for %s: %s", url, exc)

    return None


def _clean_price(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("$", "").replace(",", "")
    if not text:
        return None
    try:
        return float(text.split()[0])
    except ValueError:
        return None


def _get_cell(row: pd.Series, col: Union[int, str]) -> str:
    try:
        return str(row[col]).strip()
    except Exception:
        return ""


def query_openai_search(client: OpenAI, brand: str, model: str) -> Dict[str, Any]:
    query = f"{brand} {model}".strip()
    if not query:
        raise EnrichmentError("Brand/model missing")

    prompt = f"""
You are a product data agent. Search the web and return structured data for "{query}".
Return ONLY valid JSON with fields:
{{
  "title": "",
  "retail_price": "",
  "used_price_low": "",
  "used_price_high": "",
  "best_image_url": "",
  "source_url": "",
  "confidence": 0
}}
If you cannot find data, leave fields blank.
"""

    try:
        completion = client.responses.create(
            model=DEFAULT_MODEL,
            input=prompt,
            tools=[{"type": "web_search", "recency_days": 365}],
            max_output_tokens=600,
        )
    except Exception as exc:
        raise EnrichmentError(f"OpenAI request failed: {exc}") from exc

    raw_text = getattr(completion, "output_text", "") or ""
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise EnrichmentError(f"Invalid JSON from model: {raw_text[:200]}") from exc


def enrich_csv(
    input_csv: str,
    output_csv: str,
    images_dir: str,
    id_col: Union[int, str],
    brand_col: Union[int, str],
    model_col: Union[int, str],
) -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnrichmentError("OPENAI_API_KEY is not set")

    client = OpenAI(api_key=api_key)
    df = pd.read_csv(input_csv, dtype=str, keep_default_na=False)

    # Ensure columns exist
    for col in [
        "title",
        "retail_price",
        "used_price_low",
        "used_price_high",
        "source_url",
        "confidence",
        "image_filename",
        "price_40pct",
    ]:
        if col not in df.columns:
            df[col] = ""

    for idx, row in df.iterrows():
        brand = _get_cell(row, brand_col)
        model = _get_cell(row, model_col)
        item_id = _get_cell(row, id_col) or f"row_{idx}"

        if not brand and not model:
            logging.warning("Skipping row %s: missing brand/model", idx)
            continue

        try:
            result = query_openai_search(client, brand, model)
        except EnrichmentError as exc:
            logging.warning("[WARN] Row %s (%s %s) failed: %s", idx, brand, model, exc)
            continue

        df.at[idx, "title"] = result.get("title", "")
        df.at[idx, "retail_price"] = result.get("retail_price", "")
        df.at[idx, "used_price_low"] = result.get("used_price_low", "")
        df.at[idx, "used_price_high"] = result.get("used_price_high", "")
        df.at[idx, "source_url"] = result.get("source_url", "")
        df.at[idx, "confidence"] = result.get("confidence", "")

        retail_price = _clean_price(result.get("retail_price"))
        if retail_price is not None:
            df.at[idx, "price_40pct"] = f"{round(retail_price * 0.4, 2):.2f}"

        image_url = result.get("best_image_url", "")
        filename = _download_image(image_url, images_dir, item_id) if image_url else None
        if filename:
            df.at[idx, "image_filename"] = filename

        time.sleep(RATE_LIMIT_SECONDS)

    df.to_csv(output_csv, index=False)
    logging.info("Saved enriched CSV → %s", output_csv)
    logging.info("Images directory → %s", images_dir)


if __name__ == "__main__":
    enrich_csv(
        input_csv="B1.csv",
        output_csv="B1_enriched.csv",
        images_dir="product_images",
        id_col=0,
        brand_col=6,
        model_col=7,
    )

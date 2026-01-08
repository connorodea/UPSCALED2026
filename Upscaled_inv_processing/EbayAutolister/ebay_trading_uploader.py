#!/usr/bin/env python3
"""
eBay Trading API Uploader - XML-based listing creation
Uses the Trading API which is more stable than the Inventory API
"""

import requests
import logging
import time
import pandas as pd
from typing import Dict, List
from xml.etree import ElementTree as ET
import os
from dotenv import load_dotenv

load_dotenv()

class EbayTradingAPI:
    """eBay Trading API client using XML requests"""

    def __init__(self, dev_id: str, app_id: str, cert_id: str, auth_token: str, sandbox: bool = False):
        self.dev_id = dev_id
        self.app_id = app_id
        self.cert_id = cert_id
        self.auth_token = auth_token
        self.sandbox = sandbox

        # API endpoint
        self.api_url = "https://api.sandbox.ebay.com/ws/api.dll" if sandbox else "https://api.ebay.com/ws/api.dll"

        # Rate limiting
        self.last_request = 0
        self.min_interval = 0.5  # 500ms between requests for Trading API

        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    def _rate_limit(self):
        """Enforce rate limiting between API calls"""
        elapsed = time.time() - self.last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request = time.time()

    def _make_xml_request(self, call_name: str, xml_body: str) -> Dict:
        """Make Trading API XML request"""
        self._rate_limit()

        headers = {
            'X-EBAY-API-SITEID': '0',  # 0 = US
            'X-EBAY-API-COMPATIBILITY-LEVEL': '967',
            'X-EBAY-API-CALL-NAME': call_name,
            'X-EBAY-API-DEV-NAME': self.dev_id,
            'X-EBAY-API-APP-NAME': self.app_id,
            'X-EBAY-API-CERT-NAME': self.cert_id,
            'Content-Type': 'text/xml'
        }

        try:
            response = requests.post(self.api_url, headers=headers, data=xml_body)
            response.raise_for_status()
            return self._parse_xml_response(response.text)
        except Exception as e:
            self.logger.error(f"API request failed: {e}")
            if hasattr(response, 'text'):
                self.logger.error(f"Response: {response.text}")
            raise

    def _parse_xml_response(self, xml_text: str) -> Dict:
        """Parse XML response and extract key data"""
        try:
            root = ET.fromstring(xml_text)

            # Find namespace
            ns = {'ns': 'urn:ebay:apis:eBLBaseComponents'}

            result = {
                'Ack': root.find('.//ns:Ack', ns).text if root.find('.//ns:Ack', ns) is not None else None,
                'ItemID': root.find('.//ns:ItemID', ns).text if root.find('.//ns:ItemID', ns) is not None else None,
                'Errors': []
            }

            # Extract errors
            for error in root.findall('.//ns:Errors', ns):
                error_code = error.find('ns:ErrorCode', ns)
                short_msg = error.find('ns:ShortMessage', ns)
                long_msg = error.find('ns:LongMessage', ns)
                severity = error.find('ns:SeverityCode', ns)

                result['Errors'].append({
                    'ErrorCode': error_code.text if error_code is not None else None,
                    'ShortMessage': short_msg.text if short_msg is not None else None,
                    'LongMessage': long_msg.text if long_msg is not None else None,
                    'SeverityCode': severity.text if severity is not None else None
                })

            return result
        except Exception as e:
            self.logger.error(f"Failed to parse XML response: {e}")
            return {'Ack': 'Failure', 'Errors': [{'LongMessage': str(e)}]}

    def add_fixed_price_item(self, item_data: Dict) -> Dict:
        """
        Create a fixed-price listing using AddFixedPriceItem

        item_data should contain:
        - title: str
        - description: str
        - category_id: str
        - price: float
        - quantity: int
        - condition: str (e.g., '3000' for Used)
        - sku: str
        - fulfillment_policy_id: str
        - payment_policy_id: str
        - return_policy_id: str
        """

        # Map condition codes
        condition_map = {
            'NEW': '1000',
            'LIKE_NEW': '1500',
            'USED_EXCELLENT': '2500',
            'USED_VERY_GOOD': '2750',
            'USED_GOOD': '3000',
            'USED_ACCEPTABLE': '4000',
            'FOR_PARTS_OR_NOT_WORKING': '7000'
        }

        condition_id = condition_map.get(item_data.get('condition', 'USED_GOOD'), '3000')

        # Extract brand and model from item_data
        brand = self._escape_xml(item_data.get('brand', 'Samsung'))
        model = self._escape_xml(item_data.get('model', 'SM-R890'))

        # Determine case size based on model
        case_size = '46mm' if 'R890' in model or 'R895' in model else '40mm'

        xml_request = f'''<?xml version="1.0" encoding="utf-8"?>
<AddFixedPriceItemRequest xmlns="urn:ebay:apis:eBLBaseComponents">
    <RequesterCredentials>
        <eBayAuthToken>{self.auth_token}</eBayAuthToken>
    </RequesterCredentials>
    <Item>
        <Title>{self._escape_xml(item_data.get('title', 'Item'))}</Title>
        <Description><![CDATA[{item_data.get('description', '')}]]></Description>
        <PrimaryCategory>
            <CategoryID>{item_data.get('category_id', '178')}</CategoryID>
        </PrimaryCategory>
        <StartPrice>{item_data.get('price', 10.00)}</StartPrice>
        <CategoryMappingAllowed>true</CategoryMappingAllowed>
        <ConditionID>{condition_id}</ConditionID>
        <Country>US</Country>
        <Currency>USD</Currency>
        <DispatchTimeMax>3</DispatchTimeMax>
        <ListingDuration>GTC</ListingDuration>
        <ListingType>FixedPriceItem</ListingType>
        <Location>United States</Location>
        <Quantity>{item_data.get('quantity', 1)}</Quantity>
        <SKU>{self._escape_xml(item_data.get('sku', ''))}</SKU>
        <Site>US</Site>
        <ItemSpecifics>
            <NameValueList>
                <Name>Brand</Name>
                <Value>{brand}</Value>
            </NameValueList>
            <NameValueList>
                <Name>Model</Name>
                <Value>{model}</Value>
            </NameValueList>
            <NameValueList>
                <Name>Case Size</Name>
                <Value>{case_size}</Value>
            </NameValueList>
            <NameValueList>
                <Name>Band Material</Name>
                <Value>Silicone</Value>
            </NameValueList>
            <NameValueList>
                <Name>Compatible Operating System</Name>
                <Value>Wear OS</Value>
            </NameValueList>
        </ItemSpecifics>
        <PictureDetails>
            <GalleryType>Gallery</GalleryType>
            <PictureURL>https://i.ebayimg.com/images/g/placeholder/s-l500.jpg</PictureURL>
        </PictureDetails>
        <SellerProfiles>
            <SellerShippingProfile>
                <ShippingProfileID>{item_data.get('fulfillment_policy_id', '')}</ShippingProfileID>
            </SellerShippingProfile>
            <SellerReturnProfile>
                <ReturnProfileID>{item_data.get('return_policy_id', '')}</ReturnProfileID>
            </SellerReturnProfile>
            <SellerPaymentProfile>
                <PaymentProfileID>{item_data.get('payment_policy_id', '')}</PaymentProfileID>
            </SellerPaymentProfile>
        </SellerProfiles>
    </Item>
</AddFixedPriceItemRequest>'''

        self.logger.info(f"Creating listing for: {item_data.get('title')[:50]}...")
        return self._make_xml_request('AddFixedPriceItem', xml_request)

    def _escape_xml(self, text: str) -> str:
        """Escape XML special characters"""
        if not text:
            return ''
        text = str(text)
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&apos;')
        return text


def upload_from_csv(csv_path: str):
    """Upload items from enriched CSV to eBay using Trading API"""

    # Load environment variables
    dev_id = os.getenv('EBAY_DEV_ID')
    app_id = os.getenv('EBAY_CLIENT_ID')
    cert_id = os.getenv('EBAY_CLIENT_SECRET')
    auth_token = os.getenv('EBAY_AUTH_TOKEN')
    sandbox = os.getenv('EBAY_SANDBOX', 'false').lower() == 'true'

    fulfillment_policy = os.getenv('DEFAULT_FULFILLMENT_POLICY')
    payment_policy = os.getenv('DEFAULT_PAYMENT_POLICY')
    return_policy = os.getenv('DEFAULT_RETURN_POLICY')

    # Initialize API
    api = EbayTradingAPI(dev_id, app_id, cert_id, auth_token, sandbox)

    # Load CSV
    df = pd.read_csv(csv_path)

    results = {
        'success': [],
        'failed': [],
        'warnings': []
    }

    print(f"\n{'='*80}")
    print(f"Starting upload of {len(df)} items to eBay")
    print(f"{'='*80}\n")

    for idx, row in df.iterrows():
        try:
            # Get title - handle empty/NaN values
            title = row.get('title') if pd.notna(row.get('title')) else ''
            if not title:
                brand = row.get('brand') if pd.notna(row.get('brand')) else ''
                model = row.get('model') if pd.notna(row.get('model')) else ''
                title = f"{brand} {model}".strip()

            # Get description - use a basic one if missing
            description = row.get('description') if pd.notna(row.get('description')) else ''
            if not description:
                description = f"<h2>{title}</h2><p>Pre-owned {title} in good working condition.</p>"

            # Category ID - default to Smart Watches (178893) for Samsung watches
            category_id = row.get('category_id')
            if pd.isna(category_id) or category_id == 0.0:
                category_id = '178893'  # Smart Watches category
            else:
                category_id = str(int(float(category_id)))

            # Price - default to $100 for Samsung smartwatches if not set
            price = row.get('suggested_price')
            if pd.isna(price) or price == 0.0:
                price = row.get('market_price')
            if pd.isna(price) or price == 0.0:
                price = row.get('retail_price')
            if pd.isna(price) or price == 0.0:
                price = 100.00  # Default price for smartwatches
            else:
                price = float(price)

            # Map condition to eBay format
            condition = row.get('condition', 'USED_GOOD')
            if condition == 'LN':
                condition = 'LIKE_NEW'

            item_data = {
                'title': title,
                'description': description,
                'category_id': category_id,
                'price': price,
                'quantity': 1,
                'condition': condition,
                'sku': row.get('sku', ''),
                'brand': row.get('brand', 'Samsung'),
                'model': row.get('model', 'SM-R890'),
                'fulfillment_policy_id': fulfillment_policy,
                'payment_policy_id': payment_policy,
                'return_policy_id': return_policy
            }

            print(f"[{idx+1}/{len(df)}] Uploading: {item_data['title'][:60]}...")

            response = api.add_fixed_price_item(item_data)

            if response.get('Ack') in ['Success', 'Warning']:
                item_id = response.get('ItemID')
                print(f"  ✓ Success! Item ID: {item_id}")
                results['success'].append({
                    'sku': item_data['sku'],
                    'item_id': item_id,
                    'title': item_data['title']
                })

                # Log warnings if any
                if response.get('Errors'):
                    for error in response['Errors']:
                        if error.get('SeverityCode') == 'Warning':
                            print(f"  ⚠ Warning: {error.get('ShortMessage')}")
                            results['warnings'].append({
                                'sku': item_data['sku'],
                                'warning': error.get('ShortMessage')
                            })
            else:
                print(f"  ✗ Failed!")
                for error in response.get('Errors', []):
                    print(f"    Error: {error.get('LongMessage')}")
                results['failed'].append({
                    'sku': item_data['sku'],
                    'error': response.get('Errors', [{}])[0].get('LongMessage', 'Unknown error')
                })

        except Exception as e:
            print(f"  ✗ Exception: {e}")
            results['failed'].append({
                'sku': row.get('sku', 'unknown'),
                'error': str(e)
            })

    # Print summary
    print(f"\n{'='*80}")
    print(f"Upload Complete!")
    print(f"{'='*80}")
    print(f"✓ Successfully uploaded: {len(results['success'])} items")
    print(f"✗ Failed: {len(results['failed'])} items")
    print(f"⚠ Warnings: {len(results['warnings'])} items")
    print(f"{'='*80}\n")

    if results['success']:
        print("Successful listings:")
        for item in results['success']:
            print(f"  - {item['title'][:60]} (ID: {item['item_id']})")

    if results['failed']:
        print("\nFailed listings:")
        for item in results['failed']:
            print(f"  - SKU: {item['sku']}")
            print(f"    Error: {item['error']}")

    return results


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ebay_trading_uploader.py <enriched_csv_file>")
        sys.exit(1)

    csv_file = sys.argv[1]
    upload_from_csv(csv_file)

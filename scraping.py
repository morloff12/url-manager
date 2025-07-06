# scraping.py
import requests
import re

def scrape_product(title, url):
    try:
        response = requests.get(url, timeout=10)
        html = response.text

        # If no title, extract it
        if not title:
            match = re.search(r'<div class="field[^>]+field--name-field-web-description[^>]*">(.*?)</div>', html)
            if match:
                title = match.group(1).strip()

        # Detect sale price
        is_on_sale = bool(re.search(r'<div class="retail_price">.*?</div>', html))
        sale_match = re.search(r'<div class="promo_price">\s*(\$[\d.]+)\s*</div>', html)
        regular_match = re.search(r'<div class="retail_price">\s*(\$[\d.]+)\s*</div>', html)

        sale_price = sale_match.group(1) if sale_match else None
        regular_price = regular_match.group(1) if regular_match else sale_price

        return {
            "title": title,
            "url": url,
            "on_sale": is_on_sale,
            "sale_price": sale_price,
            "regular_price": regular_price
        }

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

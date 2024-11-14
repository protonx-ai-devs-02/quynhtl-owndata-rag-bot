import requests
import xml.etree.ElementTree as ET
import json

# URLs of the sitemaps
sitemap_urls = [
    'https://chewychewy.vn/sitemap_products_1.xml',
    'https://chewychewy.vn/sitemap_collections_1.xml',
]

all_urls = []

# Function to fetch and parse XML
def fetch_sitemap(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Check if the request was successful
        root = ET.fromstring(response.content)
        # Extract all <loc> elements that contain the URLs
        for url_element in root.iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc'):
            all_urls.append(url_element.text)
    except Exception as e:
        print(f"Error fetching or parsing {url}: {e}")

# Fetch and parse both sitemaps
for sitemap_url in sitemap_urls:
    fetch_sitemap(sitemap_url)

# Write the URLs to a JSON file
with open('json_file/chewychewy_all_urls.json', 'w') as f:
    json.dump(all_urls, f, indent=4)

print(f"Extracted {len(all_urls)} URLs and saved to all_urls.json")

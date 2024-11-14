import scrapy
from scrapy.crawler import CrawlerProcess
import json

# Load URLs from JSON file
filename = 'output_files/chewychewy_all_urls.json'
with open(filename, 'r') as file:
    all_urls = json.load(file)

class ChewyChewyCrawlerSpider(scrapy.Spider):
    name = "chewy_chewy_crawler"
    start_urls = [url for url in all_urls if "products" in url]
    # start_urls = product_urls

    def parse(self, response):
        # Extract product title
        title = response.css('meta[property="og:title"]::attr(content)').get(default="").strip()
        
        # Extract product image URL
        image_url = response.css('meta[property="og:image"]::attr(content)').get(default="").strip()
        
        # Extract product price (if available)
        price = response.css('meta[property="og:price:amount"]::attr(content)').get(default="").strip()
        currency = response.css('meta[property="og:price:currency"]::attr(content)').get(default="VND").strip()
        
        # Extract product description
        description = response.css('meta[property="og:description"]::attr(content)').get(default="").strip()

        # Collect data into a dictionary
        data = {
            "url": response.url,
            "title": title,
            "description": description,
            "price": f"{price} {currency}",
            "image_url": image_url,
        }

        yield data

        # Print log information
        self.logger.info(f"Crawled: {response.url}")
        self.logger.info(f"Title: {title}")
        self.logger.info(f"Price: {price} {currency}")
        self.logger.info(f"Image URL: {image_url}")
        self.logger.info(f"Description: {description}")

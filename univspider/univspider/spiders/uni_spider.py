import scrapy
import json
import os
import datetime
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

class UniversitySpider(scrapy.Spider):
    name = 'university'
    start_urls = [
        ("https://cs.uchicago.edu/mpcs", "University of Chicago"),
        ("https://gradschool.princeton.edu/academics/degrees-requirements/fields-study/computer-science", "Princeton University"),
        ("https://gradschool.cornell.edu/academics/fields-of-study/subject/computer-science/computer-science-ms-ithaca/", "Cornell University"),
        ("https://www.cs.columbia.edu/education/ms/", "Columbia University"),
        ("https://www.cs.jhu.edu/academic-programs/graduate-studies/mse-programs/", "Johns Hopkins University"),
        ("https://cse.engin.umich.edu/academics/graduate/", "University of Michigan"),
        ("https://www.cs.rochester.edu/graduate/masters-program.html", "University of Rochester"),
        ("https://college.harvard.edu/admissions", "Harvard University"),
        ("https://www.stanford.edu/admission/", "Stanford University"),
        ("https://www.ox.ac.uk/admissions/graduate","University of Oxford")
    ]
    max_depth_per_university = 2
    visited_urls = set()
    
    def start_requests(self):
        universities_arg = getattr(self, 'universities', None)
        universities_to_scrape = universities_arg.split(',') if universities_arg else None

        for idx, (url, university_name) in enumerate(self.start_urls, start=1):
            if universities_to_scrape is None or str(idx) in universities_to_scrape:
                filename = f'archivos_json/university_{idx}.json'
                if os.path.exists(filename):
                    os.remove(filename)
                yield scrapy.Request(url, meta={'id': idx, 'university_name': university_name, 'depth': 1}, callback=self.parse)
    
    def parse(self, response):
        university_id = response.meta['id']
        university_name = response.meta['university_name']
        
        title = response.css('h1::text').get()
        title = title.strip() if title else ''
        
        content = self.fetch_text_from_url(response.url)

        content = BeautifulSoup(content).text
        if content:
            item = {
                'id': university_id,
                'data': datetime.datetime.now().isoformat(),
                'url': response.url,
                'university_name': university_name,
                'title': title,
                'content': content
            }
            self.save_item(item, university_id)

        depth = response.meta.get('depth', 1)
        if depth < self.max_depth_per_university:
            links = response.css('a::attr(href)').getall()
            for link in links:
                if self.is_edu_link(link):
                    next_link = response.urljoin(link)
                    if next_link not in self.visited_urls:
                        self.visited_urls.add(next_link) 
                        yield response.follow(link, meta={'id': university_id, 'university_name': university_name, 'depth': depth + 1}, callback=self.parse)

    def fetch_text_from_url(self, url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            body = soup.find('body')
            if body:
                return self.clean_text(body.get_text(separator=' ', strip=True))
            else:
                return None
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def clean_text(self, text):
        cleaned_text = re.sub(r'\{\{.*?\}\}', '', text)
        cleaned_text = re.sub(r'\{\{.*?$', '', cleaned_text) 
        cleaned_text = re.sub(r'Add to GMail Close', '', cleaned_text)
        return cleaned_text.strip()

    def save_item(self, item, university_id):
        directory = 'archivos_json'
        if not os.path.exists(directory):
            os.makedirs(directory)
        filename = f'{directory}/university_{university_id}.json'
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                except json.decoder.JSONDecodeError:
                    data = []
        else:
            data = []
        data.append(item)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def closed(self, reason):
        for idx, _ in enumerate(self.start_urls, start=1):
            filename = f'archivos_json/university_{idx}.json'
            with open(filename, 'a', encoding='utf-8') as f:
                f.write("]")
        self.log('Spider closed.')
    
    def is_edu_link(self, link):
        pattern = r'^https?://(?:[a-zA-Z0-9-]+\.)+(?:edu)/?'
        return re.match(pattern, link)
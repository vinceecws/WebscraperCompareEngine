from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from re import sub
from collections import namedtuple
import textdistance
import time
import numpy as np

class GigamarketEngine():

    def __init__(self, driver_dir):
        self._product_tuple = namedtuple('Product', ['name', 'price', 'img', 'url', 'store'])
        chrome_options = Options()  
        chrome_options.add_argument("--headless")  
        self._driver = webdriver.Chrome(driver_dir, chrome_options=chrome_options)

    def transformSearchString(self, search_string):
        return search_string.replace(' ', '+')

    def getNumeric(self, non_numeric):
        return sub(r"\D", "", non_numeric)

    def scrollToBottom(self):
        lenOfPage = self._driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
        match = False
        while(match == False):
            lastCount = lenOfPage
            time.sleep(3)
            lenOfPage = self._driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
            if lastCount == lenOfPage:
                match = True

    def getPageSource(self):
        return self._driver.page_source

    def generateNewSearch(self, search_string, no_results=None):
        search_string = self.transformSearchString(search_string)
        target_products = self.searchTarget(search_string, no_results=no_results)
        amazon_products = self.searchAmazon(search_string, pages=2, no_results=no_results)
        all_pairs = self.generateAllMatches(target_products, [amazon_products])

        return all_pairs


    def searchTarget(self, search_string, no_results=None):
        #Get from Target 
        self._driver.get('https://www.target.com/s?searchTerm={}'.format(search_string))

        #TODO: Use a more reliable waitUntil
        self.scrollToBottom()
        content = self.getPageSource()
        soup = BeautifulSoup(content)
        products = []

        for product in soup.findAll('li', attrs={'class': 'Col-favj32-0 bkaXIn h-padding-a-none h-display-flex'}, limit=no_results): #TODO: search through ALL of findAll, assign textdistance to each result and get top N results
            name = product.find('a', attrs={'class': 'Link-sc-1khjl8b-0 styles__StyledTitleLink-e5kry1-5 lioQal h-display-block h-text-bold h-text-bs flex-grow-one'})
            price = product.find('span', attrs={'class': 'h-text-bs'})
            img = product.find('source')

            url = 'https://www.target.com' + name.get('href') if name else None
            name = name.getText() if name else None
            price = price.getText().replace('$', '') if price else None
            img = img.get('srcset') if img else None

            if (name, price):
                products.append(self._product_tuple(name, float(price), img, url, 'Target'))

        return products

    def searchAmazon(self, search_string, pages=None, no_results=None):
        products = []

        if not pages:
            pages = 1

        for page in range(1, pages + 1):
            #Get from Amazon 
            self._driver.get('https://www.amazon.com/s?k={}&page={}'.format(search_string, page))

            #TODO: Use a more reliable waitUntil
            time.sleep(5)
            content = self.getPageSource()
            soup = BeautifulSoup(content)

            for product in soup.findAll('div', attrs={'class': 'sg-col-inner'}, limit=no_results): #TODO: search through ALL of findAll, assign textdistance to each result and get top N results
                name = product.find('span', attrs={'class': 'a-size-base-plus a-color-base a-text-normal'})
                price_whole = product.find('span', attrs={'class': 'a-price-whole'})
                price_fraction = product.find('span', attrs={'class': 'a-price-fraction'})
                img = product.find('img', attrs={'class': 's-image'})
                url = product.find('a', attrs={'class': 'a-link-normal a-text-normal'})

                name = name.getText() if name else None
                price_whole = self.getNumeric(price_whole.getText()) if price_whole else None
                price_fraction = self.getNumeric(price_fraction.getText()) if price_fraction else None
                img = img.get('src') if img else None
                url = 'https://www.amazon.com' + url.get('href') if url else None

                if (name and price_whole and price_fraction):
                    products.append(self._product_tuple(name, float(price_whole) + (float(price_fraction) / 100), img, url, 'Amazon'))

        return products

    def generateSimilarityMatrix(self, primary, secondary, match=False):
        similarity = []
        for primary_product in primary:
            row = []
            primary_tokens = primary_product.name.split()
            for secondary_product in secondary:
                secondary_tokens = secondary_product.name.split()
                score1 = textdistance.jaccard(primary_tokens, secondary_tokens)
                score2 = textdistance.jaro_winkler(primary_product.name, secondary_product.name)
                row.append(score1 + score2)

            similarity.append(row)

        similarity = np.array(similarity)

        if match:
            matches = self.mostSimilarMatches(primary, secondary, similarity)
            return similarity, matches

        return similarity

    def mostSimilarMatches(self, primary, secondary, similarity):
        match_ind = np.argmax(similarity, axis=1)
        matches = []
        for ind, primary_product in enumerate(primary):
            matches.append(secondary[match_ind[ind]])

        return matches

    def generateAllMatches(self, primary_store, secondary_stores):
        all_matches = []
        all_matches.append(primary_store)
        for store in secondary_stores:
            similarity, matches = self.generateSimilarityMatrix(primary_store, store, match=True)
            all_matches.append(matches)

        all_pairs = []
        for matches in zip(*all_matches):
            all_pairs.append(matches)

        return all_pairs


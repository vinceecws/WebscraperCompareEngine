import argparse
from GigamarketEngine import GigamarketEngine

def main(args):
    driver_dir = '/Users/vincentchooi/desktop/webscrape/chromedriver'
    engine = GigamarketEngine(driver_dir)
    all_pairs = engine.generateNewSearch(args.search_string, no_results=args.no_results)
    for pair in all_pairs:
        print(pair)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("search_string", help="Product to search")
    parser.add_argument("--no_results", required=False, help="No. of results to compare")
    args = parser.parse_args()

    main(args)
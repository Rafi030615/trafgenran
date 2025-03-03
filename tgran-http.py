import requests
import numpy as np
from datetime import datetime
import pandas as pd
import argparse
import time
from concurrent.futures import ThreadPoolExecutor

class SourceIPAdapter(requests.adapters.HTTPAdapter):
    def __init__(self, source_address, **kwargs):
        self.source_address = source_address
        super(SourceIPAdapter, self).__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs['source_address'] = (self.source_address, 0)
        super(SourceIPAdapter, self).init_poolmanager(*args, **kwargs)

def zipf_mandelbrot(N, q, s):
    ranks = np.arange(1, N + 1)
    weights = (ranks + q) ** -s
    probabilities = weights / weights.sum()
    return probabilities

def log_to_log(data, filename='request_log_http.log'):
    with open(filename, mode='a') as file:
        file.write('\t'.join(map(str, data)) + '\n')

def make_request(url, results, session):
    start_time = datetime.now()
    try:
        response = session.get(url)
        end_time = datetime.now()
        rtt = (end_time - start_time).total_seconds() * 1000

        if rtt < 1:
            rtt = 1

        log_data = [url, start_time, end_time, rtt, 200]
        results.append(log_data)
        print(f"Request to {url} completed with status code: 200, RTT: {rtt:.6f} ms")
    except requests.exceptions.RequestException as e:
        end_time = datetime.now()
        rtt = (end_time - start_time).total_seconds() * 1000
        if rtt < 1:
            rtt = 1
        log_data = [url, start_time, end_time, rtt, f"Failed: {e}"]
        results.append(log_data)
        print(f"Request to {url} failed: {e}, RTT: {rtt:.6f} ms")
    
    log_to_log(log_data)

def generate_traffic(urls, num_requests, requests_per_second, zipf_params, session):
    probabilities = zipf_mandelbrot(len(urls), *zipf_params)
    results = []
    executor = ThreadPoolExecutor(max_workers=100)
    
    for _ in range(num_requests):
        url = np.random.choice(urls, p=probabilities)
        executor.submit(make_request, url, results, session)
        time.sleep(1 / requests_per_second)

    executor.shutdown(wait=True)
    return results

def calculate_totals_and_averages(results):
    if not results:
        print("No results to calculate totals and averages.")
        return ["Total", "", "", 0, ""], ["Average", "", "", 0, ""]
    
    total_rtt = sum(result[3] for result in results)
    average_rtt = total_rtt / len(results)
    
    total_data = ["Total", "", "", total_rtt, ""]
    average_data = ["Average", "", "", average_rtt, ""]
    
    return total_data, average_data

def main():
    print("############ Tunggu Sebentar ############")
    
    parser = argparse.ArgumentParser(description='Generate traffic for URLs with Zipf distribution.')
    parser.add_argument('-url', type=int, required=True, help='Number of URLs')
    parser.add_argument('-req', type=int, required=True, help='Number of requests')
    parser.add_argument('-rps', type=float, required=True, help='Requests per second')
    parser.add_argument('-zipf', type=float, nargs=2, required=True, help='Zipf parameters: q and s')
    
    args = parser.parse_args()

    number_of_requests = args.req
    requests_per_second = args.rps
    zipf_params = tuple(args.zipf)

    df = pd.read_csv('url_bineca_http.csv')
    urls = df['URL'].tolist()
    
    with open('request_log_http.log', mode='w') as file:
        file.write("URL\tStart Time\tEnd Time\tRTT (ms)\tStatus Code\n")
    
    source_ip = '10.60.0.3'
    session = requests.Session()
    session.mount('http://', SourceIPAdapter(source_ip))
    
    results = generate_traffic(urls, number_of_requests, requests_per_second, zipf_params, session)
    
    total_data, average_data = calculate_totals_and_averages(results)
    
    with open('request_log_http.log', mode='a') as file:
        file.write('\t'.join(map(str, total_data)) + '\n')
        file.write('\t'.join(map(str, average_data)) + '\n')
    
    print(f"Total RTT: {total_data[3]:.2f} ms")
    print(f"Average RTT: {average_data[3]:.2f} ms")

if __name__ == "__main__":
    main()

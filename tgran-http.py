import os
import requests
import numpy as np
from datetime import datetime
import pandas as pd
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

def generate_traffic(urls, num_requests, requests_per_second, zipf_params, source_ips):
    probabilities = zipf_mandelbrot(len(urls), *zipf_params)
    results = []
    executor = ThreadPoolExecutor(max_workers=100)
    sessions = [requests.Session() for _ in source_ips]
    for session, ip in zip(sessions, source_ips):
        session.mount('http://', SourceIPAdapter(ip))
    
    for i in range(num_requests):
        url = np.random.choice(urls, p=probabilities)
        session = np.random.choice(sessions)  # Pilih session secara acak dari IP yang tersedia
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

def list_csv_files():
    files = [f for f in os.listdir() if f.endswith('.csv')]
    if not files:
        print("Tidak ada file CSV yang tersedia!")
        exit()
    
    print("\n===== Pilih CSV File =====")
    for idx, file in enumerate(files):
        print(f"{idx + 1}. {file}")

    while True:
        try:
            choice = int(input("\nMasukkan nomor file yang ingin digunakan: ")) - 1
            if 0 <= choice < len(files):
                return files[choice]
            else:
                print("Nomor tidak valid, coba lagi.")
        except ValueError:
            print("Input harus berupa angka!")

def main():
    print("############ Tunggu Sebentar ############")

    csv_file = list_csv_files()
    print(f"\nFile yang dipilih: {csv_file}")

    df = pd.read_csv(csv_file)
    urls = df['URL'].tolist()
    
    with open('request_log_http.log', mode='w') as file:
        file.write("URL\tStart Time\tEnd Time\tRTT (ms)\tStatus Code\n")

    print("\n===== Masukkan Parameter Traffic =====")
    num_urls = int(input("Jumlah URL yang akan digunakan (-url): "))
    num_requests = int(input("Jumlah total request (-req): "))
    requests_per_second = float(input("Jumlah request per detik (-rps): "))
    zipf_q = float(input("Zipf parameter q (-zipf q): "))
    zipf_s = float(input("Zipf parameter s (-zipf s): "))
    source_ips = input("Masukkan Source IPs (pisahkan dengan koma, contoh: 192.168.1.1,192.168.1.2): ").split(',')

    results = generate_traffic(urls[:num_urls], num_requests, requests_per_second, (zipf_q, zipf_s), source_ips)
    
    total_data, average_data = calculate_totals_and_averages(results)
    
    with open('request_log_http.log', mode='a') as file:
        file.write('\t'.join(map(str, total_data)) + '\n')
        file.write('\t'.join(map(str, average_data)) + '\n')
    
    print(f"\nTotal RTT: {total_data[3]:.2f} ms")
    print(f"Average RTT: {average_data[3]:.2f} ms")

if __name__ == "__main__":
    main()

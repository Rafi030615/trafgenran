import os
import requests
import numpy as np
from datetime import datetime
import pandas as pd
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin
import re

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

def extract_links(html, base_url):
    pattern = r'<img[^>]+src=["\'](.*?)["\']|<script[^>]+src=["\'](.*?)["\']|<link[^>]+href=["\'](.*?)["\']'
    matches = re.findall(pattern, html, re.IGNORECASE)
    links = set()
    for match in matches:
        for link in match:
            if link:
                absolute_link = urljoin(base_url, link)
                links.add(absolute_link)
    return links

def fetch_url(session, url):
    try:
        response = session.get(url, timeout=5)
        return len(response.content), response.status_code
    except requests.exceptions.RequestException:
        return 0, None

def make_request(url, results, session):
    start_time = datetime.now()
    try:
        rtt_start = time.time()
        response = session.get(url, timeout=5)
        rtt = (time.time() - rtt_start) * 1000
        html = response.text
        status_code = response.status_code
        end_time = datetime.now()
        
        links = extract_links(html, url)
        total_size = len(response.content)

        fetch_start = time.time()
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_url = {executor.submit(fetch_url, session, link): link for link in links}
            for future in as_completed(future_to_url):
                size, _ = future.result()
                total_size += size
        fetch_time = time.time() - fetch_start

        throughput = (total_size / 1024) / fetch_time if fetch_time > 0 else 0

        log_data = [url, start_time, end_time, round(rtt, 2), status_code, round(total_size / 1024, 2), round(throughput, 2)]
        results.append(log_data)

        print(f"✅ {url} | RTT: {rtt:.2f} ms | Size: {total_size/1024:.2f} KB | Throughput: {throughput:.2f} KB/s")

    except requests.exceptions.RequestException as e:
        end_time = datetime.now()
        rtt = (end_time - start_time).total_seconds() * 1000
        log_data = [url, start_time, end_time, round(rtt, 2), f"Failed: {e}", 0, 0]
        results.append(log_data)
        print(f"❌ {url} failed: {e} | RTT: {rtt:.2f} ms")
    
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
        session = np.random.choice(sessions)
        executor.submit(make_request, url, results, session)
        time.sleep(1 / requests_per_second)

    executor.shutdown(wait=True)
    return results

def calculate_totals_and_averages(results):
    if not results:
        print("No results to calculate.")
        return ["Total", "", "", 0, "", 0, 0], ["Average", "", "", 0, "", 0, 0]
    
    total_rtt = sum(r[3] for r in results if isinstance(r[3], (int, float)))
    total_size = sum(r[5] for r in results if isinstance(r[5], (int, float)))
    total_throughput = sum(r[6] for r in results if isinstance(r[6], (int, float)))
    count = len(results)

    avg_rtt = total_rtt / count
    avg_size = total_size / count
    avg_throughput = total_throughput / count

    total_data = ["Total", "", "", round(total_rtt, 2), "", round(total_size, 2), round(total_throughput, 2)]
    average_data = ["Average", "", "", round(avg_rtt, 2), "", round(avg_size, 2), round(avg_throughput, 2)]

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
        file.write("URL\tStart Time\tEnd Time\tRTT (ms)\tStatus Code\tTotal Size (KB)\tThroughput (KB/s)\n")

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
    
    print(f"\n📊 Total RTT: {total_data[3]:.2f} ms")
    print(f"📦 Total Size: {total_data[5]:.2f} KB")
    print(f"🚀 Total Throughput: {total_data[6]:.2f} KB/s")
    print(f"⚡ Rata-rata RTT: {average_data[3]:.2f} ms")
    print(f"📦 Rata-rata Size: {average_data[5]:.2f} KB")
    print(f"🚀 Rata-rata Throughput: {average_data[6]:.2f} KB/s")

if __name__ == "__main__":
    main()

import requests
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin
import re

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'

class SourceIPAdapter(HTTPAdapter):
    def __init__(self, source_address, **kwargs):
        self.source_address = source_address
        super(SourceIPAdapter, self).__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs['source_address'] = (self.source_address, 0)
        return super(SourceIPAdapter, self).init_poolmanager(*args, **kwargs)

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

def measure_performance_once(session, url):
    try:
        start_rtt = time.time()
        response = session.get(url, timeout=5)
        rtt = (time.time() - start_rtt) * 1000
        status_code = response.status_code
    except requests.exceptions.RequestException as e:
        print(f"💥 Error request: {e}")
        return None

    links = extract_links(response.text, url)
    total_size = len(response.content)

    start_fetch = time.time()
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(fetch_url, session, link): link for link in links}
        for future in as_completed(future_to_url):
            size, _ = future.result()
            total_size += size
    fetch_time = time.time() - start_fetch

    throughput = (total_size / 1024) / fetch_time if fetch_time > 0 else 0
    latency = fetch_time * 1000

    return {
        'rtt': rtt,
        'total_size_kb': total_size / 1024,
        'throughput_kbps': throughput,
        'latency_ms': latency,
        'status_code': status_code
    }

def measure_multiple_requests(url, source_ip, num_requests=10):
    session = requests.Session()
    session.mount('http://', SourceIPAdapter(source_ip))
    session.mount('https://', SourceIPAdapter(source_ip))
    session.headers.update({'User-Agent': USER_AGENT})

    results = []
    with ThreadPoolExecutor(max_workers=num_requests) as executor:
        futures = [executor.submit(measure_performance_once, session, url) for _ in range(num_requests)]
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    avg_rtt = sum(r['rtt'] for r in results) / len(results)
    avg_size = sum(r['total_size_kb'] for r in results) / len(results)
    avg_throughput = sum(r['throughput_kbps'] for r in results) / len(results)
    avg_latency = sum(r['latency_ms'] for r in results) / len(results)

    print(f"\n🔥 Total Request: {len(results)}")
    print(f"⚡ Rata-rata RTT: {avg_rtt:.2f} ms")
    print(f"📦 Rata-rata Size: {avg_size:.2f} KB")
    print(f"🚀 Rata-rata Throughput: {avg_throughput:.2f} KB/s")
    print(f"⏱️ Rata-rata Latency: {avg_latency:.2f} ms")

if __name__ == "__main__":
    url = 'http://testasp.vulnweb.com/'
    source_ip = '10.60.0.3'
    measure_multiple_requests(url, source_ip, num_requests=10)

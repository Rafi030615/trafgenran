import os
import sys
import requests
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse
import re
import subprocess

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

def measure_performance(url, source_ip):
    session = requests.Session()
    session.mount('http://', SourceIPAdapter(source_ip))
    session.mount('https://', SourceIPAdapter(source_ip))

    start_rtt = time.time()
    try:
        response = session.get(url, timeout=5)
        rtt = (time.time() - start_rtt) * 1000  # ms
        status_code = response.status_code
        print(f"⚡ Status Code: {status_code}")
        print(f"🕒 RTT (initial request only): {rtt:.2f} ms")
    except requests.exceptions.RequestException as e:
        print(f"💥 Error saat RTT: {e}")
        return

    links = extract_links(response.text, url)
    total_size = len(response.content)

    start_fetch = time.time()
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_url = {executor.submit(fetch_url, session, link): link for link in links}
        for future in as_completed(future_to_url):
            size, _ = future.result()
            total_size += size
    fetch_time = time.time() - start_fetch

    throughput = (total_size / 1024) / fetch_time if fetch_time > 0 else 0  # KB/s
    latency = fetch_time * 1000  # ms

    print(f"📦 Total Content Size: {total_size / 1024:.2f} KB")
    print(f"🚀 Throughput: {throughput:.2f} KB/s")
    print(f"⏱️ Latency (full fetch): {latency:.2f} ms")

def run_in_namespace(namespace, script_path):
    """Jalankan ulang script ini di dalam network namespace yang dipilih."""
    print(f"🔄 Menjalankan ulang dalam namespace: {namespace}")
    os.execvp("ip", ["ip", "netns", "exec", namespace, "python3", script_path])

if __name__ == "__main__":
    # Set network namespace & source IP yang sesuai
    namespace = "ue1"
    source_ip = "10.60.0.3"
    
    # Cek apakah script sudah berjalan di dalam netns yang benar
    current_netns = subprocess.getoutput("cat /proc/self/ns/net")
    netns_list = subprocess.getoutput("ls /var/run/netns").split("\n")

    if namespace in netns_list:
        netns_path = subprocess.getoutput(f"stat -c %i /var/run/netns/{namespace}")
        if netns_path not in current_netns:
            run_in_namespace(namespace, sys.argv[0])

    # URL target
    url = 'http://testasp.vulnweb.com/'
    
    # Jalankan pengukuran performa
    measure_performance(url, source_ip)

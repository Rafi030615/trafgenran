import socket
import time
import random
import string

def generate_random_payload(size):
    """Generate random payload of given size in bytes."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=size)).encode()

def send_udp_packets(target_ip, target_port, packet_size=512, packet_count=1000, delay=0, source_ip=None):
    """
    Sends UDP packets to a target IP and port with optional source IP/interface.
    
    :param target_ip: Target destination IP
    :param target_port: Target destination port
    :param packet_size: Size of each UDP packet in bytes
    :param packet_count: Number of packets to send
    :param delay: Delay between packets (in seconds)
    :param source_ip: Optional. Bind to this source IP/interface
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Bind to a specific source IP/interface if provided
    if source_ip:
        try:
            sock.bind((source_ip, 0))  # 0 = auto port
            print(f"🔌 Bound to source IP/interface: {source_ip}")
        except Exception as e:
            print(f"❌ Failed to bind to source IP {source_ip}: {e}")
            return

    payload = generate_random_payload(packet_size)
    sent = 0
    start_time = time.time()

    print(f"🚀 Sending {packet_count} UDP packets of {packet_size} bytes to {target_ip}:{target_port}...")
    
    for _ in range(packet_count):
        try:
            sock.sendto(payload, (target_ip, target_port))
            sent += 1
            if delay > 0:
                time.sleep(delay)
        except Exception as e:
            print(f"⚠️  Failed to send UDP packet: {e}")

    elapsed = time.time() - start_time
    print(f"\n✅ Sent {sent} packets in {elapsed:.2f} seconds.")
    print(f"📊 Throughput: {((sent * packet_size) / 1024) / elapsed:.2f} KB/s")

if __name__ == "__main__":
    # === Konfigurasi ===
    target_ip = "192.168.1.100"     # Ganti dengan IP tujuan
    target_port = 9999              # Ganti dengan port tujuan
    packet_size = 512               # Ukuran per paket (bytes)
    packet_count = 1000             # Jumlah paket
    delay_between_packets = 0       # Delay antar paket (0 = kirim secepatnya)
    source_ip = "192.168.1.50"      # IP lokal (interface) yang digunakan sebagai sumber

    # Jalankan fungsi
    send_udp_packets(
        target_ip=target_ip,
        target_port=target_port,
        packet_size=packet_size,
        packet_count=packet_count,
        delay=delay_between_packets,
        source_ip=source_ip
    )

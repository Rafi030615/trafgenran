import pandas as pd

def generate_csv(ip_address, filename):
    data = {"URL": [f"http://{ip_address}/index{i}.html" for i in range(1, 101)]}
    df = pd.DataFrame(data)
    df.to_csv(filename, index_label="Index")
    print(f"File '{filename}' berhasil dibuat dengan IP: {ip_address}")

# Input dari user
ip_user = input("Input IP: ")
csv_name = input("CSV File Name (with .csv): ")

generate_csv(ip_user, csv_name)

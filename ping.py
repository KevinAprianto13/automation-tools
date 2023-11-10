import json
import subprocess
import time
import urllib.request

def cek_koneksi_internet():
    try:
        urllib.request.urlopen('http://www.google.com', timeout=1)
        return True
    except urllib.request.URLError:
        return False

if cek_koneksi_internet():
    print("Ada koneksi internet.")
    # Jalankan logika utama Anda di sini
else:
    print("Tidak ada koneksi internet.")

# Fungsi untuk membaca alamat IP dari file JSON
def baca_alamat_ip(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

# Fungsi untuk melakukan ping ke alamat IP dan mengembalikan hasilnya
def cek_ping(ip):
    try:
        result = subprocess.run(['ping', '-c', '3', ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
        if "3 packets transmitted, 3 received, 0% packet loss" in result.stdout:
            return True
        else:
            return False
    except subprocess.TimeoutExpired:
        print("Ping timeout expired.")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

# Fungsi untuk memantau alamat IP dari file JSON
def monitor_ip(file_path):
    alamat_ip = baca_alamat_ip(file_path)
    status_devices = {}  # Dictionary untuk menyimpan status setiap perangkat
    while True:
        for device in alamat_ip:
            ip_address = device.get("ip_addresses", [])[0]
            device_name = device.get("name", "Unknown Device")
            status = cek_ping(ip_address)

            # Periksa apakah alamat IP berada dalam dictionary status_devices
            if ip_address not in status_devices:
                # Jika tidak ada, inisialisasi dictionary untuk alamat IP tersebut
                status_devices[ip_address] = {
                    "name": device_name,
                    "status": None,
                    "uptime": None
                }

            if status:
                # Jika alamat IP sebelumnya dalam status "down", catat waktu uptime
                if status_devices[ip_address]["status"] == "down":
                    status_devices[ip_address]["uptime"] = time.time()
                status_devices[ip_address]["status"] = "up"
            else:
                # Jika alamat IP sebelumnya dalam status "up", catat waktu downtime
                if status_devices[ip_address]["status"] == "up":
                    status_devices[ip_address]["uptime"] = None
                status_devices[ip_address]["status"] = "down"

            print(f"Device {status_devices[ip_address]['name']} with IP address {ip_address} is {status_devices[ip_address]['status']}.")

        time.sleep(10)  # Periksa setiap 10 detik

# Main function
if __name__ == "__main__":
    file_path = "data.json"  # Ganti dengan lokasi file JSON Anda

    monitor_ip(file_path)

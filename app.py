from flask import Flask, render_template, request, redirect, url_for, jsonify, session, make_response
import json
import subprocess
import time
import urllib.request
import uuid
import datetime
import speedtest
import io
import sys
import concurrent.futures
import paramiko
import routeros_api
from scapy.all import *






app = Flask(__name__, static_url_path='/static', static_folder='static')
app.secret_key = 'your_secret_key'

output_buffer = io.StringIO()
sys.stdout = output_buffer

def load_data():
    try:
        with open("data.json", "r") as file:
            data = json.load(file)
    except FileNotFoundError:
        data = []
    return data

def write_data(data):
    with open("data.json", "w") as file:
        json.dump(data, file, indent=4)

def monitor_ip(file_path):
    alamat_ip = load_data()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        while True:
            futures = {executor.submit(cek_ping_async, device.get("ip_addresses", [])[0]): device for device in alamat_ip}
            for future in concurrent.futures.as_completed(futures):
                device = futures[future]
                ip_address = device.get("ip_addresses", [])[0]
                device_name = device.get("name", "Unknown Device")
                try:
                    status = future.result()
                    log_downtime(file_path, ip_address, device_name, status)
                    sys.stdout.write(f"Device {device_name} with IP address {ip_address} is {'up' if status else 'down'}.\n")
                    sys.stdout.flush()
                except Exception as e:
                    print(f"Error occurred: {e}")
                time.sleep(10)

# Konstanta untuk menentukan durasi minimum downtime yang akan dicatat (dalam detik)
MINIMUM_DOWNTIME_DURATION = 60  # Contoh: 1 menit

def log_downtime(file_path, ip_address, device_name, status):
    try:
        log_data = json.load(open(file_path, "r"))
    except FileNotFoundError:
        log_data = []

    current_time = int(time.time())
    formatted_current_time = format_datetime(current_time)

    if not status:
        if log_data and log_data[-1]["ip_address"] == ip_address and log_data[-1]["end_time"] == 0:
            # Update end_time of the last log entry
            log_data[-1]["end_time"] = current_time
            duration_seconds = log_data[-1]["end_time"] - log_data[-1]["start_time"]
            if duration_seconds < MINIMUM_DOWNTIME_DURATION:
                # Downtime terlalu singkat, gabungkan dengan entri sebelumnya
                log_data.pop()  # Hapus entri terakhir
                log_data[-1]["end_time"] = current_time
                duration_seconds = log_data[-1]["end_time"] - log_data[-1]["start_time"]
            hours, remainder = divmod(duration_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            log_data[-1]["duration"] = f"{int(hours)} jam {int(minutes)} menit {int(seconds)} detik"
        else:
            # Add a new log entry
            log_entry = {
                "ip_address": ip_address,
                "device_name": device_name,
                "start_time": current_time,
                "end_time": 0,
                "duration": 0,
                "date": formatted_current_time
            }
            log_data.append(log_entry)
        
        with open(file_path, "w") as log_file:
            json.dump(log_data, log_file, indent=4)



def format_datetime(timestamp):
    date_obj = datetime.fromtimestamp(timestamp)
    formatted_date = date_obj.strftime('%Y-%m-%d %H:%M:%S')
    return formatted_date



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


def cek_ping_async(ip):
    try:
        result = subprocess.run(['ping', '-c', '3', ip], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=5)
        if "3 packets transmitted, 3 received, 0% packet loss" in result.stdout:
            return True
        else:
            return False
    except subprocess.TimeoutExpired:
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

@app.route('/delete/<string:id>', methods=['DELETE'])
def delete_device(id):
    devices = load_data()
    device_to_delete = None
    for device in devices:
        if device["id"] == id:
            device_to_delete = device
            break
    if device_to_delete:
        devices.remove(device_to_delete)
        write_data(devices)
    return jsonify({"message": "Device deleted successfully"})

@app.route('/status')
def get_status():
    devices = load_data()
    status_devices = {}
    for device in devices:
        ip_address = device.get("ip_addresses", [])[0]
        device_name = device.get("name", "Unknown Device")
        status = cek_ping(ip_address)
        status_devices[ip_address] = {
            "name": device_name,
            "status": status
        }
        log_downtime("log.json", ip_address, device_name, status)
    return jsonify(status_devices)



@app.route('/')
def index():
    devices = load_data()
    try:
        with open("log.json", "r") as log_file:
            log_data = json.load(log_file)
    except FileNotFoundError:
        log_data = []
    return render_template('index.html', devices=devices, log_data=log_data)

@app.route('/add', methods=['POST'])
def add_device():
    ip_address = request.form['ip_address']
    name = request.form['name']
    new_device = {
        "id": str(uuid.uuid4()),
        "ip_addresses": [ip_address],
        "name": name
    }
    devices = load_data()
    devices.append(new_device)
    write_data(devices)
    return redirect(url_for('index'))

def test_bandwidth():
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        download_speed = st.download() / 1024 / 1024
        upload_speed = st.upload() / 1024 / 1024
        ping_latency = st.results.ping if st.results else None
        return download_speed, upload_speed, ping_latency
    except Exception as e:
        print(f"Error during speed test: {e}")
        return None, None, None

@app.route('/test_bandwidth')
def test_bandwidth_route():
    download_speed, upload_speed, ping_latency = test_bandwidth()
    return render_template('bandwidth_result.html', download_speed=download_speed, upload_speed=upload_speed, ping_latency=ping_latency)

testing = False
@app.route('/speedtest')
def speedtest_route():
    global testing
    if not testing:
        testing = True
        download_speed, upload_speed, ping_latency = test_bandwidth()
        testing = False
        return jsonify({
            "download_speed": download_speed,
            "upload_speed": upload_speed,
            "ping_latency": ping_latency
        })
    else:
        return jsonify({
            "message": "Pengujian sedang berlangsung. Tunggu hingga selesai."
        })

@app.route('/login_mikrotik')
def login_mikrotikog():
    return render_template('login_mikrotik.html')


# Route for handling the form submission
@app.route('/active_connection', methods=['GET', 'POST'])
def active_connection():
    if request.method == 'POST':
        # Handle POST request
        # Get form data
        host = request.form['host']
        username = request.form['username'] 
        password = request.form['password']

        # Store the connection details in session
        session['host'] = host
        session['username'] = username
        session['password'] = password

        # Establish connection to MikroTik
        connection = routeros_api.RouterOsApiPool(host, username=username, password=password, plaintext_login=True)
        api = connection.get_api()

         # Get the identity of the router
        identity = api.get_resource('/system/identity')
        router_identity = identity.get()[0]['name']


        # Define the path and retrieve the results
        list_ppp = api.get_resource('ppp/active/')
        show_ppp = list_ppp.get()

        # Close the connection
        connection.disconnect()

        return render_template('active_connection.html', show_ppp=show_ppp, router_identity=router_identity)
    else:
        # Handle GET request to display the Active Connection page
        # Check if the session data is available
        if 'host' in session and 'username' in session and 'password' in session:
            host = session['host']
            username = session['username']
            password = session['password']

            # Establish connection to MikroTik
            connection = routeros_api.RouterOsApiPool(host, username=username, password=password, plaintext_login=True)
            api = connection.get_api()

                     # Get the identity of the router
            identity = api.get_resource('/system/identity')
            router_identity = identity.get()[0]['name']
            # Define the path and retrieve the results

            list_ppp = api.get_resource('ppp/active/')
            show_ppp = list_ppp.get()

            # Close the connection
            connection.disconnect()

            return render_template('active_connection.html', show_ppp=show_ppp, router_identity=router_identity)

        # If session data is not available, redirect to login
        return redirect('/login_mikrotik')



# Route for handling the remote action
@app.route('/remote', methods=['POST'])
def remote():
    ip_address = request.form['ip_address']

    # Redirect the user to the modem administration page
    admin_url = f"http://{ip_address}/"  # Ganti dengan URL sesuai dengan modem Anda
    return redirect(admin_url)



# Route for displaying PPPoE results
@app.route('/management_pppoe')
def management_pppoe():
    # Retrieve connection details from session
    host = session['host']
    username = session['username']
    password = session['password']

    # Establish connection to MikroTik
    connection = routeros_api.RouterOsApiPool(host, username=username, password=password, plaintext_login=True)
    api = connection.get_api()

    identity = api.get_resource('/system/identity')
    router_identity = identity.get()[0]['name']

    # Get PPP/Secret data
    ppp = api.get_resource('/ppp/secret')
    show_ppp = ppp.get()

    # Get profile data
    profile = api.get_resource('/ppp/profile')
    show_profile = profile.get()

    # Close the connection
    connection.disconnect()

    # Render the result_pppoe.html template with the PPP/Secret data and profile data
    return render_template('management_pppoe.html', show_ppp=show_ppp, show_profile=show_profile, router_identity=router_identity)


# Route for disabling PPPoE
@app.route('/management_pppoe/disable_pppoe', methods=['POST'])
def disable_pppoe():
    pppoe_id = request.form['pppoe_id']

    # Retrieve connection details from session
    host = session['host']
    username = session['username']
    password = session['password']

    # Establish connection to MikroTik
    connection = routeros_api.RouterOsApiPool(host, username=username, password=password, plaintext_login=True)
    api = connection.get_api()

    # Get PPP/Secret data
    ppp = api.get_resource('/ppp/secret')
    ppp.set(id=pppoe_id, disabled="true")  # Menggunakan metode set untuk menonaktifkan PPPoE

    # Close the connection
    connection.disconnect()

    return redirect('/management_pppoe')


# Route for Enable PPPoE
@app.route('/management_pppoe/enable_pppoe', methods=['POST'])
def enable_pppoe():
    pppoe_id = request.form['pppoe_id']

    # Retrieve connection details from session
    host = session['host']
    username = session['username']
    password = session['password']

    # Establish connection to MikroTik
    connection = routeros_api.RouterOsApiPool(host, username=username, password=password, plaintext_login=True)
    api = connection.get_api()

    # Get PPP/Secret data
    ppp = api.get_resource('/ppp/secret')
    ppp.set(id=pppoe_id, disabled="false")  # Menggunakan metode set untuk mengaktifkan PPPoE

    # Close the connection
    connection.disconnect()

    return redirect('/management_pppoe')


# Route for logging out and clearing session data
@app.route('/logout')
def logout():
    # Clear session data
    session.clear()

    # Create a response and set cache-control header to no-cache
    response = make_response(redirect('/login_mikrotik'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # clear cache for stablitas router
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'

    return response

def run_traceroute(target, max_hops=30):
    hops = []
    try:
        for i in range(1, max_hops + 1):
            pkt = IP(dst=target, ttl=i) / ICMP()
            reply = sr1(pkt, verbose=0, timeout=1)
            if reply is None:
                hops.append("*")
            elif reply.type == 11:  # Response from an intermediate hop
                hops.append(reply.src)
            elif reply.type == 0:  # Response from the target host
                hops.append(reply.src)
                break
    except Exception as e:
        print(f"Error: {e}")
    return hops


@app.route('/traceroute', methods=['GET', 'POST'])
def traceroute():
    traceroute_result = []
    if request.method == 'POST':
        target_ip = request.form['target_ip']
        max_hops = 30  # Ganti dengan jumlah maksimal hop yang diinginkan
        traceroute_result = run_traceroute(target_ip, max_hops)
    return render_template('traceroute.html', traceroute_result=traceroute_result)

def ping_domain(domain):
    try:
        result = subprocess.run(['ping', '-c', '4', domain], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        output = result.stdout
        return output
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"

@app.route('/ping_result', methods=['GET', 'POST'])
def ping_result():
    result = None

    if request.method == 'POST':
        domain_to_ping = request.form.get('domain')
        result = ping_domain(domain_to_ping)

    return render_template('ping-result.html', result=result)

if __name__ == '__main__':
    app.run(host="10.10.10.4", port=8300, debug=True)

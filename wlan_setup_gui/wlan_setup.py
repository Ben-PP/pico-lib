import network
import socket
import gc
import time
from machine import Pin

def create_html(body: str, style: str):
    html = f"""
    <html>
        <head>
            <link rel="icon" href="data:,">
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                {style}
            </style>
        </head>
        <body>
            {body}
        </body>
    </html>
    """
    return html

def try_connect():
    style = """
    """
    body = f"""
    <h2>Connecting to network...</h2>
    """
    return create_html(body, style)

def password_page(ssid:str):
    print(ssid)
    style = """
    """
    body = f"""
    <h2>Connecting to {ssid}</h2>
    <form action="/connect" method="post" enctype="text/plain">
        <input type="hidden" id="ssid" name="ssid" value="{ssid}"
        <label for="pwd">Password:</label><br>
        <input type="password" id="pwd" name="pwd" value=""<br>
        <input type="submit" value="Connect">
    </form>
    """
    return create_html(body, style)

def set_up_page(networks):
    links = ''
    for net in networks:
        links = links + f"<a href=\"password?ssid={net}\">{net}</a>\n"

    style = """
    .dropbtn {
      background-color: #04AA6D;
      color: white;
      padding: 16px;
      font-size: 16px;
      border: none;
    }
    
    .dropdown {
      position: relative;
      display: inline-block;
    }
    
    .dropdown-content {
      display: none;
      position: absolute;
      background-color: #f1f1f1;
      min-width: 160px;
      box-shadow: 0px 8px 16px 0px rgba(0,0,0,0.2);
      z-index: 1;
    }
    
    .dropdown-content a {
      color: black;
      padding: 12px 16px;
      text-decoration: none;
      display: block;
    }
    
    .dropdown-content a:hover {background-color: #ddd}
    .dropdown:hover .dropdown-content {display: block}
    .dropdown:hover .dropbtn {background-color: #3e8e41;}
    """

    body =f"""
            <h1>Connect to your wlan</h1>
            <h3>Select a network from below</h3>
            <div class="dropdown">
                <button class="dropbtn">Networks</button>
                <div class="dropdown-content">
                    {links}
                </div>
            </div>"""
    return create_html(body, style)

def error_page():
    style = """
    """
    body = f"""
    <h2>Oops, something went wrong :(</h2>
    """
    return create_html(body, style)

def get_query_params(url: str):
    query_string = url.split("?")[1]
    query_string = query_string.split(" ")[0]
    param_strings = query_string.split("&")
    params: dict = {}
    for string in param_strings:
        key,value = string.split("=")
        params.update({key:value})
    return params

def get_post_content(request: list[str]):
    print(request)
    is_in_post = False
    key_value_pairs = []
    for line in request:
        if (line == ""):
            is_in_post = True
            continue
        if (is_in_post):
            key_value_pairs.append(line)
    print(key_value_pairs)
    params: dict = {}
    for pair in key_value_pairs:
        key,value = pair.split("=")
        params.update({key: value})
    print(params)
    return params

def connect(ap: network.WLAN, wlan: network.WLAN, ssid: str, password: str, sock: socket.socket):
    ap.active(False)
    wlan.active(True)
    print(f"ssid: '{ssid}'")
    print(f"password: '{password}'")
    wlan.connect(ssid,password)
    led = Pin('LED', Pin.OUT)
    max_wait = 10
    while max_wait > 0:
        led.value(1)
        time.sleep_ms(500)
        led.value(0)
        time.sleep_ms(500)
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        print('waiting for connection...')
    print(wlan.status())
    if wlan.status() != 3:
        wlan.active(False)
        ap.active(True)
        print("Failed to connect")
    else:
        sock.close()
        print('connected')
        status = wlan.ifconfig()
        print( 'ip = ' + str(status) )

def create_ap():
    ssid: str = 'pico_setup'
    password : str = 'pico2023'
    ap = network.WLAN(network.AP_IF)
    ap.config(essid=ssid, password=password)
    ap.active(True)
    while ap.active() == False:
      time.sleep(1)
      pass
    print('Connection is successful')
    print(ap.ifconfig())
    return ap

def wlan_setup():
    gc.collect()

    ap = create_ap()

    scanner = network.WLAN(network.STA_IF)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   #creating socket object
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    i = 0
    while i < 5:
        try:
            s.bind(('', 80))
            s.listen(5)
            i = 5
        except:
            i += 1
            time.sleep(1)

    while True:
        conn: socket.socket; addr:tuple
        conn, addr = s.accept()
        networks = scanner.scan() # list with tupples with 6 fields ssid, bssid, channel, RSSI, security, hidden
        request = bytes(conn.recv(1024)).decode("utf-8")
        request_lines = request.splitlines()
        print(f"Got a connection from {str(addr)}")
        resource = ""
        for line in request_lines:
            if (line.startswith("GET")):
                line = line.strip("GET ")
                resource = line.split(" ")[0]
            elif(line.startswith("POST")):
                line = line.strip("POST ")
                resource = line.split(" ")[0]
        print(f"resource:{resource}")

        if (resource.startswith("/password")):
           print("=========Give password================")
           params = get_query_params(resource)
           response = password_page(str(params.get('ssid')))
           conn.send(response)
        elif (resource.startswith("/connect")):
            print("=========connect================")
            print(request_lines)
            params: dict = get_post_content(request_lines)
            connect(ap, scanner, str(params.get("ssid")), str(params.get("pwd")), s)
            if (scanner.isconnected()):
                break

        elif (resource == "/"):
            print("=========home================")
            ssids = []
            for net in networks:
               print(net[0].decode())
               ssids.append(net[0].decode())
            response = set_up_page(ssids)
            conn.send(response)
        else:
            print(request)
            response = error_page()
            conn.send(response)
        conn.close()

if __name__ == "__main__":
  wlan_setup()
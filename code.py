import time
import board
import busio
import displayio
import terminalio
import wifi
import socketpool
import adafruit_requests
#import adafruit_sht4x
import adafruit_htu31d
from adafruit_display_text import label
from adafruit_bitmap_font import bitmap_font
import secrets
import digitalio
import ipaddress


UPDATE_INTERVAL = 60  # seconds

# --- Button setup ---
button = digitalio.DigitalInOut(board.D0)
button.switch_to_input(pull=digitalio.Pull.UP)
last_button_state = True  # assume not pressed

button_ip = digitalio.DigitalInOut(board.D2)  # middle button
button_ip.switch_to_input(pull=digitalio.Pull.DOWN)
sending_enabled = True   # or False, depending on desired startup state
last_button_ip_state = False
show_ip = False

button_brightness = digitalio.DigitalInOut(board.D1)
button_brightness.switch_to_input(pull=digitalio.Pull.DOWN)
last_button_brightness_state = False

brightness_levels = [1.0, 0.3, 0.01, 0.001, 0.0]
brightness_index = 0
board.DISPLAY.brightness = brightness_levels[brightness_index]

# --- Wi-Fi ---
print("Connecting to WiFi...")
wifi.radio.connect(secrets.secrets["ssid"], secrets.secrets["password"])
print("Connected to", secrets.secrets["ssid"])
print("IP address:", wifi.radio.ipv4_address)

# -- for Dashy --
def start_http_hello_server():
    print("Starting simple HTTP server on port 80...")
    pool = socketpool.SocketPool(wifi.radio)
    server = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
    server.setsockopt(pool.SOL_SOCKET, pool.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", 80))
    server.listen(1)
    server.settimeout(0.1)
    return server


# --- Start HTTP server for Dashy workaround ---
http_server = start_http_hello_server()

# --- HTTP Setup ---
pool = socketpool.SocketPool(wifi.radio)
requests = adafruit_requests.Session(pool)

# --- Display Setup ---
display = board.DISPLAY
display.rotation = 180
splash = displayio.Group()
display.root_group = splash

ROOM = secrets.secrets["sensor_room"]

IP_ADDR = str(wifi.radio.ipv4_address)

# Set background color
bg_bitmap = displayio.Bitmap(display.width, display.height, 1)
bg_palette = displayio.Palette(1)
bg_palette[0] = 0x001833  # Deep navy blue

bg_tile = displayio.TileGrid(bg_bitmap, pixel_shader=bg_palette)
splash.append(bg_tile)

font_large = bitmap_font.load_font("/fonts/LeagueSpartan-Bold-16.bdf")

MAIN_COLOR   = 0xE6F1FF  # soft white
ACCENT_COLOR = 0x00C8FF  # aqua

time_label = label.Label(font_large, text="--:-- AM", x=10, y=15, scale=1, color=ACCENT_COLOR)
date_label = label.Label(font_large, text="--/--", x=180, y=15, scale=1, color=ACCENT_COLOR)

# Draw subtle divider line
line_bitmap = displayio.Bitmap(display.width, 1, 1)
line_palette = displayio.Palette(1)
line_palette[0] = ACCENT_COLOR
div = displayio.TileGrid(line_bitmap, pixel_shader=line_palette, x=0, y=32)

temp_label = label.Label(
    font_large,
    text="--.-°F",
    scale=2,
    color=MAIN_COLOR
)
temp_label.anchor_point = (0.0, 0.5)
temp_label.anchored_position = (15, 57)

humid_label = label.Label(
    font_large,
    text="--.-%",
    scale=2,
    color=MAIN_COLOR
)
humid_label.anchor_point = (1.0, 0.5)
humid_label.anchored_position = (display.width - 10, 94)

MAIN_COLOR   = 0xE6F1FF  # soft white
ACCENT_COLOR = 0x00C8FF  # aqua
GOOD_COLOR   = 0x00FF66  # green (sending enabled)
BAD_COLOR    = 0xFF4444  # red (sending disabled)

# line_bitmap = displayio.Bitmap(display.width, 1, 1)
# line_palette = displayio.Palette(1)
# line_palette[0] = ACCENT_COLOR
div2 = displayio.TileGrid(line_bitmap, pixel_shader=line_palette, x=0, y=117)

status_label_label = label.Label(
    terminalio.FONT,
    text="Sending: ",
    x=10,
    y=127
)
status_label = label.Label(
    terminalio.FONT,
    text="ON",
    x=65,
    y=127,
    color=GOOD_COLOR
)

room_label = label.Label(terminalio.FONT, text=f"Room: {ROOM}", x=100, y=127, scale=1, color=MAIN_COLOR)

# Append in order (background already appended)
splash.append(time_label)
splash.append(date_label)
splash.append(div)
splash.append(temp_label)
splash.append(humid_label)
splash.append(div2)
splash.append(status_label_label)
splash.append(status_label)
splash.append(room_label)

# --- Sensor Setup ---
i2c = board.I2C()
# sht = adafruit_sht4x.SHT4x(i2c)
# sht.mode = adafruit_sht4x.Mode.NOHEAT_HIGHPRECISION

htu = adafruit_htu31d.HTU31D(i2c)

status_modes = ["room", "ip", "wifi"]
status_mode_index = 0


def get_wifi_bars():
    try:
        rssi = wifi.radio.ap_info.rssi
    except Exception:
        return "WiFi: ?"

    if rssi >= -55:
        bars = "████"
    elif rssi >= -70:
        bars = "███"
    elif rssi >= -80:
        bars = "██"
    else:
        bars = "█"
    return f"WiFi: {bars} {rssi} "


# --- Time Fetch ---
def update_time_from_server():
    try:
        response = requests.get(secrets.secrets["time_server"])
        data = response.json()[0]

        just_time = data["just_time"]
        am_pm = data["am_pm"]
        month = data["month"]
        day = data["day"]

        time_label.text = f"{just_time} {am_pm.upper()}"
        date_label.text = f"{month}{day}"

        response.close()
    except Exception as e:
        print("Error fetching time:", e)

# --- Influx Send ---
def send_to_influx(measurement: str, value: float, host: str, room: str):
    try:
        influx_url = secrets.secrets["influx_url"]
        token = secrets.secrets["influx_token"]
        org = secrets.secrets["influx_org"]
        bucket = secrets.secrets["influx_bucket"]
        url = f"{influx_url}/api/v2/write?org={org}&bucket={bucket}&precision=s"
        line = f"{measurement},host={host},room={room} value={value:.2f}"
        headers = {
            "Authorization": f"Token {token}",
            "Content-Type": "text/plain; charset=utf-8"
        }
        print(f"Sending to InfluxDB: {line}")
        response = requests.post(url, headers=headers, data=line)
        print("Status:", response.status_code)
        response.close()
    except Exception as e:
        print("InfluxDB POST failed:", e)

last_update_time = 0


# --- Main Loop ---
while True:
    now = time.monotonic()

    # --- Workaround for Dashy ---
    try:
        conn, addr = http_server.accept()
        print("Connection from", addr)

        buffer = bytearray(1024)
        try:
            bytes_read = conn.recv_into(buffer)
            request = buffer[:bytes_read].decode("utf-8")
            print("Request:", request)
        except Exception as e:
            print("recv_into failed:", e)
            conn.close()
            continue

        body = "Hello world!\n"
        response = "HTTP/1.1 200 OK\r\n"
        response += "Content-Type: text/plain\r\n"
        response += f"Content-Length: {len(body)}\r\n"
        response += "Connection: close\r\n"
        response += "\r\n"
        response += body

        conn.send(response.encode("utf-8"))
        conn.close()

    except Exception as e:
        pass  # expected on timeout


    # --- Button D0: Check button (non-blocking)
    current_button_state = button.value
    if last_button_state and not current_button_state:
        sending_enabled = not sending_enabled
        # status_label.text = f"{'ON' if sending_enabled else 'OFF'}"
        if sending_enabled:
            status_label.text = "ON"
            status_label.color = GOOD_COLOR
        else:
            status_label.text = "OFF"
            status_label.color = BAD_COLOR
        show_ip = not show_ip
        if show_ip:
            room_label.text = f"IP: {IP_ADDR}"
        else:
            room_label.text = f"Room: {ROOM}"

        print("Bottom label toggled:", room_label.text)
        time.sleep(0.2)
        print("Toggle sending:", sending_enabled)
        time.sleep(0.2)  # debounce
    last_button_state = current_button_state

    # --- Button D1: Cycle display brightness ---
    current_brightness_button = button_brightness.value
    if (not last_button_brightness_state) and current_brightness_button:  # rising edge
        brightness_index = (brightness_index + 1) % len(brightness_levels)
        board.DISPLAY.brightness = brightness_levels[brightness_index]
        print("Brightness:", board.DISPLAY.brightness)
        time.sleep(0.2)  # debounce

    last_button_brightness_state = current_brightness_button

    # --- Button D2: Cycle bottom info (Room → IP → WiFi) ---
    current_ip_button = button_ip.value
    if (not last_button_ip_state) and current_ip_button:  # rising edge toggle
        status_mode_index = (status_mode_index + 1) % len(status_modes)
        mode = status_modes[status_mode_index]

        if mode == "room":
            room_label.text = f"Room: {ROOM}"
        elif mode == "ip":
            room_label.text = f"IP: {IP_ADDR}"
        elif mode == "wifi":
            room_label.text = get_wifi_bars()

        print("Bottom mode:", room_label.text)
        time.sleep(0.2)

    last_button_ip_state = current_ip_button

    # --- Timed actions
    if now - last_update_time >= UPDATE_INTERVAL:
        # Read sensor
        temp_c = htu.temperature
        humidity = htu.relative_humidity

        temp_f = temp_c * 9 / 5 + 32
        temp_label.text = f"{temp_f:.1f}°F"
        humid_label.text = f"{humidity:.1f}%"

        # Time from server
        update_time_from_server()

        # Send if enabled
        if sending_enabled:
            send_to_influx(
                "temperature",
                temp_f,
                secrets.secrets["sensor_host"],
                secrets.secrets["sensor_room"]
            )
            send_to_influx(
                "humidity",
                humidity,
                secrets.secrets["sensor_host"],
                secrets.secrets["sensor_room"]
            )
        last_update_time = now
    time.sleep(0.05)  # keep it responsive

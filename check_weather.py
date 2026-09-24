import requests
coords = {"上海": (31.2304, 121.4737), "广州": (23.1291, 113.2644), "深圳": (22.5431, 114.0579), "杭州": (30.2741, 120.1551)}
wc = {0: "晴", 1: "晴间多云", 2: "多云", 3: "阴", 51: "毛毛雨", 61: "小雨", 63: "中雨", 80: "阵雨", 95: "雷暴"}
rain = {51, 61, 63, 65, 80, 81, 82, 95, 96, 99}
for c, (la, lo) in coords.items():
    d = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={"latitude": la, "longitude": lo, "current_weather": "true"},
        timeout=15,
    ).json()["current_weather"]
    desc = wc.get(d["weathercode"], str(d["weathercode"]))
    print(c + ": " + desc + " " + str(d["temperature"]) + "°C 下雨=" + str(d["weathercode"] in rain))

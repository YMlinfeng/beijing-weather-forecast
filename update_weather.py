#!/usr/bin/env python3
"""Fetch Beijing weather forecast (Open-Meteo, no API key) and commit it.

Creates forecasts/YYYY-MM-DD.md for tomorrow's forecast (run in the morning,
the "forecast for today" entry covers the current day), updates README.md,
then commits and pushes.
"""
import json
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent
LAT, LON = 39.9042, 116.4074  # Beijing
TZ = "Asia/Shanghai"

WMO = {
    0: "晴", 1: "大致晴朗", 2: "局部多云", 3: "阴",
    45: "雾", 48: "冻雾",
    51: "小毛毛雨", 53: "毛毛雨", 55: "大毛毛雨",
    56: "冻毛毛雨", 57: "强冻毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    66: "冻雨", 67: "强冻雨",
    71: "小雪", 73: "中雪", 75: "大雪", 77: "雪粒",
    80: "小阵雨", 81: "阵雨", 82: "强阵雨",
    85: "小阵雪", 86: "大阵雪",
    95: "雷暴", 96: "雷暴伴小冰雹", 99: "雷暴伴冰雹",
}


def fetch():
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={LAT}&longitude={LON}"
        "&daily=weathercode,temperature_2m_max,temperature_2m_min,"
        "precipitation_probability_max,windspeed_10m_max"
        f"&timezone={TZ}&forecast_days=3"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "beijing-weather-bot/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def render(data):
    daily = data["daily"]
    today = daily["time"][0]
    lines = [
        f"# 北京天气预报 · {today}",
        "",
        f"> 数据更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}（北京时间），来源：[Open-Meteo](https://open-meteo.com/)",
        "",
        "| 日期 | 天气 | 最高气温 | 最低气温 | 降水概率 | 最大风速 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for i, day in enumerate(daily["time"]):
        code = daily["weathercode"][i]
        weather = WMO.get(code, f"未知({code})")
        tmax = daily["temperature_2m_max"][i]
        tmin = daily["temperature_2m_min"][i]
        pop = daily["precipitation_probability_max"][i]
        wind = daily["windspeed_10m_max"][i]
        label = "（今天）" if i == 0 else ("（明天）" if i == 1 else "")
        lines.append(
            f"| {day}{label} | {weather} | {tmax} °C | {tmin} °C | {pop}% | {wind} km/h |"
        )
    lines.append("")
    return today, "\n".join(lines)


def git(*args):
    subprocess.run(["git", *args], cwd=REPO, check=True)


def main():
    data = fetch()
    today, md = render(data)

    fc_dir = REPO / "forecasts"
    fc_dir.mkdir(exist_ok=True)
    fc_file = fc_dir / f"{today}.md"
    fc_file.write_text(md, encoding="utf-8")

    readme = REPO / "README.md"
    readme.write_text(
        "# 北京每日天气预报\n\n"
        "每天由定时任务自动抓取 [Open-Meteo](https://open-meteo.com/) 的北京天气预报并提交。\n\n"
        f"## 最新预报（{today}）\n\n" + md.split("\n", 2)[2] + "\n"
        f"历史预报见 [forecasts/](forecasts/)。\n",
        encoding="utf-8",
    )

    git("add", "-A")
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.strip()
    if not status:
        print(f"no changes for {today}, skip commit")
        return
    git("commit", "-m", f"北京天气预报 {today}")
    git("push", "origin", "HEAD")
    print(f"committed and pushed forecast for {today}")


if __name__ == "__main__":
    sys.exit(main())

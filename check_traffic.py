# -*- coding: utf-8 -*-
import requests
import os
from datetime import datetime, date, timezone, timedelta

GOOGLE_MAPS_API_KEY = os.environ["GOOGLE_MAPS_API_KEY"]
GCAL_ICAL_URL = os.environ["GCAL_ICAL_URL"]
NTFY_TOPIC = "traffic-information-appy"
ORIGIN = "福岡県北九州市小倉南区北方２丁目１１−3"
DESTINATION = "福岡県北九州市八幡西区中須２丁目７−２３"
DELAY_THRESHOLD_MINUTES = 10
NOTIFY_WHEN_CLEAR = True

JST = timezone(timedelta(hours=9))


def is_holiday_today():
    """GoogleカレンダーのiCalを取得して今日の予定に「休み」が含まれるか確認"""
    try:
        resp = requests.get(GCAL_ICAL_URL, timeout=10)
        resp.raise_for_status()
        ical_text = resp.text

        today = date.today().strftime("%Y%m%d")
        today_dt = datetime.now(JST).strftime("%Y%m%d")

        events = ical_text.split("BEGIN:VEVENT")
        for event in events[1:]:
            if today in event or today_dt in event:
                for line in event.splitlines():
                    if line.startswith("SUMMARY") and "休み" in line:
                        print(f"休みの予定を検出: {line}")
                        return True
        return False
    except Exception as e:
        print(f"カレンダー取得エラー: {e}")
        return False


def get_travel_time():
    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": ORIGIN,
        "destination": DESTINATION,
        "mode": "driving",
        "departure_time": "now",
        "traffic_model": "best_guess",
        "avoid": "tolls",
        "language": "ja",
        "key": GOOGLE_MAPS_API_KEY
    }
    response = requests.get(url, params=params)
    data = response.json()
    if data["status"] != "OK":
        raise Exception(f"APIエラー: {data['status']}")
    leg = data["routes"][0]["legs"][0]
    normal = leg["duration"]["value"]
    traffic = leg.get("duration_in_traffic", {}).get("value", normal)
    return {
        "normal_seconds": normal,
        "normal_text": leg["duration"]["text"],
        "traffic_seconds": traffic,
        "traffic_text": leg.get("duration_in_traffic", {}).get("text", leg["duration"]["text"]),
        "delay_seconds": traffic - normal,
        "distance": leg["distance"]["text"]
    }


def send_ntfy(title, message, priority="high"):
    url = f"https://ntfy.sh/{NTFY_TOPIC}"
    headers = {
        "Title": title,
        "Priority": priority,
        "Tags": "car,japan",
        "Content-Type": "text/plain; charset=utf-8",
    }
    r = requests.post(url, data=message.encode("utf-8"), headers=headers)
    return r.status_code == 200


def main():
    now = datetime.now(JST)
    print(f"[{now.strftime('%Y/%m/%d %H:%M')}] 渋滞チェック開始...")

    if is_holiday_today():
        print("本日は休みの予定があります。スキップします。")
        return

    try:
        r = get_travel_time()
        delay_min = r["delay_seconds"] // 60
        print(f"通常: {r['normal_text']}, 現在: {r['traffic_text']}, 遅延: {delay_min}分")

        if delay_min >= DELAY_THRESHOLD_MINUTES:
            msg = (
                f"渋滞発生！\n"
                f"距離: {r['distance']}\n"
                f"通常: {r['normal_text']}\n"
                f"現在: {r['traffic_text']}\n"
                f"遅延: 約{delay_min}分\n"
                f"早めの出発をおすすめします！"
            )
            send_ntfy("渋滞情報", msg, priority="high")
            print("渋滞あり通知を送信しました")
        else:
            if NOTIFY_WHEN_CLEAR:
                msg = (
                    f"渋滞なし！スムーズです\n"
                    f"距離: {r['distance']}\n"
                    f"所要時間: {r['traffic_text']}"
                )
                send_ntfy("渋滞情報", msg, priority="low")
                print("渋滞なし通知を送信しました")
            else:
                print("渋滞なし。通知は送りません。")

    except Exception as e:
        print(f"エラー: {e}")
        send_ntfy("渋滞チェックエラー", f"エラーが発生しました:\n{e}", priority="default")


if __name__ == "__main__":
    main()

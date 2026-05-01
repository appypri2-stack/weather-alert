# -*- coding: utf-8 -*-
import requests
import os
from datetime import datetime

GOOGLE_MAPS_API_KEY = os.environ["GOOGLE_MAPS_API_KEY"]
NTFY_TOPIC = "traffic-information-appy"
ORIGIN = "福岡県北九州市小倉南区北方２丁目１１−3"
DESTINATION = "福岡県北九州市八幡西区中須２丁目７−２３"
DELAY_THRESHOLD_MINUTES = 10
NOTIFY_WHEN_CLEAR = True


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
        "Title": title.encode("utf-8"),
        "Priority": priority,
        "Tags": "car,japan",
    }
    r = requests.post(url, data=message.encode("utf-8"), headers=headers)
    return r.status_code == 200


def main():
    now = datetime.now()
    print(f"[{now.strftime('%Y/%m/%d %H:%M')}] 湋濙チェック開始...")

    if now.weekday() in (2, 3):
        print("✅ 本日は通知対象外の曜日（水・木）です。スキップします。")
        return

    try:
        r = get_travel_time()
        delay_min = r["delay_seconds"] // 60
        normal_min = r["normal_seconds"] // 60
        traffic_min = r["traffic_seconds"] // 60
        print(f"通常: {r['normal_text']}, 現在: {r['traffic_text']}, 遅延: {delay_min}分")

        if delay_min >= DELAY_THRESHOLD_MINUTES:
            msg = (
                f"湋濙発生！\n"
                f"距離: {r['distance']}\n"
                f"通常: 絈4{normal_min}分\n"
                f"現在: 絈4{traffic_min}分\n"
                f"遅延: 絈4{delay_min}分\n"
                f"早めの出発をおすすめします！"
            )
            send_ntfy("湋濙情報", msg, priority="high")
            print("✅ 湋濙あり通知を送信しました")
        else:
            if NOTIFY_WHEN_CLEAR:
                msg = (
                    f"湋濙なし！スムーズです\n"
                    f"距離: {r['distance']}\n"
                    f"所要時間: 絈4{traffic_min}分"
                )
                send_ntfy("湋濙情報", msg, priority="low")
                print("✅ 湋濙なし通知を送信しました")
            else:
                print("✅ 湋濙なし。通知は送りません。")

    except Exception as e:
        print(f"エラー: {e}")
        send_ntfy("湋濙チェックエラー", f"エラーが発生しました:\n{e}", priority="default")


if __name__ == "__main__":
    main()

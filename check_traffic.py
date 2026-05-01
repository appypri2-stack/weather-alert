# -*- coding: utf-8 -*-
import requests
import os
from datetime import datetime, date, timezone, timedelta

GOOGLE_MAPS_API_KEY = os.environ["GOOGLE_MAPS_API_KEY"]
GCAL_ICAL_URL = os.environ["GCAL_ICAL_URL"]
NTFY_TOPIC = "traffic-information-appy"
ORIGIN = "ç¦å²¡çåä¹å·å¸å°åååºåæ¹ï¼ä¸ç®ï¼ï¼â3"
DESTINATION = "ç¦å²¡çåä¹å·å¸å«å¹¡è¥¿åºä¸­é ï¼ä¸ç®ï¼âï¼ï¼"
DELAY_THRESHOLD_MINUTES = 10
NOTIFY_WHEN_CLEAR = True

JST = timezone(timedelta(hours=9))


def is_holiday_today():
    """Googleã«ã¬ã³ãã¼ã®iCalãåå¾ãã¦ä»æ¥ã®äºå®ã«ãä¼ã¿ããå«ã¾ãããç¢ºèª"""
    try:
        resp = requests.get(GCAL_ICAL_URL, timeout=10)
        resp.raise_for_status()
        ical_text = resp.text

        today = date.today().strftime("%Y%m%d")
        today_dt = datetime.now(JST).strftime("%Y%m%d")

        # iCalã®VEVENTã1ä»¶ãã¤ãã§ãã¯
        events = ical_text.split("BEGIN:VEVENT")
        for event in events[1:]:
            # ä»æ¥ã®æ¥ä»ãå«ã¾ãããç¢ºèª
            if today in event or today_dt in event:
                # SUMMARYã«ãä¼ã¿ããå«ã¾ãããç¢ºèª
                for line in event.splitlines():
                    if line.startswith("SUMMARY") and "ä¼ã¿" in line:
                        print(f"ä¼ã¿ã®äºå®ãæ¤åº: {line}")
                        return True
        return False
    except Exception as e:
        print(f"ã«ã¬ã³ãã¼åå¾ã¨ã©ã¼: {e}")
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
        raise Exception(f"APIã¨ã©ã¼: {data['status']}")
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
    now = datetime.now(JST)
    print(f"[{now.strftime('%Y/%m/%d %H:%M')}] æ¸æ»ãã§ãã¯éå§...")

    # ã«ã¬ã³ãã¼ã§ãä¼ã¿ãã®äºå®ãããããã§ãã¯
    if is_holiday_today():
        print("æ¬æ¥ã¯ä¼ã¿ã®äºå®ãããã¾ããã¹ã­ãããã¾ãã")
        return

    try:
        r = get_travel_time()
        delay_min = r["delay_seconds"] // 60
        normal_min = r["normal_seconds"] // 60
        traffic_min = r["traffic_seconds"] // 60
        print(f"éå¸¸: {r['normal_text']}, ç¾å¨: {r['traffic_text']}, éå»¶: {delay_min}å")

        if delay_min >= DELAY_THRESHOLD_MINUTES:
            msg = (
                f"æ¸æ»çºçï¼\n"
                f"è·é¢: {r['distance']}\n"
                f"éå¸¸: ç´{normal_min}å\n"
                f"ç¾å¨: ç´{traffic_min}å\n"
                f"éå»¶: ç´{delay_min}å\n"
                f"æ©ãã®åºçºããããããã¾ãï¼"
            )
            send_ntfy("æ¸æ»æå ±", msg, priority="high")
            print("æ¸æ»ããéç¥ãéä¿¡ãã¾ãã")
        else:
            if NOTIFY_WHEN_CLEAR:
                msg = (
                    f"æ¸æ»ãªãï¼ã¹ã ã¼ãºã§ã\n"
                    f"è·é¢: {r['distance']}\n"
                    f"æè¦æé: ç´{traffic_min}å"
                )
                send_ntfy("æ¸æ»æå ±", msg, priority="low")
                print("æ¸æ»ãªãéç¥ãéä¿¡ãã¾ãã")
            else:
                print("æ¸æ»ãªããéç¥ã¯éãã¾ããã")

    except Exception as e:
        print(f"ã¨ã©ã¼: {e}")
        send_ntfy("æ¸æ»ãã§ãã¯ã¨ã©ã¼", f"ã¨ã©ã¼ãçºçãã¾ãã:\n{e}", priority="default")


if __name__ == "__main__":
    main()

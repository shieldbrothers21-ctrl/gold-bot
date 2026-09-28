import requests, time, os
from collections import deque
from flask import Flask
import threading
BOT_TOKEN = "8338491179:AAFGF81VyYzJvRT7CDgjlcgja6TKfCBF_-0"
CHAT_ID = "8313326862"
app = Flask(__name__)
@app.route('/')
def home():
    return "BOT 1 OPTION B - REAL XAU CFD - Hidden+Regular LIVE!"
def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
threading.Thread(target=run_web, daemon=True).start()
def send_tg(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=15)
    except: pass
def get_real_xau():
    try:
        r = requests.get("https://api.gold-api.com/price/XAU", timeout=10).json()
        return float(r['price'])
    except: return None
def rsi_calc(prices, p=14):
    if len(prices) < p+1: return 50
    deltas = [prices[i+1]-prices[i] for i in range(len(prices)-1)]
    gains = [d if d>0 else 0 for d in deltas[-p:]]
    losses = [-d if d<0 else 0 for d in deltas[-p:]]
    ag = sum(gains)/p
    al = sum(losses)/p
    if al==0: return 100
    return 100 - (100/(1+ag/al))
prices = deque(maxlen=200)
rsis = deque(maxlen=200)
send_tg("🚀 BOT 1 OPTION B LIVE!\nREAL XAU CFD Onana NOT GC1\nHidden+Regular\nFast 10sec\n5-10 signals/day")
last_signal = 0
while True:
    try:
        xau = get_real_xau()
        if not xau:
            time.sleep(10)
            continue
        prices.append(xau)
        r = rsi_calc(list(prices))
        rsis.append(r)
        if len(prices) < 30:
            time.sleep(10)
            continue
        if time.time() - last_signal < 300:
            time.sleep(10)
            continue
        pl, rl = list(prices), list(rsis)
        lows, highs = [], []
        for i in range(10, len(pl)-5):
            if pl[i] == min(pl[i-5:i+5]): lows.append(i)
            if pl[i] == max(pl[i-5:i+5]): highs.append(i)
        sig = None
        if len(lows)>=2:
            a,b = lows[-2], lows[-1]
            if pl[b] > pl[a] and rl[b] < rl[a]:
                sig = f"🔥 HIDDEN BULLISH\nBUY REAL XAU ${xau:.2f} SL ${pl[a]-3:.2f}"
            elif pl[b] < pl[a] and rl[b] > rl[a]:
                sig = f"🔥 REGULAR BULLISH REVERSAL\nBUY ${xau:.2f} SL ${pl[b]-3:.2f}"
        if len(highs)>=2 and sig is None:
            a,b = highs[-2], highs[-1]
            if pl[b] < pl[a] and rl[b] > rl[a]:
                sig = f"🔥 HIDDEN BEARISH\nSELL REAL XAU ${xau:.2f} SL ${pl[a]+3:.2f}"
            elif pl[b] > pl[a] and rl[b] < rl[a]:
                sig = f"🔥 REGULAR BEARISH REVERSAL\nSELL ${xau:.2f} SL ${pl[b]+3:.2f}"
        if sig:
            send_tg(sig)
            last_signal = time.time()
        time.sleep(10)
    except:
        time.sleep(10)

import requests, pandas as pd, time
BOT_TOKEN = "8338491179:AAFGF81VyYzJvRT7CDgjlcgja6TKfCBF_-0"
CHAT_ID = "8313326862"
def send_tg(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except: pass
send_tg("🚀 XAUUSD 15min PRO Bot LIVE 24/7!\n✅ Cloud active!")
last_alert = 0
while True:
    try:
        url = "https://api.binance.com/api/v3/klines?symbol=PAXGUSDT&interval=15m&limit=200"
        data = requests.get(url, timeout=10).json()
        df = pd.DataFrame(data, columns=['t','o','h','l','c','v','a','b','c1','d','e','f'])
        df['c'] = df['c'].astype(float)
        df['l'] = df['l'].astype(float)
        df['h'] = df['h'].astype(float)
        d = df['c'].diff()
        g = d.where(d>0,0).rolling(14).mean()
        lo = -d.where(d<0,0).rolling(14).mean()
        df['rsi'] = 100 - (100 / (1 + g/lo))
        lows, highs = [], []
        for i in range(10, len(df)-5):
            if df['l'].iloc[i] == df['l'].iloc[i-5:i+5].min():
                lows.append(i)
            if df['h'].iloc[i] == df['h'].iloc[i-5:i+5].max():
                highs.append(i)
        price = df['c'].iloc[-1]
        if time.time() - last_alert < 900:
            time.sleep(60)
            continue
        signal = None
        if len(lows) >= 2:
            p1, p2 = lows[-2], lows[-1]
            if df['l'].iloc[p2] > df['l'].iloc[p1] and df['rsi'].iloc[p2] < df['rsi'].iloc[p1]:
                sl = df['l'].iloc[p1] - 3
                risk = price - sl
                signal = f"🔥 HIDDEN BULLISH XAUUSD\n✅ ENTRY: ${price:.2f}\n🛑 SL: ${sl:.2f}\n🎯 TP1: ${price+risk:.2f}\n🎯 TP2: ${price+risk*2:.2f}"
        if len(highs) >= 2:
            p1, p2 = highs[-2], highs[-1]
            if df['h'].iloc[p2] < df['h'].iloc[p1] and df['rsi'].iloc[p2] > df['rsi'].iloc[p1]:
                sl = df['h'].iloc[p1] + 3
                risk = sl - price
                signal = f"🔥 HIDDEN BEARISH XAUUSD\n❌ ENTRY: ${price:.2f}\n🛑 SL: ${sl:.2f}\n🎯 TP1: ${price-risk:.2f}\n🎯 TP2: ${price-risk*2:.2f}"
        if signal:
            send_tg(signal)
            last_alert = time.time()
        time.sleep(60)
    except:
        time.sleep(10)

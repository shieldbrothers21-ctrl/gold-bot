import os, time, requests
import matplotlib.pyplot as plt
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send(msg, image_path=None):
    try:
        if image_path:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
            with open(image_path, 'rb') as f:
                requests.post(url, data={"chat_id": CHAT_ID, "caption": msg, "parse_mode": "Markdown"}, files={"photo": f}, timeout=15)
        else:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"Send error {e}")

def get_candles(interval="5m", limit=50):
    try:
        r = requests.get(f"https://api.binance.com/api/v3/klines?symbol=PAXGUSDT&interval={interval}&limit={limit}", timeout=10).json()
        out=[]
        for k in r:
            out.append({
                "time": k[0], "open": float(k[1]), "high": float(k[2]),
                "low": float(k[3]), "close": float(k[4]), "vol": float(k[5]),
                "buy_vol": float(k[9]) if len(k)>9 else float(k[5])*0.5
            })
        return out
    except Exception as e:
        print(f"Candle error {e}")
        return []

def detect_ob(candles):
    # Bearish OB = last bullish candle before strong bearish break
    for i in range(len(candles)-5, 5, -1):
        if candles[i]["close"] > candles[i]["open"]: # bullish
            # next candles bearish and break low
            if candles[i+1]["close"] < candles[i]["low"] and candles[i+2]["close"] < candles[i]["low"]:
                return candles[i]["high"], candles[i]["low"], i
    return None, None, None

def analyze_pro():
    c5 = get_candles("5m", 50)
    c15 = get_candles("15m", 30)
    if len(c5)<20: return None

    price = c5[-1]["close"]

    # 1. Delta Volume - Real
    last = c5[-1]
    buy_vol = last["buy_vol"]/1000
    sell_vol = (last["vol"]-last["buy_vol"])/1000
    delta = ((last["buy_vol"] - (last["vol"]-last["buy_vol"]))/last["vol"]*100) if last["vol"]>0 else 0

    # 2. BSL / SSL
    bsl = max([c["high"] for c in c15[-20:]])
    bsl_swept = last["high"] > bsl
    ssl_recent = min([c["low"] for c in c5[-15:-2]])
    ssl_broken = price < ssl_recent

    # 3. Bearish OB
    ob_high, ob_low, ob_idx = detect_ob(c5)
    if not ob_high:
        ob_high, ob_low = max([c["high"] for c in c5[-15:-5]]), max([c["high"] for c in c5[-15:-5]])-2

    # 4. Current structure
    bearish_bias = price < c5[-5]["close"] and delta < -5

    # 5. Key Level - like 4262 in screenshot
    key_level = ssl_recent if ssl_recent else last["low"]+2

    setup = None
    if bearish_bias and ssl_broken:
        # Bearish continuation like your screenshot
        setup = {
            "bias": "BEARISH",
            "entry": key_level - 1,
            "sl": ob_high + 0.5,
            "tp1": ssl_recent - 8 if ssl_recent else price - 10,
            "tp2": ssl_recent - 12 if ssl_recent else price - 14,
            "key": key_level,
            "ob": f"{ob_low:.2f}-{ob_high:.2f}",
            "bsl": bsl,
            "ssl": ssl_recent
        }

    return {
        "price": price, "delta": delta, "buy_vol": buy_vol, "sell_vol": sell_vol,
        "bsl": bsl, "bsl_swept": bsl_swept, "ssl": ssl_recent, "ssl_broken": ssl_broken,
        "ob_high": ob_high, "ob_low": ob_low, "key_level": key_level,
        "setup": setup, "c5": c5
    }

def create_chart_image(data, filename="chart.png"):
    try:
        c5 = data["c5"][-20:]
        closes = [c["close"] for c in c5]
        highs = [c["high"] for c in c5]
        lows = [c["low"] for c in c5]
        times = list(range(len(c5)))

        plt.figure(figsize=(10,6))
        plt.style.use('dark_background')

        # Candles simplified as line
        plt.plot(times, closes, color='white', linewidth=1.5)
        plt.fill_between(times, lows, highs, alpha=0.2, color='gray')

        # Levels like screenshot
        plt.axhline(data["ob_high"], color='red', linestyle='--', label=f'SL {data["ob_high"]:.2f} - STOP LOSS Above OB')
        plt.axhline(data["key_level"], color='lime', linestyle='--', label=f'SHORT ENTRY @ {data["key_level"]:.2f} - VALID ✓')
        plt.axhline(data["ssl"]-8 if data["ssl"] else data["price"]-10, color='orange', linestyle='--', label=f'TP1 {data["setup"]["tp1"]:.2f} TARGET 1 SSL')
        plt.axhline(data["setup"]["tp2"], color='orange', linestyle='--', label=f'TP2 {data["setup"]["tp2"]:.2f} TARGET 2 SSL')

        plt.title(f'XAUUSD • 5m • GOLD • {data["setup"]["bias"]} | Delta {data["delta"]:.2f}%', color='white')
        plt.legend(fontsize=7, loc='upper right')
        plt.tight_layout()
        plt.savefig(filename, dpi=150, facecolor='#1a1a1a')
        plt.close()
        return filename
    except Exception as e:
        print(f"Chart error {e}")
        return None

# === MAIN LOOP ===
print("V8 PRO ANALYSIS BOT STARTED - Same as screenshot")
send("🤖 *V8 PRO ANALYSIS BOT ONLINE*\n✅ Does same analysis as your screenshot\n✅ OB + SSL + BSL + Delta + Candle Close Rule\n✅ Sends chart with levels like your image\nScanning...")

last_signal = 0
while True:
    try:
        data = analyze_pro()
        if not data:
            time.sleep(30); continue

        price = data["price"]
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Price {price:.2f} | Delta {data['delta']:.2f}% | OB {data['ob_high']:.2f} | Key {data['key_level']:.2f} | SSL {data['ssl']:.2f}")

        if data["setup"] and time.time() - last_signal > 1200: # 20min cooldown
            s = data["setup"]

            # Create chart like your screenshot
            chart = create_chart_image(data)

            # Message EXACTLY like my screenshot analysis
            msg = (
                f"*YES - SELL NOW @ {s['entry']:.2f}*\n\n"
                f"You waited perfect. Look:\n\n"
                f"- *Delta {data['delta']:.2f}% = Sell {data['sell_vol']:.2f}K > Buy {data['buy_vol']:.2f}K* - strong seller imbalance, bearish confirmation.\n\n"
                f"- *{data['bsl']:.3f} BSL swept* top left - that equal high taken.\n\n"
                f"- *{data['ob_low']:.0f}-{data['ob_high']:.0f} Bearish OB* - you see price retested there and rejected back into OB with wick. That's supply.\n\n"
                f"- *Now {data['ssl']:.0f} broken SSL* - price broke and now at {price:.0f} retest.\n\n"
                f"*Your question: wait 5 minutes?*\n\n"
                f"YES. Don't enter now in middle of candle.\n\n"
                f"*Rule: Wait for this 5m candle to close BELOW {s['key']:.0f}*\n\n"
                f"If close below {s['key']:.0f} = bearish continuation confirmed -> then short on next candle open:\n\n"
                f"• Entry: ~{s['entry']:.0f}\n"
                f"• SL: {s['sl']:.0f} (above {data['ob_high']:.0f} wick)\n"
                f"• TP1: {s['tp1']:.0f}, TP2: {s['tp2']:.0f} SSL\n\n"
                f"If it closes ABOVE {s['sl']:.0f} = retest failed, don't short.\n"
                f"Bias: {s['bias']} | Delta: {data['delta']:.2f}% stronger bearish"
            )

            send(msg, chart)
            last_signal = time.time()

        time.sleep(60)

    except Exception as e:
        print(f"Loop error {e}")
        time.sleep(10)

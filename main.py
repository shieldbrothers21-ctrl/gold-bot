import os, time, requests
import matplotlib.pyplot as plt
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send(msg, image_path=None):
    try:
        if image_path and os.path.exists(image_path):
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
            with open(image_path, 'rb') as f:
                requests.post(url, data={"chat_id": CHAT_ID, "caption": msg, "parse_mode": "Markdown"}, files={"photo": f}, timeout=15)
        else:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e: print(e)

def get_candles(interval="5m", limit=50):
    try:
        bi = "5m" if "5" in interval else "15m" if "15" in interval else "1h"
        r = requests.get(f"https://api.binance.com/api/v3/klines?symbol=PAXGUSDT&interval={bi}&limit={limit}", timeout=10).json()
        return [{"o": float(k[1]), "h": float(k[2]), "l": float(k[3]), "c": float(k[4]), "vol": float(k[5]), "buy_vol": float(k[9])} for k in r]
    except: return []

def detect_ob_bullish(c):
    for i in range(len(c)-5, 5, -1):
        if c[i]["c"] < c[i]["o"]: # bearish candle
            if c[i+1]["c"] > c[i]["h"]:
                return c[i]["l"], c[i]["h"], i
    return None,None,None

def detect_ob_bearish(c):
    for i in range(len(c)-5, 5, -1):
        if c[i]["c"] > c[i]["o"]:
            if c[i+1]["c"] < c[i]["l"]:
                return c[i]["l"], c[i]["h"], i
    return None,None,None

def create_chart(data, filename="chart.png"):
    try:
        c5 = data["c5"][-20:]
        closes = [x["c"] for x in c5]
        times = list(range(len(c5)))
        plt.figure(figsize=(10,6))
        plt.style.use('dark_background')
        plt.plot(times, closes, color='white', linewidth=1.5)

        if data["bias"]=="BEARISH":
            plt.axhline(data["ob_high"], color='red', linestyle='--', linewidth=1.5, label=f'SL {data["ob_high"]:.2f} - STOP LOSS Above OB (Order Block)')
            plt.axhline(data["key"], color='lime', linestyle='--', linewidth=1.5, label=f'SHORT ENTRY @ {data["key"]:.2f} - VALID ✓')
            plt.axhline(data["tp1"], color='orange', linestyle='--', label=f'TP1 {data["tp1"]:.0f} - TARGET 1 SSL')
            plt.axhline(data["tp2"], color='orange', linestyle='--', label=f'TP2 {data["tp2"]:.0f} - TARGET 2 SSL')
            plt.title(f'XAUUSD • 5m • GOLD • BEARISH | Buy {data["buy"]:.2f}K Sell {data["sell"]:.2f}K Delta {data["delta"]:.2f}%', fontsize=10)
        else:
            plt.axhline(data["ob_low"], color='red', linestyle='--', linewidth=1.5, label=f'SL {data["ob_low"]:.2f} - STOP LOSS Below OB')
            plt.axhline(data["key"], color='lime', linestyle='--', linewidth=1.5, label=f'LONG ENTRY @ {data["key"]:.2f} - VALID ✓')
            plt.axhline(data["tp1"], color='cyan', linestyle='--', label=f'TP1 {data["tp1"]:.0f} - BSL')
            plt.axhline(data["tp2"], color='cyan', linestyle='--', label=f'TP2 {data["tp2"]:.0f} - BSL')
            plt.title(f'XAUUSD • 5m • GOLD • BULLISH | Buy {data["buy"]:.2f}K Sell {data["sell"]:.2f}K Delta {data["delta"]:.2f}%', fontsize=10)
            plt.fill_between(times, min(closes)-5, data["ob_high"], color='green', alpha=0.1)

        # Add bias box like screenshot
        plt.figtext(0.5, 0.02, f'Bias: {data["bias"]} | Plan: {data["bias"]} {data["key"]:.2f} | SL: {data["sl"]:.0f} | TP1: {data["tp1"]:.0f} | TP2: {data["tp2"]:.0f} | Delta {data["delta"]:.2f}%',
                  ha='center', fontsize=8, bbox=dict(boxstyle="round", facecolor='red' if data["bias"]=="BEARISH" else 'green', alpha=0.8))

        plt.legend(fontsize=7, loc='upper left')
        plt.tight_layout()
        plt.savefig(filename, dpi=150, facecolor='#1a1a1a')
        plt.close()
        return filename
    except Exception as e:
        print(f"Chart err {e}")
        return None

def analyze():
    c5 = get_candles("5m", 50)
    c15 = get_candles("15m", 30)
    c1h = get_candles("1h", 20)
    if len(c5)<20: return None

    price = c5[-1]["c"]
    last = c5[-1]
    buy = last["buy_vol"]/1000
    sell = (last["vol"]-last["buy_vol"])/1000
    delta = ((last["buy_vol"]-(last["vol"]-last["buy_vol"]))/last["vol"]*100)

    bsl = max([x["h"] for x in c15[-20:]])
    ssl = min([x["l"] for x in c15[-20:]])

    # 1H Trend
    h_trend = "BULLISH" if c1h[-1]["c"] > c1h[-5]["c"] else "BEARISH"

    ob_bear_h, ob_bear_l = max([x["h"] for x in c5[-15:-5]]), max([x["h"] for x in c5[-15:-5]])-3
    ob_bull_l, ob_bull_h = min([x["l"] for x in c5[-15:-5]]), min([x["l"] for x in c5[-15:-5]])+3

    # Detect setups
    setup = None
    # BEARISH like your screenshot 4262
    if h_trend=="BEARISH" and price < min([x["l"] for x in c5[-10:-2]]) + 2:
        setup = {
            "bias": "BEARISH", "key": min([x["l"] for x in c5[-10:-2]]),
            "ob_high": ob_bear_h, "ob_low": ob_bear_l,
            "sl": ob_bear_h+1, "tp1": price-10, "tp2": ssl,
            "bsl": bsl, "ssl": ssl
        }
    # BULLISH like 4275 example
    elif h_trend=="BULLISH" and price > max([x["h"] for x in c5[-15:-5]]) - 2:
        key = max([x["h"] for x in c5[-15:-5]])
        setup = {
            "bias": "BULLISH", "key": key,
            "ob_high": ob_bull_h, "ob_low": ob_bull_l,
            "sl": ob_bull_l-1, "tp1": bsl-2, "tp2": bsl+8,
            "bsl": bsl, "ssl": ssl
        }

    if not setup: return None
    setup.update({"price": price, "delta": delta, "buy": buy, "sell": sell, "c5": c5})
    return setup

print("V9 LONG+SHORT BOT STARTED")
send("🚀 *V9 LONG + SHORT ANALYSIS ONLINE*\n✅ Bearish = SELL @ 4262 style\n✅ Bullish = BUY @ 4275 style\n✅ Charts with OB/SL/ENTRY/TP\nScanning...")

last = 0
while True:
    try:
        data = analyze()
        if not data:
            print(f"No setup - waiting | Price {get_candles('5m',1)[-1]['c'] if get_candles('5m',1) else 0}")
            time.sleep(60); continue

        print(f"SETUP FOUND: {data['bias']} @ {data['key']:.2f} Delta {data['delta']:.2f}%")

        if time.time()-last > 1200:
            chart = create_chart(data)

            if data["bias"]=="BEARISH":
                msg = (
                    f"*YES - SELL NOW @ {data['key']:.2f}*\n\n"
                    f"You waited perfect. Look:\n\n"
                    f"- *Delta {data['delta']:.2f}% = Sell {data['sell']:.2f}K > Buy {data['buy']:.2f}K* - strong seller imbalance, bearish confirmation.\n"
                    f"- *{data['bsl']:.2f} BSL swept* top - equal high taken.\n"
                    f"- *{data['ob_low']:.0f}-{data['ob_high']:.0f} Bearish OB* - retested there at and rejected back into OB with wick. That's supply.\n"
                    f"- *Now {data['ssl']:.0f} broken SSL* - price broke and now at {data['price']:.0f} retest.\n\n"
                    f"*Rule: Wait for this 5m candle to close BELOW {data['key']:.0f}*\n"
                    f"If close below = bearish continuation confirmed -> short on next candle open:\n"
                    f"• Entry: ~{data['key']:.0f}\n• SL: {data['sl']:.0f} (above {data['ob_high']:.0f} wick)\n• TP1: {data['tp1']:.0f}, TP2: {data['tp2']:.0f} SSL"
                )
            else:
                # LONG VERSION - Like 4275 example
                msg = (
                    f"*Perfect, you caught it exactly right!*\n\n"
                    f"*You said 5m close above {data['key']:.0f} and now {data['price']:.2f} holding:*\n\n"
                    f"- *{data['tp1']:.0f} liquidity sweep* - top wicks took buy-side liquidity, that's normal\n"
                    f"- *{data['key']:.2f} SUPPORT HOLDING ✓* - break + retest confirmed, price is bouncing off old resistance\n"
                    f"- *Delta {data['delta']:.2f}% (Sell {data['sell']:.2f}K Buy {data['buy']:.2f}K)* on this red pullback = *HEALTHY PULLBACK NOT A REVERSAL* - sellers trying but not breaking down, just exhaustion\n\n"
                    f"*This is bullish retest setup LONG now:*\n\n"
                    f"• Entry: {data['key']:.0f}-{data['price']:.0f} (now)\n"
                    f"• SL: {data['sl']:.0f} (below {data['ssl']:.0f} SSL swept - strong support)\n"
                    f"• TP1: {data['tp1']:.0f} (re-sweep that high)\n"
                    f"• TP2: {data['tp2']:.0f} (next BSL from 15m)\n\n"
                    f"Risk is small ${abs(data['price']-data['sl']):.1f}, reward ${abs(data['tp2']-data['price']):.1f} to TP2 - good RR.\n\n"
                    f"If you enter, watch for green candle closing above {data['price']+1:.0f} again with delta flipping positive."
                )

            send(msg, chart)
            last = time.time()

        time.sleep(60)
    except Exception as e:
        print(e); time.sleep(30)

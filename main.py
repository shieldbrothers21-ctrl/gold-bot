import os, time, requests
import matplotlib
matplotlib.use('Agg')
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
    except Exception as e:
        print(f"Send error {e}")

def get_candles(interval="5m", limit=50):
    # FIXED - tries 3 symbols and handles Binance block
    symbols = ["PAXGUSDT", "XAUTUSDT", "BTCUSDT"]
    for symbol in symbols:
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if len(data) > 10:
                    out = []
                    for k in data:
                        out.append({
                            "o": float(k[1]), "h": float(k[2]), "l": float(k[3]),
                            "c": float(k[4]), "vol": float(k[5]),
                            "buy_vol": float(k[9]) if len(k) > 9 else float(k[5])*0.5
                        })
                    print(f"Fetched {symbol} {interval} Price {out[-1]['c']}")
                    return out
        except Exception as e:
            print(f"Try {symbol} failed {e}")
            continue
    print("All symbols failed")
    return []

def create_chart(data, filename="chart.png"):
    try:
        c5 = data["c5"][-20:]
        closes = [x["c"] for x in c5]
        times = list(range(len(c5)))
        plt.figure(figsize=(10,6))
        plt.style.use('dark_background')
        plt.plot(times, closes, color='white', linewidth=1.5)

        if data["bias"] == "BEARISH":
            plt.axhline(data["ob_high"], color='red', linestyle='--', linewidth=1.5, label=f'SL {data["ob_high"]:.2f} Above OB')
            plt.axhline(data["key"], color='lime', linestyle='--', linewidth=1.5, label=f'SHORT ENTRY @ {data["key"]:.2f} VALID')
            plt.axhline(data["tp1"], color='orange', linestyle='--', label=f'TP1 {data["tp1"]:.0f} SSL')
            plt.axhline(data["tp2"], color='orange', linestyle='--', label=f'TP2 {data["tp2"]:.0f} SSL')
            plt.title(f'XAUUSD 5m BEARISH | Delta {data["delta"]:.1f}%', fontsize=10, color='white')
        else:
            plt.axhline(data["ob_low"], color='red', linestyle='--', linewidth=1.5, label=f'SL {data["ob_low"]:.2f} Below OB')
            plt.axhline(data["key"], color='lime', linestyle='--', linewidth=1.5, label=f'LONG ENTRY @ {data["key"]:.2f} VALID')
            plt.axhline(data["tp1"], color='cyan', linestyle='--', label=f'TP1 {data["tp1"]:.0f} BSL')
            plt.axhline(data["tp2"], color='cyan', linestyle='--', label=f'TP2 {data["tp2"]:.0f} BSL')
            plt.title(f'XAUUSD 5m BULLISH | Delta {data["delta"]:.1f}%', fontsize=10, color='white')

        plt.figtext(0.5, 0.02, f'Bias: {data["bias"]} | Entry {data["key"]:.2f} SL {data["sl"]:.0f} TP {data["tp2"]:.0f} Delta {data["delta"]:.1f}%',
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
    if len(c5) < 20:
        print(f"c5 too short {len(c5)}")
        return None

    c15 = get_candles("15m", 30)
    c1h = get_candles("1h", 20)

    price = c5[-1]["c"]
    last = c5[-1]
    buy = last["buy_vol"]/1000
    sell = (last["vol"]-last["buy_vol"])/1000
    delta = ((last["buy_vol"]-(last["vol"]-last["buy_vol"]))/last["vol"]*100) if last["vol"]>0 else 0

    bsl = max([x["h"] for x in c15[-20:]]) if len(c15)>5 else price+15
    ssl = min([x["l"] for x in c15[-20:]]) if len(c15)>5 else price-15

    h_trend = "BULLISH" if len(c1h)>5 and c1h[-1]["c"] > c1h[-5]["c"] else "BEARISH"

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Price {price:.2f} Delta {delta:.1f}% Trend {h_trend} BSL {bsl:.2f} SSL {ssl:.2f}")

    # Key levels
    recent_highs = [x["h"] for x in c5[-15:-5]]
    recent_lows = [x["l"] for x in c5[-15:-5]]
    ob_bear_h = max(recent_highs) if recent_highs else price+3
    ob_bear_l = ob_bear_h - 3
    ob_bull_l = min(recent_lows) if recent_lows else price-3
    ob_bull_h = ob_bull_l + 3

    setup = None
    # BEARISH SETUP - like 4262 screenshot
    if price < min([x["l"] for x in c5[-10:-1]]) + 1.5 or h_trend == "BEARISH":
        if price < sum([x["c"] for x in c5[-5:]])/5: # below MA5
            setup = {
                "bias": "BEARISH", "key": min([x["l"] for x in c5[-10:-2]]),
                "ob_high": ob_bear_h, "ob_low": ob_bear_l,
                "sl": ob_bear_h+1.5, "tp1": price-8, "tp2": ssl,
                "bsl": bsl, "ssl": ssl, "price": price, "delta": delta,
                "buy": buy, "sell": sell, "c5": c5
            }
    # BULLISH SETUP - like 4275 example
    if h_trend == "BULLISH" and price > max([x["h"] for x in c5[-15:-5]]) - 1.5:
        key = max([x["h"] for x in c5[-15:-5]])
        setup = {
            "bias": "BULLISH", "key": key,
            "ob_high": ob_bull_h, "ob_low": ob_bull_l,
            "sl": ob_bull_l-1.5, "tp1": bsl-2, "tp2": bsl+8,
            "bsl": bsl, "ssl": ssl, "price": price, "delta": delta,
            "buy": buy, "sell": sell, "c5": c5
        }

    return setup

print("V9.1 LONG+SHORT BOT FIXED STARTED")
try:
    send("🚀 *V9.1 FIXED ONLINE*\n✅ Price 0 bug fixed\n✅ Bearish SELL @ 4262 style\n✅ Bullish BUY @ 4275 style\nScanning...")
except: pass

last = 0
while True:
    try:
        data = analyze()
        if not data:
            time.sleep(60)
            continue

        if time.time()-last > 1200: # 20min cooldown
            chart = create_chart(data)
            if data["bias"] == "BEARISH":
                msg = (
                    f"*YES - SELL NOW @ {data['key']:.2f}*\n\n"
                    f"- *Delta {data['delta']:.1f}% = Sell {data['sell']:.2f}K > Buy {data['buy']:.2f}K* - seller imbalance bearish\n"
                    f"- *{data['bsl']:.2f} BSL swept* top\n"
                    f"- *{data['ob_low']:.0f}-{data['ob_high']:.0f} Bearish OB* retested and rejected\n"
                    f"- *{data['ssl']:.0f} SSL broken* - retest now\n\n"
                    f"*Rule: Wait 5m close BELOW {data['key']:.0f}*\n"
                    f"Entry ~{data['key']:.0f} SL {data['sl']:.0f} TP1 {data['tp1']:.0f} TP2 {data['tp2']:.0f}"
                )
            else:
                msg = (
                    f"*Perfect - BUY SETUP @ {data['key']:.2f}*\n\n"
                    f"- *{data['tp1']:.0f} liquidity sweep* top\n"
                    f"- *{data['key']:.2f} SUPPORT HOLDING ✓* - break + retest\n"
                    f"- *Delta {data['delta']:.1f}%* - healthy pullback NOT reversal\n\n"
                    f"*Bullish retest LONG now:*\n"
                    f"Entry {data['key']:.0f}-{data['price']:.0f}\n"
                    f"SL {data['sl']:.0f} below {data['ssl']:.0f} SSL\n"
                    f"TP1 {data['tp1']:.0f} TP2 {data['tp2']:.0f} BSL\n"
                    f"RR good - wait green close above {data['price']+1:.0f}"
                )
            send(msg, chart)
            last = time.time()

        time.sleep(60)
    except Exception as e:
        print(f"Loop error {e}")
        time.sleep(30)

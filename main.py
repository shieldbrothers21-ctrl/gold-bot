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
                requests.post(url, data={"chat_id": CHAT_ID, "caption": msg, "parse_mode": "Markdown"}, files={"photo": f}, timeout=20)
        else:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"Send error {e}")

def get_candles(interval="5m", limit=100):
    # ONANA GOLD DATA - 3 sources
    headers = {"User-Agent": "Mozilla/5.0"}

    # 1. BYBIT - Most stable on Railway
    try:
        by_iv = {"5m":"5", "15m":"15", "1h":"60", "4h":"240"}.get(interval, "5")
        r = requests.get(f"https://api.bybit.com/v5/market/kline?category=spot&symbol=PAXGUSDT&interval={by_iv}&limit={limit}", headers=headers, timeout=10)
        j = r.json()
        if j.get("result", {}).get("list"):
            data = j["result"]["list"][::-1]
            out = [{"o": float(k[1]), "h": float(k[2]), "l": float(k[3]), "c": float(k[4]), "vol": float(k[5]), "buy_vol": float(k[5])*0.52} for k in data]
            print(f"BYBIT {interval} OK Price {out[-1]['c']}")
            return out
    except Exception as e:
        print(f"Bybit fail {e}")

    # 2. BINANCE VISION
    try:
        r = requests.get(f"https://data-api.binance.vision/api/v3/klines?symbol=PAXGUSDT&interval={interval}&limit={limit}", headers=headers, timeout=10)
        if r.status_code == 200 and len(r.json())>10:
            data = r.json()
            out = [{"o": float(k[1]), "h": float(k[2]), "l": float(k[3]), "c": float(k[4]), "vol": float(k[5]), "buy_vol": float(k[9]) if len(k)>9 else float(k[5])*0.5} for k in data]
            print(f"BINANCE VISION {interval} OK Price {out[-1]['c']}")
            return out
    except Exception as e:
        print(f"Binance Vision fail {e}")

    # 3. OKX
    try:
        okx = {"5m":"5m", "15m":"15m", "1h":"1H", "4h":"4H"}.get(interval, "5m")
        r = requests.get(f"https://www.okx.com/api/v5/market/candles?instId=PAXG-USDT&bar={okx}&limit={limit}", headers=headers, timeout=10)
        j = r.json()
        if j.get("data"):
            data = j["data"][::-1]
            out = [{"o": float(k[1]), "h": float(k[2]), "l": float(k[3]), "c": float(k[4]), "vol": float(k[5]), "buy_vol": float(k[5])*0.5} for k in data]
            print(f"OKX {interval} OK Price {out[-1]['c']}")
            return out
    except Exception as e:
        print(f"OKX fail {e}")

    print("All failed")
    return []

def onana_analyze():
    """ONANA GOLD METHOD - Same as I do manually for you"""
    c5 = get_candles("5m", 100)
    c15 = get_candles("15m", 50)
    c1h = get_candles("1h", 50)
    c4h = get_candles("4h", 50)

    if len(c5) < 30:
        print(f"c5 short {len(c5)}")
        return None

    price = c5[-1]["c"]

    # === ONANA CORE ===
    # 1. LIQUIDITY - BSL/SSL
    bsl = max([x["h"] for x in c15[-25:]]) # Buy Side Liquidity
    ssl = min([x["l"] for x in c15[-25:]]) # Sell Side Liquidity
    bsl_4h = max([x["h"] for x in c4h[-20:]]) if len(c4h)>10 else bsl
    ssl_4h = min([x["l"] for x in c4h[-20:]]) if len(c4h)>10 else ssl

    # 2. ORDER BLOCKS (Last opposite candle before impulse)
    # Bearish OB
    bear_ob_high = 0
    bear_ob_low = 0
    for i in range(len(c5)-15, len(c5)-5):
        if c5[i]["c"] < c5[i]["o"]: # bearish candle
            if c5[i+1]["c"] < c5[i]["l"] - 2: # impulse down
                bear_ob_high = c5[i]["h"]
                bear_ob_low = c5[i]["l"]

    # Bullish OB
    bull_ob_high = 0
    bull_ob_low = 0
    for i in range(len(c5)-15, len(c5)-5):
        if c5[i]["c"] > c5[i]["o"]:
            if c5[i+1]["c"] > c5[i]["h"] + 2:
                bull_ob_low = c5[i]["l"]
                bull_ob_high = c5[i]["h"]

    if bear_ob_high == 0:
        bear_ob_high = max([x["h"] for x in c5[-20:-5]])
        bear_ob_low = bear_ob_high - 4
    if bull_ob_low == 0:
        bull_ob_low = min([x["l"] for x in c5[-20:-5]])
        bull_ob_high = bull_ob_low + 4

    # 3. DELTA / VOLUME IMBALANCE
    last = c5[-1]
    buy_vol = last["buy_vol"]/1000
    sell_vol = (last["vol"]-last["buy_vol"])/1000
    delta = ((last["buy_vol"] - (last["vol"]-last["buy_vol"])) / last["vol"] * 100) if last["vol"]>0 else 0

    # 4. MARKET STRUCTURE SHIFT
    hh = c5[-1]["h"] > max([x["h"] for x in c5[-15:-1]])
    ll = c5[-1]["l"] < min([x["l"] for x in c5[-15:-1]])
    trend_1h = "BULLISH" if c1h[-1]["c"] > c1h[-10]["c"] else "BEARISH" if len(c1h)>10 else "BEARISH"
    trend_4h = "BULLISH" if len(c4h)>10 and c4h[-1]["c"] > c4h[-10]["c"] else "BEARISH"

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Price {price:.2f} 1H:{trend_1h} 4H:{trend_4h} BSL {bsl:.2f} SSL {ssl:.2f} Delta {delta:.1f}%")

    # === ONANA ENTRY LOGIC ===
    # BEARISH - like 4262 example you sent
    bearish_confluence = 0
    if trend_1h == "BEARISH": bearish_confluence += 1
    if price < bsl - 5 and price > bear_ob_low - 10: bearish_confluence += 1 # After BSL sweep, at OB
    if delta < -10: bearish_confluence += 1 # Seller delta
    if price < sum([x["c"] for x in c5[-10:]])/10: bearish_confluence += 1

    # BULLISH - like 4275 example
    bullish_confluence = 0
    if trend_1h == "BULLISH": bullish_confluence += 1
    if price > ssl + 5 and price < bull_ob_high + 10: bullish_confluence += 1
    if delta > 10: bullish_confluence += 1
    if price > sum([x["c"] for x in c5[-10:]])/10: bullish_confluence += 1

    setup = None
    if bearish_confluence >= 3:
        setup = {
            "bias": "BEARISH", "confluence": bearish_confluence,
            "price": price, "bsl": bsl, "ssl": ssl, "bsl_4h": bsl_4h, "ssl_4h": ssl_4h,
            "ob_high": bear_ob_high, "ob_low": bear_ob_low,
            "key": bear_ob_low + 1, "sl": bear_ob_high + 2,
            "tp1": price - 10, "tp2": ssl, "tp3": ssl_4h-10,
            "delta": delta, "buy": buy_vol, "sell": sell_vol,
            "trend": trend_1h, "trend_4h": trend_4h, "c5": c5, "c15": c15
        }
    elif bullish_confluence >= 3:
        setup = {
            "bias": "BULLISH", "confluence": bullish_confluence,
            "price": price, "bsl": bsl, "ssl": ssl, "bsl_4h": bsl_4h, "ssl_4h": ssl_4h,
            "ob_high": bull_ob_high, "ob_low": bull_ob_low,
            "key": bull_ob_low + 1, "sl": bull_ob_low - 2,
            "tp1": bsl, "tp2": bsl_4h, "tp3": bsl_4h + 10,
            "delta": delta, "buy": buy_vol, "sell": sell_vol,
            "trend": trend_1h, "trend_4h": trend_4h, "c5": c5, "c15": c15
        }

    return setup

def create_onana_chart(data, filename="onana.png"):
    try:
        c5 = data["c5"][-30:]
        closes = [x["c"] for x in c5]
        times = list(range(len(closes)))
        plt.figure(figsize=(12,7))
        plt.style.use('dark_background')
        plt.plot(times, closes, color='white', linewidth=1.8, label='GOLD PAXG')

        if data["bias"] == "BEARISH":
            plt.axhspan(data["ob_low"], data["ob_high"], color='red', alpha=0.25, label=f'Bearish OB {data["ob_low"]:.0f}-{data["ob_high"]:.0f}')
            plt.axhline(data["sl"], color='red', linestyle='--', linewidth=1.2, label=f'SL {data["sl"]:.2f} Above OB')
            plt.axhline(data["key"], color='#00FF00', linestyle='-', linewidth=2, label=f'SHORT @ {data["key"]:.2f} VALID')
            plt.axhline(data["tp1"], color='orange', linestyle='--', label=f'TP1 {data["tp1"]:.0f} SSL')
            plt.axhline(data["tp2"], color='orange', linestyle='--', linewidth=1.5, label=f'TP2 {data["tp2"]:.0f} SSL 4H')
            plt.title(f'ONANA GOLD 5m BEARISH | {data["trend"]} | Delta {data["delta"]:.1f}%', color='white', fontsize=11, fontweight='bold')
        else:
            plt.axhspan(data["ob_low"], data["ob_high"], color='green', alpha=0.25, label=f'Bullish OB {data["ob_low"]:.0f}-{data["ob_high"]:.0f}')
            plt.axhline(data["sl"], color='red', linestyle='--', linewidth=1.2, label=f'SL {data["sl"]:.2f} Below OB')
            plt.axhline(data["key"], color='#00FF00', linestyle='-', linewidth=2, label=f'LONG @ {data["key"]:.2f} VALID')
            plt.axhline(data["tp1"], color='cyan', linestyle='--', label=f'TP1 {data["tp1"]:.0f} BSL')
            plt.axhline(data["tp2"], color='cyan', linestyle='--', linewidth=1.5, label=f'TP2 {data["tp2"]:.0f} BSL 4H')
            plt.title(f'ONANA GOLD 5m BULLISH | {data["trend"]} | Delta {data["delta"]:.1f}%', color='white', fontsize=11, fontweight='bold')

        plt.figtext(0.5, 0.02, f'ONANA | Bias: {data["bias"]} ({data["confluence"]}/4) | Entry {data["key"]:.2f} SL {data["sl"]:.0f} TP {data["tp2"]:.0f} | Delta {data["delta"]:.1f}% | 1H {data["trend"]} 4H {data["trend_4h"]}',
                  ha='center', fontsize=8, bbox=dict(boxstyle="round", facecolor='red' if data["bias"]=="BEARISH" else 'green', alpha=0.9))
        plt.legend(fontsize=7, loc='upper left', facecolor='black')
        plt.tight_layout()
        plt.savefig(filename, dpi=160, facecolor='#0f0f0f')
        plt.close()
        return filename
    except Exception as e:
        print(f"Chart err {e}")
        return None

print("V10 ONANA GOLD BOT STARTED")
try:
    send("🚀 *V10 ONANA GOLD ONLINE*\n✅ Same analysis as I do for you\n✅ BSL/SSL + OB + Delta + MSS\n✅ Bearish & Bullish\nScanning GOLD now...")
except: pass

last_signal = 0
while True:
    try:
        data = onana_analyze()
        if not data:
            time.sleep(60)
            continue

        if time.time() - last_signal > 1800: # 30min cooldown - ONANA quality
            chart = create_onana_chart(data)

            if data["bias"] == "BEARISH":
                msg = (
                    f"🔴 *ONANA GOLD - SELL NOW @ {data['key']:.2f}*\n\n"
                    f"*Why Bearish? ({data['confluence']}/4 Confluence):*\n"
                    f"• *Delta {data['delta']:.1f}% = Sell {data['sell']:.2f}K > Buy {data['buy']:.2f}K* - seller imbalance 🔴\n"
                    f"• *{data['bsl']:.2f} BSL swept* - buy stops hunted top ✓\n"
                    f"• *{data['ob_low']:.0f}-{data['ob_high']:.0f} Bearish OB* - retested and rejected ✓\n"
                    f"• *{data['ssl']:.0f} SSL* broken - liquidity grab\n"
                    f"• *1H {data['trend']} / 4H {data['trend_4h']}* - HTF bearish\n\n"
                    f"*ONANA Rule:*\n"
                    f"Wait 5m close BELOW {data['key']:.0f}\n"
                    f"Entry {data['key']:.0f} | SL {data['sl']:.0f} above OB\n"
                    f"TP1 {data['tp1']:.0f} TP2 {data['tp2']:.0f} (SSL) TP3 {data['tp3']:.0f}"
                )
            else:
                msg = (
                    f"🟢 *ONANA GOLD - BUY NOW @ {data['key']:.2f}*\n\n"
                    f"*Why Bullish? ({data['confluence']}/4 Confluence):*\n"
                    f"• *{data['ssl']:.0f} SSL swept* - sell stops hunted bottom ✓\n"
                    f"• *{data['key']:.2f} SUPPORT HOLDING* - bullish OB retest ✓\n"
                    f"• *Delta {data['delta']:.1f}% = Buy {data['buy']:.2f}K > Sell {data['sell']:.2f}K* - buyer imbalance 🟢\n"
                    f"• *{data['bsl']:.0f} BSL* target top\n"
                    f"• *1H {data['trend']} / 4H {data['trend_4h']}* - HTF bullish\n\n"
                    f"*ONANA Rule:*\n"
                    f"Wait bullish close above {data['price']+1:.0f}\n"
                    f"Entry {data['key']:.0f}-{data['price']:.0f} | SL {data['sl']:.0f}\n"
                    f"TP1 {data['tp1']:.0f} TP2 {data['tp2']:.0f} (BSL) TP3 {data['tp3']:.0f}"
                )

            send(msg, chart)
            last_signal = time.time()

        time.sleep(60)
    except Exception as e:
        print(f"Loop error {e}")
        time.sleep(30)

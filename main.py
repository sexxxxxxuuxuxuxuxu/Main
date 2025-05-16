
import requests
import os
import time

# Настройки от средата
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BINANCE_SYMBOL = "SOLUSDT"
INTERVAL = "1m"
LIMIT = 200

# Телеграм съобщение
def send_message(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
        response = requests.post(url, data=payload)
        print("Съобщение изпратено:", response.status_code)
    except Exception as e:
        print(f"Грешка при изпращане в Telegram: {e}")

# Извличане на данни от Binance
def get_binance_data():
    url = f"https://api.binance.com/api/v3/klines?symbol={BINANCE_SYMBOL}&interval={INTERVAL}&limit={LIMIT}"
    try:
        res = requests.get(url)
        if res.status_code != 200:
            print("Binance API грешка:", res.text)
            return None
        data = res.json()
        closes = [float(x[4]) for x in data]
        volumes = [float(x[5]) for x in data]
        return closes, volumes
    except Exception as e:
        print("Грешка при извличане на данни от Binance:", e)
        return None

# RSI изчисление
def calculate_rsi(prices, period=14):
    gains = []
    losses = []
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        gains.append(max(0, change))
        losses.append(max(0, -change))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)

# SMA изчисление
def calculate_sma(prices, period):
    if len(prices) < period:
        return None
    return round(sum(prices[-period:]) / period, 2)

# EMA изчисление
def calculate_ema(prices, period):
    if len(prices) < period:
        return None
    ema = prices[-period]
    multiplier = 2 / (period + 1)
    for price in prices[-period+1:]:
        ema = (price - ema) * multiplier + ema
    return ema

# MACD
def calculate_macd(prices):
    ema12 = calculate_ema(prices, 12)
    ema26 = calculate_ema(prices, 26)
    if ema12 is None or ema26 is None:
        return None
    return round(ema12 - ema26, 2)

# Основен цикъл
last_signal = None

print("Ботът стартира!")

while True:
    try:
        result = get_binance_data()
        if result is None:
            print("Пропускаме итерация...")
            time.sleep(60)
            continue

        prices, volumes = result
        current_price = prices[-1]
        rsi = calculate_rsi(prices)
        sma50 = calculate_sma(prices, 50)
        sma200 = calculate_sma(prices, 200)
        macd = calculate_macd(prices)
        avg_volume = sum(volumes[-50:]) / 50
        current_volume = volumes[-1]

        signals = []
        trend = None

        if rsi < 30:
            signals.append("RSI нисък (BUY)")
            trend = "buy"
        elif rsi > 70:
            signals.append("RSI висок (SELL)")
            trend = "sell"

        if sma50 and sma200:
            if sma50 > sma200:
                signals.append("SMA50 > SMA200 (BUY)")
                if not trend:
                    trend = "buy"
            elif sma50 < sma200:
                signals.append("SMA50 < SMA200 (SELL)")
                if not trend:
                    trend = "sell"

        if macd:
            if macd > 0:
                signals.append("MACD положителен (BUY)")
                if not trend:
                    trend = "buy"
            elif macd < 0:
                signals.append("MACD отрицателен (SELL)")
                if not trend:
                    trend = "sell"

        if current_volume > avg_volume * 1.5:
            signals.append("Обемът е над средния (силен тренд)")

        if len(signals) >= 3 and trend:
            if last_signal == trend:
                if trend == "buy":
                    take_profit = round(current_price * 1.05, 2)
                    stop_loss = round(current_price * 0.975, 2)
                else:
                    take_profit = round(current_price * 0.95, 2)
                    stop_loss = round(current_price * 1.025, 2)

                message = (
                    f"[SIGNAL - {trend.upper()}]"
"
                    f"Цена: ${current_price}
" +
                    "
".join(f"- {sig}" for sig in signals) +
                    f"

Take Profit: ${take_profit}
Stop Loss: ${stop_loss}"
                )
                send_message(message)
                print(">>> Сигнал изпратен в Telegram")

            last_signal = trend

        time.sleep(60)

    except Exception as e:
        print("⚠️ Грешка в основния цикъл:", e)
        time.sleep(30)

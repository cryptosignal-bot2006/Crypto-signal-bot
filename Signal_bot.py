import os
import json
import urllib.request
import urllib.parse

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

SYMBOLS = ["BTCUSDT", "ETHUSDT"]
INTERVAL = "15m"
LIMIT = 100


def get_json(url):
    with urllib.request.urlopen(url, timeout=20) as response:
        return json.loads(response.read().decode())


def ema(values, period):
    multiplier = 2 / (period + 1)
    result = [values[0]]

    for value in values[1:]:
        result.append(
            (value * multiplier) +
            (result[-1] * (1 - multiplier))
        )

    return result


def get_closes(symbol):
    url = (
        f"https://api.binance.com/api/v3/klines"
        f"?symbol={symbol}&interval={INTERVAL}&limit={LIMIT}"
    )

    candles = get_json(url)

    # Ignore candle that is still forming
    return [float(candle[4]) for candle in candles[:-1]]


def find_signal(symbol):
    closes = get_closes(symbol)

    fast = ema(closes, 9)
    slow = ema(closes, 21)

    previous_fast = fast[-2]
    previous_slow = slow[-2]

    current_fast = fast[-1]
    current_slow = slow[-1]

    entry = closes[-1]

    # BUY signal
    if previous_fast <= previous_slow and current_fast > current_slow:
        stop_loss = entry * 0.985
        take_profit = entry * 1.03

        return "BUY", entry, stop_loss, take_profit

    # SELL signal
    if previous_fast >= previous_slow and current_fast < current_slow:
        stop_loss = entry * 1.015
        take_profit = entry * 0.97

        return "SELL", entry, stop_loss, take_profit

    return None


def get_chat_ids():
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

    data = get_json(url)

    chat_ids = set()

    for update in data.get("result", []):
        message = update.get("message")

        if message:
            chat = message.get("chat", {})

            if chat.get("type") == "private":
                chat_id = chat.get("id")

                if chat_id:
                    chat_ids.add(chat_id)

    return chat_ids


def send_message(chat_id, message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    payload = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": message
    }).encode()

    request = urllib.request.Request(
        url,
        data=payload,
        method="POST"
    )

    urllib.request.urlopen(request, timeout=20)


def main():
    chat_ids = get_chat_ids()

    if not chat_ids:
        print("No Telegram chat found.")
        return

    for symbol in SYMBOLS:
        try:
            signal = find_signal(symbol)

            if signal:
                action, entry, stop_loss, take_profit = signal

                emoji = "🟢" if action == "BUY" else "🔴"

                message = (
                    f"{emoji} {action} SIGNAL\n\n"
                    f"💰 {symbol}\n"
                    f"📊 Timeframe: 15m\n\n"
                    f"🎯 Entry: {entry:.2f}\n"
                    f"🛑 Stop Loss: {stop_loss:.2f}\n"
                    f"✅ Take Profit: {take_profit:.2f}\n\n"
                    f"⚠️ Educational signal only.\n"
                    f"Not financial advice."
                )

                for chat_id in chat_ids:
                    send_message(chat_id, message)

                print(f"{action} signal sent for {symbol}")

            else:
                print(f"WAIT - no new signal for {symbol}")

        except Exception as error:
            print(f"Error with {symbol}: {error}")


if __name__ == "__main__":
    main()

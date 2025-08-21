"""
Alarm Commands – etkileşimli + tek satır
- Kaynak: services/market (Binance cache)
- /alarm, /alarmlist, /alarmstop, /alarmcancel
- PRICE_TOLERANCE (config.py)
- Eski alarm şemasından otomatik migrasyon (coin/coin_id → symbol)
"""

from __future__ import annotations
import threading
import time
import json
from typing import Dict, List, Any, Optional

from config import PRICE_TOLERANCE, ALARM_CHECK_INTERVAL, MAX_ALARMS_PER_USER
from services.market import start as market_start, get_price, to_binance_symbol

price_alarms: Dict[int, List[Dict[str, Any]]] = {}
user_states: Dict[int, Dict[str, Any]] = {}
ALARM_FILE = "alarms.json"

_monitor_thread: Optional[threading.Thread] = None
_monitor_running = False


# ---------------- yardımcılar ----------------
def _pretty(v: float) -> str:
    if v is None:
        return "—"
    if v >= 1:
        return f"${v:,.2f}"
    if v >= 0.01:
        return f"${v:.6f}"
    return f"${v:.8f}"

def _save_alarms():
    try:
        with open(ALARM_FILE, "w", encoding="utf-8") as f:
            json.dump(price_alarms, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Alarm kaydetme hatası: {e}")

def _load_alarms():
    global price_alarms
    try:
        with open(ALARM_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        price_alarms = {int(k): v for k, v in data.items()}
        _migrate_alarms()  # <<< eski kayıtları dönüştür
        print(f"⏰ Kaydedilmiş alarmlar: {sum(len(v) for v in price_alarms.values())}")
    except FileNotFoundError:
        price_alarms = {}
    except Exception as e:
        print(f"⚠️ Alarm yükleme hatası: {e}")
        price_alarms = {}

def _migrate_alarms():
    """Eski şemadaki (coin/coin_id) kayıtları yeni şemaya (symbol) çevirir."""
    changed = False
    for uid, alarms in list(price_alarms.items()):
        for a in alarms:
            if "symbol" not in a:
                # eski: {'coin': 'btc', 'coin_id': 'bitcoin', 'target': ..., 'direction': ...}
                sym = None
                if "coin" in a and a["coin"]:
                    sym = to_binance_symbol(str(a["coin"]))
                # coin_id'den sembole gidemezsek 'BTCUSDT' tahmini yok, o zaman coin üstünden gideceğiz
                if sym:
                    a["symbol"] = sym
                    changed = True
                else:
                    # son çare: coin alanını büyük harf olarak gösterimde kullanacağız
                    a["symbol"] = str(a.get("coin", "???")).upper()
                    changed = True
                # temizlik
                a.pop("coin_id", None)
                a.pop("coin", None)
    if changed:
        _save_alarms()

def _add_alarm(user_id: int, symbol: str, target: float, direction: str):
    price_alarms.setdefault(user_id, []).append({
        "symbol": symbol,
        "target": float(target),
        "direction": direction
    })
    _save_alarms()


# --------------- izleme döngüsü ---------------
def _monitor_loop(bot):
    global _monitor_running
    print(f"🔔 Alarm izleme ({ALARM_CHECK_INTERVAL}s) başladı.")
    while _monitor_running:
        try:
            for user_id, alarms in list(price_alarms.items()):
                for alarm in alarms[:]:
                    # symbol yoksa (tam göçmemiş veri) coin fallback
                    symbol = alarm.get("symbol") or to_binance_symbol(alarm.get("coin", "")) or str(alarm.get("coin", "???")).upper()
                    target = float(alarm["target"])
                    direction = alarm.get("direction", "up")

                    price = get_price(symbol)
                    if price is None:
                        continue

                    if direction == "up":
                        hit = price >= target * (1 - float(PRICE_TOLERANCE))
                    else:
                        hit = price <= target * (1 + float(PRICE_TOLERANCE))

                    if hit:
                        txt = (
                            f"🔔📈 <b>ALARM!</b>\n\n"
                            f"<b>{symbol}</b> hedefine ulaştı.\n"
                            f"🎯 Hedef: {_pretty(target)}\n"
                            f"💰 Fiyat: {_pretty(price)}\n\n"
                            f"ℹ️ Alarm tek seferliktir. Yeni alarm: /alarm {symbol}"
                        )
                        try:
                            bot.send_message(user_id, txt, parse_mode="HTML")
                        except Exception as e:
                            print(f"Mesaj gönderilemedi (uid={user_id}): {e}")
                        alarms.remove(alarm)
                        _save_alarms()
            time.sleep(ALARM_CHECK_INTERVAL)
        except Exception as e:
            print(f"🔁 Alarm döngü hatası: {e}")
            time.sleep(ALARM_CHECK_INTERVAL)

def _ensure_monitor_started(bot):
    global _monitor_thread, _monitor_running
    if _monitor_thread and _monitor_thread.is_alive():
        return
    _monitor_running = True
    _monitor_thread = threading.Thread(target=_monitor_loop, args=(bot,), daemon=True)
    _monitor_thread.start()


# ---------------- komutlar ----------------
def register_alarm_commands(bot):
    market_start()           # market servisi ayakta
    _load_alarms()           # alarmları yükle + migrate
    _ensure_monitor_started(bot)

    # — Öncelik: list/stop/cancel (bekleme modunda da çalışsın)
    @bot.message_handler(commands=["alarmlist"])
    def cmd_alarmlist(message):
        uid = message.chat.id
        # Eski sürümlerde farklı key kullanılmış olabilir; iki ihtimali de dene
        candidates = [uid, getattr(message.from_user, "id", uid)]
        alarms: List[Dict[str, Any]] = []
        for k in candidates:
            if k in price_alarms:
                alarms = price_alarms[k]
                break

        if not alarms:
            bot.send_message(uid, "🔕 Aktif alarm yok.")
            return

        lines = ["⏰ <b>Alarmların:</b>"]
        for i, a in enumerate(alarms, 1):
            sym = a.get("symbol") or str(a.get("coin", "???")).upper()
            direction = a.get("direction", "up")
            lines.append(f"{i}. {sym} → {_pretty(a.get('target'))} ({'⬆️' if direction=='up' else '⬇️'})")
        bot.send_message(uid, "\n".join(lines), parse_mode="HTML")

    @bot.message_handler(commands=["alarmstop"])
    def cmd_alarmstop(message):
        uid = message.chat.id
        price_alarms.pop(uid, None)
        _save_alarms()
        bot.send_message(uid, "🗑️ Tüm alarmların silindi.")

    @bot.message_handler(commands=["alarmcancel"])
    def cmd_alarmcancel(message):
        user_states.pop(getattr(message.from_user, "id", None), None)
        bot.send_message(message.chat.id, "❎ Alarm kurulumu iptal edildi.")

    # — /alarm —
    @bot.message_handler(commands=["alarm"])
    def cmd_alarm(message):
        parts = message.text.strip().split()
        if len(parts) == 1:
            bot.send_message(
                message.chat.id,
                "⏰ <b>Fiyat Alarmı</b>\n\n"
                "Kullanım:\n"
                "• <code>/alarm btc</code>  → hedef fiyatı sorar\n"
                "• <code>/alarm btc 117150</code>  → tek satırda kurar\n\n"
                "ℹ️ Liste: <code>/alarmlist</code>",
                parse_mode="HTML"
            )
            return

        coin = parts[1]
        symbol = to_binance_symbol(coin)
        if not symbol:
            bot.send_message(message.chat.id, f"❌ Coin bulunamadı: {coin.upper()}")
            return

        # Tek satır modu
        if len(parts) >= 3:
            try:
                target = float(parts[2].replace(",", "").replace("$", ""))
            except ValueError:
                bot.send_message(message.chat.id, "⚠️ Geçerli bir fiyat gir (örn: 117150)")
                return

            cur = get_price(symbol)
            direction = "up" if (cur is None or target >= cur) else "down"

            alarms = price_alarms.setdefault(message.chat.id, [])
            if len(alarms) >= MAX_ALARMS_PER_USER:
                bot.send_message(message.chat.id, f"⚠️ En fazla {MAX_ALARMS_PER_USER} alarm ekleyebilirsin.")
                return

            _add_alarm(message.chat.id, symbol, target, direction)
            bot.send_message(
                message.chat.id,
                f"✅ <b>Alarm Kuruldu!</b>\n{symbol} hedef: {_pretty(target)}",
                parse_mode="HTML"
            )
            return

        # Etkileşimli mod
        cur = get_price(symbol)
        cur_txt = _pretty(cur) if cur is not None else "—"
        user_states[message.from_user.id] = {"state": "waiting_price", "symbol": symbol, "current": cur}
        bot.send_message(
            message.chat.id,
            f"🎯 <b>{symbol}</b> için hedef fiyatı yaz.\n"
            f"Şu anki fiyat: {cur_txt}\n"
            f"Örnek: 117150\n\n"
            f"İptal: /alarmcancel",
            parse_mode="HTML"
        )

    # — Fiyat beklerken girilen metin —
    @bot.message_handler(
        func=lambda m: (
            m.from_user
            and m.from_user.id in user_states
            and user_states[m.from_user.id].get("state") == "waiting_price"
            and isinstance(m.text, str)
            and not m.text.strip().startswith("/")  # komutlar geçsin
        )
    )
    def handle_target(message):
        st = user_states.get(message.from_user.id)
        if not st:
            return
        txt = (message.text or "").strip().replace(",", "").replace("$", "")
        try:
            target = float(txt)
            if target <= 0:
                raise ValueError
        except Exception:
            bot.send_message(message.chat.id, "❌ Geçerli bir sayı gir (örn: 117150).")
            return

        symbol = st["symbol"]
        cur = get_price(symbol)
        direction = "up" if (cur is None or target >= (cur or 0)) else "down"

        alarms = price_alarms.setdefault(message.chat.id, [])
        if len(alarms) >= MAX_ALARMS_PER_USER:
            bot.send_message(message.chat.id, "⚠️ Alarm limitine ulaştın.")
            user_states.pop(message.from_user.id, None)
            return

        _add_alarm(message.chat.id, symbol, target, direction)
        bot.send_message(
            message.chat.id,
            f"✅ <b>Alarm Kuruldu!</b>\n{symbol} hedef: {_pretty(target)}",
            parse_mode="HTML"
        )
        user_states.pop(message.from_user.id, None)


# not: _ensure_monitor_started(bot) register içinde çağrılıyor
def _ensure_monitor_started(bot):
    global _monitor_thread, _monitor_running
    if _monitor_thread and _monitor_thread.is_alive():
        return
    _monitor_running = True
    _monitor_thread = threading.Thread(target=_monitor_loop, args=(bot,), daemon=True)
    _monitor_thread.start()

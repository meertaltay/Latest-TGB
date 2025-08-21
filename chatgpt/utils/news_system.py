from __future__ import annotations
import os, json, threading
from telebot import TeleBot
from telebot.types import Message, ChatMemberUpdated

# -----------------------------
# Depolama: data/ klasörü
# -----------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE  = os.path.join(DATA_DIR, "news_users.json")
GROUPS_FILE = os.path.join(DATA_DIR, "news_groups.json")

# Eski kök konumlarla uyumluluk
LEGACY_USERS_FILES  = [os.path.join(BASE_DIR, "news_users.json")]
LEGACY_GROUPS_FILES = [
    os.path.join(BASE_DIR, "news_groups.json"),
    os.path.join(BASE_DIR, "news_targets.json"),
]

_lock = threading.Lock()
_users: set[int] = set()
_groups: set[int] = set()

def _load(path) -> list[int]:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ load({path}): {e}")
    return []

def _save(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(sorted(list(data)), f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ save({path}): {e}")

def _migrate():
    """Kökteki eski dosyaları data/ altına taşı."""
    global _users, _groups
    for src in LEGACY_USERS_FILES:
        if os.path.exists(src):
            try:
                arr = _load(src)
                before = len(_users)
                _users.update(int(x) for x in arr)
                if len(_users) > before:
                    print(f"🔁 migrate: {os.path.basename(src)} -> users +{len(_users)-before}")
            except Exception as e:
                print("migrate users err:", e)
    for src in LEGACY_GROUPS_FILES:
        if os.path.exists(src):
            try:
                arr = _load(src)
                before = len(_groups)
                _groups.update(int(x) for x in arr)
                if len(_groups) > before:
                    print(f"🔁 migrate: {os.path.basename(src)} -> groups +{len(_groups)-before}")
            except Exception as e:
                print("migrate groups err:", e)
    _save(USERS_FILE, _users)
    _save(GROUPS_FILE, _groups)

def _init_load():
    global _users, _groups
    _users  = set(int(x) for x in _load(USERS_FILE))
    _groups = set(int(x) for x in _load(GROUPS_FILE))
    _migrate()
    print(f"📰 Haber kayıtları: {_users and len(_users) or 0} kullanıcı, {_groups and len(_groups) or 0} grup")

def add_active_user(uid: int):
    with _lock:
        if uid not in _users:
            _users.add(int(uid))
            _save(USERS_FILE, _users)
            print(f"➕ kullanıcı eklendi: {uid} (toplam: {len(_users)})")

def add_active_group(gid: int):
    with _lock:
        if gid not in _groups:
            _groups.add(int(gid))
            _save(GROUPS_FILE, _groups)
            print(f"➕ grup eklendi: {gid} (toplam: {len(_groups)})")

def remove_group(gid: int):
    with _lock:
        if gid in _groups:
            _groups.discard(int(gid))
            _save(GROUPS_FILE, _groups)
            print(f"➖ grup çıkarıldı: {gid} (toplam: {len(_groups)})")

def get_news_stats():
    return {
        "active_users": len(_users),
        "active_groups": len(_groups),
        "users": sorted(list(_users)),
        "groups": sorted(list(_groups)),
    }

def register_news_forwarding(bot: TeleBot):
    """Kanal postlarını herkese ilet + otomatik kayıt ve grup üyeligi yönetimi."""
    _init_load()

    # 1) Kanal postu geldiğinde herkes/gruplarına FORWARD et
    @bot.channel_post_handler(func=lambda m: True)
    def _on_channel_post(message: Message):
        failed_u = failed_g = 0

        # Özel kullanıcılar
        for uid in list(_users):
            try:
                bot.forward_message(
                    chat_id=uid,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id
                )
            except Exception as e:
                failed_u += 1
                print(f"⚠️ forward user({uid}): {e}")

        # Gruplar
        for gid in list(_groups):
            try:
                bot.forward_message(
                    chat_id=gid,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id
                )
            except Exception as e:
                failed_g += 1
                print(f"⚠️ forward group({gid}): {e}")

        print(f"📢 Haber gönderildi: {len(_users)-failed_u} kullanıcı, {len(_groups)-failed_g} grup "
              f"(başarısız: u={failed_u}, g={failed_g})")

    # 2) Bot gruba eklendi/çıkarıldı
    @bot.my_chat_member_handler(func=lambda upd: True)
    def _on_my_chat_member(upd: ChatMemberUpdated):
        try:
            c = upd.chat
            if c.type not in ("group", "supergroup"):
                return
            st = upd.new_chat_member.status  # 'member','administrator','left','kicked',...
            if st in ("member", "administrator"):
                add_active_group(c.id)
            elif st in ("left", "kicked"):
                remove_group(c.id)
        except Exception as e:
            print("my_chat_member err:", e)

    # 3) Komut olmayan metinlerde otomatik kayıt (özel & grup)
    @bot.message_handler(
        content_types=['text'],
        func=lambda m: (m.text is not None) and (not m.text.strip().startswith('/'))
    )
    def _auto_register(message: Message):
        try:
            c = message.chat
            if c.type == "private":
                add_active_user(c.id)
            elif c.type in ("group", "supergroup"):
                add_active_group(c.id)
        except Exception as e:
            print("auto_register err:", e)

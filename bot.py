import json
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

with open("catalog.json", "r", encoding="utf-8") as f:
    catalog = json.load(f)

bot = Bot(token=config["token"])
dp = Dispatcher(bot)

user_data = {}

def get_main_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    for category in catalog:
        kb.add(InlineKeyboardButton(category, callback_data=f"cat|{category}"))
    kb.add(InlineKeyboardButton("🛒 Корзина", callback_data="cart"))
    return kb

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    user_data[msg.from_user.id] = {"cart": []}
    await msg.answer("Добро пожаловать! Выберите категорию:", reply_markup=get_main_keyboard())

@dp.callback_query_handler(lambda c: c.data.startswith("cat|"))
async def category_handler(call: types.CallbackQuery):
    _, cat = call.data.split("|")
    subcats_or_items = catalog[cat]
    if isinstance(subcats_or_items, dict):
        kb = InlineKeyboardMarkup()
        for sub in subcats_or_items:
            kb.add(InlineKeyboardButton(sub, callback_data=f"sub|{cat}|{sub}"))
        await call.message.edit_text(f"📂 {cat} — выберите подкатегорию:", reply_markup=kb)
    elif isinstance(subcats_or_items, list):
        await list_items(call.message, subcats_or_items, cat)

@dp.callback_query_handler(lambda c: c.data.startswith("sub|"))
async def subcategory_handler(call: types.CallbackQuery):
    _, cat, sub = call.data.split("|")
    items = catalog[cat][sub]
    await list_items(call.message, items, sub)

async def list_items(message, items, title):
    kb = InlineKeyboardMarkup()
    for i, item in enumerate(items):
        name = item["name"]
        price = item["price"]
        kb.add(InlineKeyboardButton(f"{name} — {price} UZS", callback_data=f"add|{title}|{i}"))
    kb.add(InlineKeyboardButton("⬅️ Назад", callback_data="back"))
    await message.edit_text(f"🛍 {title} — выберите товар:", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("add|"))
async def add_to_cart(call: types.CallbackQuery):
    _, cat, idx = call.data.split("|")
    idx = int(idx)
    user_id = call.from_user.id
    item = None
    for category in catalog:
        subcats = catalog[category]
        if isinstance(subcats, dict) and cat in subcats:
            item = subcats[cat][idx]
        elif isinstance(subcats, list) and category == cat:
            item = subcats[idx]
    if item:
        user_data.setdefault(user_id, {"cart": []})
        user_data[user_id]["cart"].append(item)
        await call.answer("Добавлено в корзину!")

@dp.callback_query_handler(lambda c: c.data == "cart")
async def show_cart(call: types.CallbackQuery):
    user_id = call.from_user.id
    cart = user_data.get(user_id, {}).get("cart", [])
if not cart:
    await call.message.edit_text("🛒 Ваша корзина пуста.")
    return

text = "🛒 Ваша корзина:\n"
total = 0
for i, item in enumerate(cart, start=1):
    text += f"{i}. {item['name']} — {item['price']} UZS\n"
    total += item["price"]
text += f"\n💰 Итого: {total} UZS"

keyboard = InlineKeyboardMarkup(row_width=2)
keyboard.add(
    InlineKeyboardButton("💳 RUB", callback_data="pay_rub"),
    InlineKeyboardButton("💳 UAH", callback_data="pay_uah"),
    InlineKeyboardButton("💳 UZS", callback_data="pay_uzs"),
    InlineKeyboardButton("💳 USDT", callback_data="pay_usdt")
)

await call.message.edit_text(
    text + "\n\nВыберите валюту для оплаты:",
    reply_markup=keyboard
)


@dp.callback_query_handler(lambda c: c.data.startswith("pay|"))
async def show_payment_details(call: types.CallbackQuery):
    _, cur = call.data.split("|")
    user_id = call.from_user.id
    cart = user_data.get(user_id, {}).get("cart", [])
    total = sum(item["price"] for item in cart)
    details = config["payment"].get(cur, "Нет данных")
    msg = (
    f"💳 Оплата в {cur} на сумму: {total} UZS\n"
    f"Реквизиты:\n"
    f"{details}\n\n"
    "После оплаты напишите админу."
)
    await call.message.edit_text(msg)
    # Уведомление админу
    admin_id = config["admin_id"]
    text = f"🆕 Новый заказ от @{call.from_user.username or call.from_user.id}:

"
    for i, item in enumerate(cart):
        text += f"{i+1}. {item['name']} — {item['price']} UZS
"
    text += f"
Итого: {total} UZS
Валюта: {cur}"
    await bot.send_message(admin_id, text)

@dp.callback_query_handler(lambda c: c.data == "back")
async def back_to_main(call: types.CallbackQuery):
    await call.message.edit_text("Выберите категорию:", reply_markup=get_main_keyboard())

if __name__ == "__main__":
    executor.start_polling(dp)

import logging
import os
import sqlite3
from datetime import datetime, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

AGENCY_NAME = "Emmanuel Digitals & CO"
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", "0"))
PORTFOLIO_URL = os.environ.get("PORTFOLIO_URL", "")
DB_PATH = os.environ.get("DB_PATH", "leads.db")

ABOUT_TEXT = (
    "Emmanuel Digitals & CO is a digital growth and automation agency helping global brands "
    "scale through social media, paid advertising, custom bots, automation, and crypto/forex marketing."
)
SERVICES_TEXT = (
    "🛠 <b>Our Services</b>\n\n"
    "• Social Media & Growth\n• Ad Management — Meta, Google & TikTok\n"
    "• Automation & Custom Bots\n• Crypto / Forex Marketing\n\n"
    "Tell us what you need and our team will help you find the right solution."
)
STATUS_LABELS = {"new": "🆕 New", "contacted": "📞 Contacted", "progress": "🔄 In Progress", "closed": "✅ Closed"}


def db():
    connection = sqlite3.connect(DB_PATH)
    connection.execute("""CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, name TEXT NOT NULL,
        username TEXT, created_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'new')""")
    connection.commit()
    return connection


def create_lead(user) -> int:
    connection = db()
    cursor = connection.execute(
        "INSERT INTO leads (user_id, name, username, created_at) VALUES (?, ?, ?, ?)",
        (user.id, user.full_name, user.username or "", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")),
    )
    lead_id = cursor.lastrowid
    connection.commit(); connection.close()
    return lead_id


def set_status(lead_id: int, status: str) -> None:
    connection = db()
    connection.execute("UPDATE leads SET status = ? WHERE id = ?", (status, lead_id))
    connection.commit(); connection.close()


def home_keyboard():
    rows = [
        [InlineKeyboardButton("🏢 About Agency", callback_data="about")],
        [InlineKeyboardButton("🛠 Our Services", callback_data="services")],
    ]
    if PORTFOLIO_URL:
        rows.append([InlineKeyboardButton("💼 Portfolio", url=PORTFOLIO_URL)])
    rows.append([InlineKeyboardButton("📩 Send a Request", callback_data="request")])
    return InlineKeyboardMarkup(rows)


def back_home_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Back to Home", callback_data="home")]])


def lead_admin_keyboard(lead_id: int, user_id: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Reply to Client", callback_data=f"reply:{user_id}")],
        [InlineKeyboardButton("📞 Contacted", callback_data=f"status:{lead_id}:contacted:{user_id}"),
         InlineKeyboardButton("🔄 In Progress", callback_data=f"status:{lead_id}:progress:{user_id}")],
        [InlineKeyboardButton("✅ Close Lead", callback_data=f"status:{lead_id}:closed:{user_id}")],
    ])


def is_admin(update: Update) -> bool:
    return bool(ADMIN_CHAT_ID and update.effective_chat and update.effective_chat.id == ADMIN_CHAT_ID)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        f"<b>{AGENCY_NAME}</b>\n\nDigital growth, marketing & automation for ambitious brands.\n\n"
        "Explore our agency, see what we do, view our portfolio, or send your project or issue directly to our team.",
        parse_mode=ParseMode.HTML, reply_markup=home_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"<b>{AGENCY_NAME}</b>\n\nUse /start to return home or 📩 Send a Request to contact our team.",
        parse_mode=ParseMode.HTML, reply_markup=home_keyboard())


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("awaiting_request", None)
    context.user_data.pop("reply_to_user", None)
    await update.message.reply_text("Cancelled.", reply_markup=home_keyboard())


async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "home":
        context.user_data["awaiting_request"] = False
        await query.edit_message_text(
            f"<b>{AGENCY_NAME}</b>\n\nDigital growth, marketing & automation for ambitious brands.\n\n"
            "Explore our agency, see what we do, view our portfolio, or send your project or issue directly to our team.",
            parse_mode=ParseMode.HTML, reply_markup=home_keyboard())
    elif data == "about":
        await query.edit_message_text(f"<b>🏢 About {AGENCY_NAME}</b>\n\n{ABOUT_TEXT}", parse_mode=ParseMode.HTML, reply_markup=back_home_keyboard())
    elif data == "services":
        await query.edit_message_text(SERVICES_TEXT, parse_mode=ParseMode.HTML, reply_markup=back_home_keyboard())
    elif data == "request":
        context.user_data["awaiting_request"] = True
        await query.edit_message_text(
            "<b>📩 Send a Request</b>\n\nTell us about your issue, project, goal, or what you need help with. "
            "Send your message here and it will be forwarded directly to our team.\n\n"
            "You can send text, a photo, document, or other supported Telegram message.\n\nUse /cancel if you change your mind.",
            parse_mode=ParseMode.HTML, reply_markup=back_home_keyboard())
    elif data.startswith("reply:"):
        if not is_admin(update):
            await query.answer("Admin access only.", show_alert=True); return
        target_user_id = int(data.split(":", 1)[1])
        context.user_data["reply_to_user"] = target_user_id
        await query.message.reply_text(
            f"💬 <b>Reply mode enabled</b>\n\nSend your reply now. It will be delivered to <code>{target_user_id}</code>.\n\nUse /cancel to exit.",
            parse_mode=ParseMode.HTML)
    elif data.startswith("status:"):
        if not is_admin(update):
            await query.answer("Admin access only.", show_alert=True); return
        _, lead_id_text, status, user_id_text = data.split(":", 3)
        lead_id, user_id = int(lead_id_text), int(user_id_text)
        set_status(lead_id, status)
        text = query.message.text or ""
        if "<b>Status:</b>" in text:
            text = text.split("\n\n<b>Status:</b>", 1)[0]
        await query.edit_message_text(
            text + f"\n\n<b>Status:</b> {STATUS_LABELS[status]}",
            parse_mode=ParseMode.HTML,
            reply_markup=lead_admin_keyboard(lead_id, user_id))
        await query.answer(f"Lead marked {STATUS_LABELS[status]}")


async def receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if is_admin(update) and context.user_data.get("reply_to_user"):
        target_user_id = context.user_data["reply_to_user"]
        try:
            await update.effective_message.copy(chat_id=target_user_id)
            await update.effective_message.reply_text("✅ Reply delivered to the client.")
        except Exception:
            logging.exception("Failed to deliver admin reply")
            await update.effective_message.reply_text("❌ Reply could not be delivered. The user may have blocked the bot.")
        context.user_data.pop("reply_to_user", None)
        return

    if not context.user_data.get("awaiting_request"):
        return
    if not ADMIN_CHAT_ID:
        logging.error("ADMIN_CHAT_ID is not configured")
        await update.effective_message.reply_text("Sorry, requests are temporarily unavailable. Please try again later.")
        return

    message, user = update.effective_message, update.effective_user
    lead_id = create_lead(user)
    username = f"@{user.username}" if user.username else "Not set"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    header = (
        f"📩 <b>NEW CLIENT REQUEST · #{lead_id}</b>\n\n"
        f"👤 <b>Client:</b> {user.full_name}\n🔗 <b>Username:</b> {username}\n"
        f"🆔 <b>Telegram ID:</b> <code>{user.id}</code>\n🕐 <b>Received:</b> {timestamp}\n"
        f"📌 <b>Status:</b> {STATUS_LABELS['new']}\n\n<b>REQUEST</b>"
    )
    sent_header = await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID, text=header, parse_mode=ParseMode.HTML,
        reply_markup=lead_admin_keyboard(lead_id, user.id))
    await message.copy(chat_id=ADMIN_CHAT_ID, reply_to_message_id=sent_header.message_id)
    context.user_data["awaiting_request"] = False
    await message.reply_text(
        f"<b>✅ Request received</b>\n\nThank you for contacting <b>{AGENCY_NAME}</b>. "
        "Your request has been sent directly to our team. We'll review it and get back to you.",
        parse_mode=ParseMode.HTML, reply_markup=back_home_keyboard())


async def leads_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    connection = db()
    rows = connection.execute("SELECT id,name,username,status,created_at FROM leads ORDER BY id DESC LIMIT 20").fetchall()
    connection.close()
    if not rows:
        await update.effective_message.reply_text("📭 No leads yet."); return
    lines = ["📋 <b>Recent Leads</b>", ""]
    for lead_id, name, username, status, created_at in rows:
        display_username = f"@{username}" if username else "no username"
        lines.append(f"#{lead_id} · {name} ({display_username}) · {STATUS_LABELS.get(status, status)} · {created_at}")
    await update.effective_message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logging.exception("Unhandled bot error", exc_info=context.error)


def main():
    token = os.environ.get("BOT_TOKEN")
    if not token: raise RuntimeError("BOT_TOKEN environment variable is required")
    logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
    db().close()
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("leads", leads_command))
    application.add_handler(CallbackQueryHandler(callbacks))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, receive_message))
    application.add_error_handler(error_handler)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

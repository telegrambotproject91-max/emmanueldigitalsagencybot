import logging
import os
import sqlite3
from datetime import datetime, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

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
    "• Social Media & Growth\n"
    "• Ad Management — Meta, Google & TikTok\n"
    "• Automation & Custom Bots\n"
    "• Crypto / Forex Marketing\n\n"
    "Tell us what you need and our team will help you find the right solution."
)

STATUS_LABELS = {
    "new": "🆕 New",
    "contacted": "📞 Contacted",
    "progress": "🔄 In Progress",
    "closed": "✅ Closed",
}


def db():
    connection = sqlite3.connect(DB_PATH)
    connection.execute(
        """CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            username TEXT,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'new'
        )"""
    )
    connection.commit()
    return connection


def create_lead(user) -> int:
    username = user.username if user and user.username else ""
    name = user.full_name if user else "Unknown"
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    connection = db()
    cursor = connection.execute(
        "INSERT INTO leads (user_id, name, username, created_at) VALUES (?, ?, ?, ?)",
        (user.id, name, username, created_at),
    )
    lead_id = cursor.lastrowid
    connection.commit()
    connection.close()
    return lead_id


def set_status(lead_id: int, status: str) -> None:
    connection = db()
    connection.execute("UPDATE leads SET status = ? WHERE id = ?", (status, lead_id))
    connection.commit()
    connection.close()


def home_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("🏢 About Agency", callback_data="about")],
        [InlineKeyboardButton("🛠 Our Services", callback_data="services")],
    ]
    if PORTFOLIO_URL:
        rows.append([InlineKeyboardButton("💼 Portfolio", url=PORTFOLIO_URL)])
    rows.append([InlineKeyboardButton("📩 Send a Request", callback_data="request")])
    return InlineKeyboardMarkup(rows)


def back_home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🏠 Back to Home", callback_data="home")]]
    )


def lead_admin_keyboard(lead_id: int, user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Reply to Client", callback_data=f"reply:{user_id}")],
        [
            InlineKeyboardButton("📞 Contacted", callback_data=f"status:{lead_id}:contacted"),
            InlineKeyboardButton("🔄 In Progress", callback_data=f"status:{lead_id}:progress"),
        ],
        [InlineKeyboardButton("✅ Close Lead", callback_data=f"status:{lead_id}:closed")],
    ])


def user_details(update: Update) -> str:
    user = update.effective_user
    username = f"@{user.username}" if user and user.username else "Not set"
    name = user.full_name if user else "Unknown"
    user_id = user.id if user else "Unknown"
    return f"👤 <b>Name:</b> {name}\n🔗 <b>Username:</b> {username}\n🆔 <b>Telegram ID:</b> <code>{user_id}</code>"


def is_admin(update: Update) -> bool:
    return bool(ADMIN_CHAT_ID and update.effective_chat and update.effective_chat.id == ADMIN_CHAT_ID)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["awaiting_request"] = False
    text = (
        f"<b>{AGENCY_NAME}</b>\n\n"
        "Digital growth, marketing & automation for ambitious brands.\n\n"
        "Explore our agency, see what we do, view our portfolio, or send your project or issue directly to our team."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=home_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"<b>{AGENCY_NAME}</b>\n\nUse /start to return to the home menu.\nUse 📩 Send a Request to contact our team directly.",
        parse_mode=ParseMode.HTML,
        reply_markup=home_keyboard(),
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["awaiting_request"] = False
    context.user_data.pop("reply_to_user", None)
    await update.message.reply_text("Request cancelled.", reply_markup=home_keyboard())


async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "home":
        context.user_data["awaiting_request"] = False
        await query.edit_message_text(
            f"<b>{AGENCY_NAME}</b>\n\nDigital growth, marketing & automation for ambitious brands.\n\n"
            "Explore our agency, see what we do, view our portfolio, or send your project or issue directly to our team.",
            parse_mode=ParseMode.HTML,
            reply_markup=home_keyboard(),
        )
    elif data == "about":
        await query.edit_message_text(
            f"<b>🏢 About {AGENCY_NAME}</b>\n\n{ABOUT_TEXT}",
            parse_mode=ParseMode.HTML,
            reply_markup=back_home_keyboard(),
        )
    elif data == "services":
        await query.edit_message_text(SERVICES_TEXT, parse_mode=ParseMode.HTML, reply_markup=back_home_keyboard())
    elif data == "request":
        context.user_data["awaiting_request"] = True
        await query.edit_message_text(
            "<b>📩 Send a Request</b>\n\nTell us about your issue, project, goal, or what you need help with. "
            "Send your message here and it will be forwarded directly to our team.\n\n"
            "You can send text, a photo, document, or other supported Telegram message.\n\n"
            "Use /cancel if you change your mind.",
            parse_mode=ParseMode.HTML,
            reply_markup=back_home_keyboard(),
        )
    elif data.startswith("reply:"):
        if not is_admin(update):
            await query.answer("Admin access only.", show_alert=True)
            return
        target_user_id = int(data.split(":", 1)[1])
        context.user_data["reply_to_user"] = target_user_id
        await query.message.reply_text(
            f"💬 <b>Reply mode enabled</b>\n\nSend your reply now. It will be delivered to Telegram user <code>{target_user_id}</code>.\n\nUse /cancel to exit reply mode.",
            parse_mode=ParseMode.HTML,
        )
    elif data.startswith("status:"):
        if not is_admin(update):
            await query.answer("Admin access only.", show_alert=True)
            return
        _, lead_id_text, status = data.split(":", 2)
        lead_id = int(lead_id_text)
        set_status(lead_id, status)
        old_text = query.message.text or ""
        status_line = f"\n\n<b>Status:</b> {STATUS_LABELS[status]}"
        if "<b>Status:</b>" in old_text:
            old_text = old_text.split("\n\n<b>Status:</b>", 1)[0]
        await query.edit_message_text(
            old_text + status_line,
            parse_mode=ParseMode.HTML,
            reply_markup=lead_admin_keyboard(lead_id, int(context.user_data.get("lead_user_id", 0))) if context.user_data.get("lead_user_id") else None,
        )
        await query.answer(f"Lead marked {STATUS_LABELS[status]}")


async def receive_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not is_admin(update) or "reply_to_user" not in context.user_data:
        return False

    target_user_id = context.user_data["reply_to_user"]
    try:
        await update.effective_message.copy(chat_id=target_user_id)
        await update.effective_message.reply_text("✅ Reply delivered to the client.")
    except Exception:
        logging.exception("Failed to deliver admin reply")
        await update.effective_message.reply_text("❌ I couldn't deliver that reply. The user may have blocked the bot.")
    finally:
        context.user_data.pop("reply_to_user", None)
    return True


async def receive_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await receive_admin_reply(update, context):
        return
    if not context.user_data.get("awaiting_request"):
        return

    if not ADMIN_CHAT_ID:
        logging.error("ADMIN_CHAT_ID is not configured")
        await update.effective_message.reply_text("Sorry, requests are temporarily unavailable. Please try again later.")
        return

    message = update.effective_message
    user = update.effective_user
    lead_id = create_lead(user)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    username = f"@{user.username}" if user and user.username else "Not set"
    name = user.full_name if user else "Unknown"
    user_id = user.id if user else 0

    header = (
        f"📩 <b>NEW CLIENT REQUEST · #{lead_id}</b>\n\n"
        f"👤 <b>Client:</b> {name}\n"
        f"🔗 <b>Username:</b> {username}\n"
        f"🆔 <b>Telegram ID:</b> <code>{user_id}</code>\n"
        f"🕐 <b>Received:</b> {timestamp}\n"
        f"📌 <b>Status:</b> {STATUS_LABELS['new']}\n\n"
        "<b>REQUEST</b>"
    )

    sent_header = await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=header,
        parse_mode=ParseMode.HTML,
        reply_markup=lead_admin_keyboard(lead_id, user_id),
    )
    context.user_data["lead_user_id"] = user_id
    await message.copy(chat_id=ADMIN_CHAT_ID, reply_to_message_id=sent_header.message_id)

    context.user_data["awaiting_request"] = False
    await message.reply_text(
        "<b>✅ Request received</b>\n\n"
        f"Thank you for contacting <b>{AGENCY_NAME}</b>. Your request has been sent directly to our team. We'll review it and get back to you.",
        parse_mode=ParseMode.HTML,
        reply_markup=back_home_keyboard(),
    )


async def leads_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update):
        return
    connection = db()
    rows = connection.execute(
        "SELECT id, name, username, status, created_at FROM leads ORDER BY id DESC LIMIT 20"
    ).fetchall()
    connection.close()
    if not rows:
        await update.effective_message.reply_text("📭 No leads yet.")
        return
    lines = ["📋 <b>Recent Leads</b>", ""]
    for lead_id, name, username, status, created_at in rows:
        display_username = f"@{username}" if username else "no username"
        lines.append(f"#{lead_id} · {name} ({display_username}) · {STATUS_LABELS.get(status, status)} · {created_at}")
    await update.effective_message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.exception("Unhandled bot error", exc_info=context.error)


def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable is required")

    logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
    db().close()

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("leads", leads_command))
    application.add_handler(CallbackQueryHandler(callbacks))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, receive_request))
    application.add_error_handler(error_handler)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

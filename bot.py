import logging
import os
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


def user_details(update: Update) -> str:
    user = update.effective_user
    username = f"@{user.username}" if user and user.username else "Not set"
    name = user.full_name if user else "Unknown"
    user_id = user.id if user else "Unknown"
    return f"👤 <b>Name:</b> {name}\n🔗 <b>Username:</b> {username}\n🆔 <b>Telegram ID:</b> <code>{user_id}</code>"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["awaiting_request"] = False
    text = (
        f"<b>{AGENCY_NAME}</b>\n\n"
        "Digital growth, marketing & automation for ambitious brands.\n\n"
        "Explore our agency, see what we do, view our portfolio, or send your project or issue directly to our team."
    )
    await update.message.reply_text(
        text, parse_mode=ParseMode.HTML, reply_markup=home_keyboard()
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"<b>{AGENCY_NAME}</b>\n\nUse /start to return to the home menu.\nUse 📩 Send a Request to contact our team directly.",
        parse_mode=ParseMode.HTML,
        reply_markup=home_keyboard(),
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data["awaiting_request"] = False
    await update.message.reply_text(
        "Request cancelled.", reply_markup=home_keyboard()
    )


async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "home":
        context.user_data["awaiting_request"] = False
        await query.edit_message_text(
            f"<b>{AGENCY_NAME}</b>\n\n"
            "Digital growth, marketing & automation for ambitious brands.\n\n"
            "Explore our agency, see what we do, view our portfolio, or send your project or issue directly to our team.",
            parse_mode=ParseMode.HTML,
            reply_markup=home_keyboard(),
        )
    elif query.data == "about":
        await query.edit_message_text(
            f"<b>🏢 About {AGENCY_NAME}</b>\n\n{ABOUT_TEXT}",
            parse_mode=ParseMode.HTML,
            reply_markup=back_home_keyboard(),
        )
    elif query.data == "services":
        await query.edit_message_text(
            SERVICES_TEXT,
            parse_mode=ParseMode.HTML,
            reply_markup=back_home_keyboard(),
        )
    elif query.data == "request":
        context.user_data["awaiting_request"] = True
        await query.edit_message_text(
            "<b>📩 Send a Request</b>\n\n"
            "Tell us about your issue, project, goal, or what you need help with. "
            "Send your message here and it will be forwarded directly to our team.\n\n"
            "You can send text, a photo, document, or other supported Telegram message.\n\n"
            "Use /cancel if you change your mind.",
            parse_mode=ParseMode.HTML,
            reply_markup=back_home_keyboard(),
        )


async def receive_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.user_data.get("awaiting_request"):
        return

    if not ADMIN_CHAT_ID:
        logging.error("ADMIN_CHAT_ID is not configured")
        await update.effective_message.reply_text(
            "Sorry, requests are temporarily unavailable. Please try again later."
        )
        return

    message = update.effective_message
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    header = (
        f"📩 <b>New Client Request</b>\n\n"
        f"{user_details(update)}\n"
        f"🕐 <b>Time:</b> {timestamp}\n\n"
        "<b>Message:</b>"
    )

    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=header,
        parse_mode=ParseMode.HTML,
    )
    await message.copy(chat_id=ADMIN_CHAT_ID)

    context.user_data["awaiting_request"] = False
    await message.reply_text(
        "<b>✅ Request received</b>\n\n"
        f"Thank you for contacting <b>{AGENCY_NAME}</b>. Your request has been sent directly to our team. "
        "We'll review it and get back to you.",
        parse_mode=ParseMode.HTML,
        reply_markup=back_home_keyboard(),
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.exception("Unhandled bot error", exc_info=context.error)


def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable is required")

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CallbackQueryHandler(callbacks))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, receive_request))
    application.add_error_handler(error_handler)

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

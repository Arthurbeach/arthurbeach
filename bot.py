# bot.py
import asyncio
import logging
import os

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
import httpx

# Load environment variables (safe for GitHub)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not TELEGRAM_TOKEN or not DEEPSEEK_API_KEY:
    raise ValueError("❌ Please set TELEGRAM_TOKEN and DEEPSEEK_API_KEY in your environment.")

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

user_state = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_state[user_id] = "awaiting_english_word"
    await update.message.reply_text(
        "🇬🇧➡️🇪🇸 ¡Hola! Envíame una **palabra en inglés** y te daré:\n"
        "• Una explicación clara en español\n"
        "• 5 palabras relacionadas en español con definiciones breves"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_state.get(user_id) != "awaiting_english_word":
        await update.message.reply_text("Por favor, escribe /start para comenzar.")
        return

    if not text or not text.replace("-", "").replace(" ", "").isalpha():
        await update.message.reply_text("❌ Por favor, envía una palabra válida en inglés (solo letras).")
        return

    english_word = text.lower()
    user_state[user_id] = None

    try:
        prompt = (
            f"Eres un experto en lingüística española. La palabra en inglés es: '{english_word}'.\n"
            f"Responde ÚNICAMENTE en español, con este formato exacto:\n\n"
            f"🔤 **Palabra en inglés**: {english_word}\n\n"
            f"📘 **Explicación**: [Definición clara y educativa en español.]\n\n"
            f"📚 **5 Palabras Relacionadas**:\n"
            f"1. **[Palabra 1]**: [Definición breve]\n"
            f"2. **[Palabra 2]**: [Definición breve]\n"
            f"3. **[Palabra 3]**: [Definición breve]\n"
            f"4. **[Palabra 4]**: [Definición breve]\n"
            f"5. **[Palabra 5]**: [Definición breve]\n\n"
            f"No añadas introducciones, despedidas ni texto adicional."
        )

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                DEEPSEEK_API_URL,
                headers={
                    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()

        if len(content) <= 4096:
            await update.message.reply_text(content, parse_mode="Markdown")
        else:
            for i in range(0, len(content), 4096):
                await update.message.reply_text(content[i:i+4096], parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error processing '{english_word}': {repr(e)}")
        await update.message.reply_text(
            "⚠️ Lo siento, hubo un error. Verifica que la palabra sea válida o inténtalo más tarde."
        )
    finally:
        user_state[user_id] = "awaiting_english_word"

async def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("✅ Bot iniciado.")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())

# app/services/report_service.py
from aiogram import Bot

# from aiogram.exceptions import TelegramAPIError  # Removed per user request
from loguru import logger as log

# from src.backend.core.config import settings  # Removed unused import


class ReportService:
    @staticmethod
    async def send_report(bot: Bot, user_id: int, username: str, report_type: str, report_text: str) -> bool:
        """
        Отправить форматированный отчет в административный канал.
        """
        # if not settings.bug_report_channel_id:
        #     log.warning("Отчет не отправлен: BUG_REPORT_CHANNEL_ID не задан.")
        #     return False

        # Форматирование текста (для логов)
        log.info(f"🐞 НОВЫЙ БАГ-РЕПОРТ | Пользователь: {username} (ID: {user_id}) | Категория: {report_type}")
        log.info(f"Текст отчета: {report_text[:200]}...")

        try:
            # await bot.send_message(chat_id=settings.bug_report_channel_id, text=message_text, parse_mode="HTML")
            log.info(f"Отчет от {user_id} ({report_type}) успешно сформирован (отправка в канал отключена).")
            return True
        except Exception as e:
            log.error(
                f"Ошибка при обработке отчета от {user_id}: {e}",
                exc_info=True,
            )
            return False

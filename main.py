#!/usr/bin/env python3
"""
Professional Telegram Scraper
Main entry point for the application
"""

import asyncio
import sys
from telethon import TelegramClient

from config import settings
from tools import TelegramTools


class TelegramScraper:
    """Main application class"""

    def __init__(self):
        # Ensure folders exist
        settings.ensure_folders()

        # Create session file path in sessions folder
        session_path = settings.sessions_folder / settings.session_file_prefix

        self.client = TelegramClient(
            str(session_path), settings.api_id, settings.api_hash
        )
        self.tools = TelegramTools(self.client)

    def display_menu(self) -> str:
        """Display main menu and get user choice"""
        print("🚀 Telegram Messages Scraper")
        print("=" * 55)

        choice = input(
            "\n📋 Выберите действие:\n"
            "1. 💬 Получить сообщения группы по периоду\n"
            "2. 🤖 Обработать и валидировать данные с AI\n"
            "3. 📊 Загрузить данные в Google Sheets\n"
            "\n👆 Ваш выбор: "
        )

        return choice.strip()

    async def run(self) -> None:
        """Main application loop"""
        try:
            choice = self.display_menu()

            if choice == "1":
                await self.tools.connect_client()
                await self.tools.fetch_group_messages()
            elif choice == "2":
                await self.tools.process_and_validate_data()
            elif choice == "3":
                await self.tools.upload_existing_data_to_sheets()
            else:
                print("❌ Неверный выбор")

        except ValueError:
            print("❌ Введите числовое значение")
        except KeyboardInterrupt:
            print("\n\n👋 Работа прервана пользователем")
        except Exception as e:
            print(f"❌ Произошла ошибка: {e}")
        finally:
            if self.client.is_connected():
                print("\n🔌 Отключение от Telegram...")
                try:
                    self.client.disconnect()
                except Exception:
                    pass


async def main() -> None:
    """Main entry point"""
    try:
        scraper = TelegramScraper()
        await scraper.run()
    except KeyboardInterrupt:
        print("\n👋 До свидания!")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Run the application
    asyncio.run(main())

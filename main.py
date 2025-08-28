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
        self.client = TelegramClient(
            settings.session_file_prefix, settings.api_id, settings.api_hash
        )
        self.tools = TelegramTools(self.client)

    def display_menu(self) -> str:
        """Display main menu and get user choice"""
        print("🚀 Professional Telegram Scraper")
        print("=" * 55)

        choice = input(
            "\\n📋 Выберите действие:\\n"
            "1. 👥 Список участников группы\\n"
            "2. ➕ Добавить пользователей в группу\\n"
            "3. 📄 Отобразить содержимое CSV\\n"
            "4. 💬 Получить сообщения группы по периоду\\n"
            "\\n👆 Ваш выбор: "
        )

        return choice.strip()

    async def run(self) -> None:
        """Main application loop"""
        try:
            await self.tools.connect_client()

            choice = self.display_menu()

            if choice == "1":
                await self.tools.list_users_in_group()
            elif choice == "2":
                await self.tools.add_users_to_group()
            elif choice == "3":
                self.tools.display_csv()
            elif choice == "4":
                await self.tools.fetch_group_messages()
            else:
                print("❌ Неверный выбор")

        except ValueError:
            print("❌ Введите числовое значение")
        except KeyboardInterrupt:
            print("\\n\\n👋 Работа прервана пользователем")
        except Exception as e:
            print(f"❌ Произошла ошибка: {e}")
        finally:
            if self.client.is_connected():
                print("\\n🔌 Отключение от Telegram...")
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
        print("\\n👋 До свидания!")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Validate required environment variables
    try:
        # This will raise validation error if env vars are missing
        _ = settings.api_id
        _ = settings.api_hash
        _ = settings.phone
    except Exception as e:
        print("❌ Ошибка конфигурации:")
        print(f"   {e}")
        print("\\n💡 Убедитесь, что в .env файле указаны:")
        print("   - API_ID")
        print("   - API_HASH")
        print("   - PHONE")
        sys.exit(1)

    # Run the application
    asyncio.run(main())

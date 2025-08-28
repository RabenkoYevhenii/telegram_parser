#!/usr/bin/env python3
"""
Оптимизированный асинхронный Telegram скрапер с расширенной информацией о пользователях
Быстрая обработка сообщений с поиском gaming-ключевых слов
"""

import os
import asyncio
import uuid
from pathlib import Path
from telethon import TelegramClient
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import (
    InputPeerEmpty,
    InputChannel,
    InputUser,
)
from telethon.errors.rpcerrorlist import (
    PeerFloodError,
    UserPrivacyRestrictedError,
    FloodWaitError,
)
from telethon.tl.functions.channels import InviteToChannelRequest
import sys
import csv
import re
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

# Получаем переменные окружения
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
PHONE = os.environ.get("PHONE")

# Проверяем обязательные переменные
if not API_ID or not API_HASH or not PHONE:
    print("❌ Ошибка: Установите API_ID, API_HASH и PHONE в .env файле")
    sys.exit(1)

GAMING_KEYWORDS = [
    "igaming",
    "casino",
    "bet",
    "betting",
    "poker",
    "slots",
    "gambling",
    "game",
    "games",
    "jackpot",
    "lottery",
    "roulette",
    "payments",
    "payment",
    "crypto",
    "bitcoin",
    "trading",
    "forex",
    "affiliate",
    "партнер",
    "казино",
    "ставки",
    "игры",
    "азарт",
    "криптовалюта",
    "трейдинг",
    "партнёрка",
    "реферал",
    "гемблинг",
    "букмекер",
    "bookmaker",
    "спорт",
    "sport",
    "прогноз",
    "прогнозы",
    "капер",
    "capper",
    "tipster",
    "бинанс",
    "binance",
    "сигнал",
    "spin",
    "spinz",
    "vegas",
    "roll",
    "highroll",
    "betwin",
    "betwinner",
    "melbet",
    "1xbet",
    "1xcasino",
    "cpa",
    "revshare",
    "arbitrage",
    "арбитраж",
    "sportsbook",
    "offers",
    "офферы",
    "офера",
    "manager",
    "менеджер",
    "leads",
    "conversion",
    "deposit",
    "депозит",
    "bingo",
    "reel",
    "bizdev",
    "business development",
    "partners",
    "партнёры",
    "geo",
    "гео",
    "traf",
    "траф",
]


class FastTelegramScraper:
    def __init__(self):
        self.client = TelegramClient(PHONE, int(API_ID), API_HASH)  # type: ignore
        self._common_groups_cache = None
        self.data_folder = Path("data")

    def ensure_data_folder(self):
        """Создает папку data если её нет"""
        self.data_folder.mkdir(exist_ok=True)

    def generate_filename(self, prefix: str, group_title: str) -> str:
        """Генерирует имя файла с UUID"""
        self.ensure_data_folder()
        sanitized_title = re.sub("[^a-z0-9]+", "-", group_title.lower())
        unique_id = str(uuid.uuid4())[:8]  # Короткий UUID
        filename = f"{prefix}-{sanitized_title}-{unique_id}.csv"
        return str(self.data_folder / filename)

    async def connect(self):
        """Подключение к Telegram"""
        print("🔌 Подключение к Telegram...")
        await self.client.connect()
        if not await self.client.is_user_authorized():
            await self.client.send_code_request(PHONE)  # type: ignore
            code = input("📱 Введите код подтверждения: ")
            await self.client.sign_in(PHONE, code)  # type: ignore
        print("✅ Успешно подключен!")

    async def get_user_fast_info(self, user):
        """Быстрое получение информации о пользователе без API запросов"""
        info = {
            "bio": "",
            "gaming_keywords": "",
            "common_groups": "",
        }

        try:
            # Проверяем тип объекта
            if hasattr(user, "__class__"):
                class_name = user.__class__.__name__
                if "Channel" in class_name or "Chat" in class_name:
                    info["bio"] = "CHANNEL"
                    return info

            # Проверяем, если это бот
            is_bot = getattr(user, "bot", False)
            if is_bot:
                info["bio"] = "BOT"
                return info

            # Кэшированные общие группы (получаем один раз)
            if self._common_groups_cache is None:
                try:
                    dialogs = await self.client.get_dialogs(limit=200)
                    self._common_groups_cache = [
                        d.title for d in dialogs if d.is_group
                    ][:10]
                except Exception:
                    self._common_groups_cache = []

            info["common_groups"] = "; ".join(self._common_groups_cache[:5])

        except Exception:
            # Игнорируем ошибки в быстром режиме
            pass

        return info

    async def get_user_detailed_info(self, user):
        """Подробная информация о пользователе с API запросами"""
        info = await self.get_user_fast_info(user)

        try:
            # Только для обычных пользователей получаем био
            if info["bio"] not in [
                "BOT",
                "CHANNEL",
            ]:
                full_user_info = await self.client(GetFullUserRequest(user.id))

                if (
                    hasattr(full_user_info, "full_user")
                    and full_user_info.full_user  # type: ignore
                    and full_user_info.full_user.about  # type: ignore
                ):

                    bio = full_user_info.full_user.about  # type: ignore
                    info["bio"] = bio

        except Exception as e:
            if "InputPeerChannel" not in str(e):
                username = getattr(user, "username", f"ID:{user.id}")
                print(f"⚠️  {username}: {str(e)}")

        return info

    async def list_users_in_group(self):
        """Экспорт участников группы в CSV с расширенной информацией"""
        result = await self.client(
            GetDialogsRequest(
                offset_date=None,
                offset_id=0,
                offset_peer=InputPeerEmpty(),
                limit=200,
                hash=0,
            )
        )

        print("\n📋 Доступные чаты:")
        for idx, chat in enumerate(result.chats):  # type: ignore
            print(f"{idx}: {chat.title}")

        try:
            group_idx = int(input("\n👆 Введите номер группы: "))
            target_group = result.chats[group_idx]  # type: ignore
        except (ValueError, IndexError):
            print("❌ Неверный номер группы")
            return

        print("👥 Получение участников...")
        participants = await self.client.get_participants(
            target_group, aggressive=True
        )

        # Спрашиваем режим обработки
        mode_choice = input(
            "\n🚀 Режим обработки:\n1. 🔥 Быстрый (без API запросов)\n2. 🔍 Подробный (с био)\n👆 Выбор: "
        )
        fast_mode = mode_choice == "1"

        # Генерируем имя файла с UUID
        prefix = "members"
        filename = self.generate_filename(prefix, target_group.title)

        print(f"💾 Сохранение в {filename}...")

        with open(filename, "w", encoding="UTF-8", newline="") as file:
            writer = csv.writer(file, delimiter=",")
            writer.writerow(
                [
                    "username",
                    "user_id",
                    "access_hash",
                    "name",
                    "group",
                    "group_id",
                    "bio",
                    "gaming_keywords",
                    "common_groups",
                ]
            )

            for i, user in enumerate(participants):
                if i % 50 == 0 or i == len(participants) - 1:
                    progress = (i + 1) / len(participants) * 100
                    print(
                        f"[{i+1}/{len(participants)}] Обработка: {progress:.1f}%"
                    )

                username = getattr(user, "username", "")
                name = " ".join(
                    filter(
                        None,
                        [
                            getattr(user, "first_name", ""),
                            getattr(user, "last_name", ""),
                        ],
                    )
                )

                # Выбираем режим обработки
                if fast_mode:
                    info = await self.get_user_fast_info(user)
                    await asyncio.sleep(0.1)  # Минимальная задержка
                else:
                    info = await self.get_user_detailed_info(user)
                    await asyncio.sleep(0.5)  # Задержка для API

                writer.writerow(
                    [
                        username,
                        user.id,
                        getattr(user, "access_hash", ""),
                        name,
                        target_group.title,
                        target_group.id,
                        info["bio"],
                        info["gaming_keywords"],
                        info["common_groups"],
                    ]
                )

        print(f"✅ Сохранено {len(participants)} участников в {filename}")

    async def fetch_group_messages(self):
        """Быстрое получение сообщений группы"""
        result = await self.client(
            GetDialogsRequest(
                offset_date=None,
                offset_id=0,
                offset_peer=InputPeerEmpty(),
                limit=200,
                hash=0,
            )
        )

        print("\n📋 Доступные чаты:")
        for idx, chat in enumerate(result.chats):  # type: ignore
            print(f"{idx}: {chat.title}")

        try:
            group_idx = int(input("\n👆 Введите номер группы: "))
            target_group = result.chats[group_idx]  # type: ignore
        except (ValueError, IndexError):
            print("❌ Неверный номер группы")
            return

        print("\n📅 Варианты периода:")
        print("1. Дни")
        print("2. Недели")
        print("3. Месяцы")

        try:
            period_choice = int(input("👆 Выберите тип периода: "))
            period_map = {1: "days", 2: "weeks", 3: "months"}
            period_type = period_map.get(period_choice)

            if not period_type:
                print("❌ Неверный выбор периода")
                return

            quantity = int(input(f"🔢 Введите количество {period_type}: "))
        except ValueError:
            print("❌ Неверный ввод")
            return

        # Режим обработки
        mode_choice = input(
            "\n🚀 Режим обработки:\n1. 🔥 Быстрый (только имена)\n2. 🔍 Подробный (с био)\n👆 Выбор: "
        )
        fast_mode = mode_choice == "1"

        # Расчет дат
        end_date = datetime.now(timezone.utc)
        if period_type == "days":
            start_date = end_date - timedelta(days=quantity)
        elif period_type == "weeks":
            start_date = end_date - timedelta(weeks=quantity)
        elif period_type == "months":
            start_date = end_date - timedelta(days=quantity * 30)
        else:
            return

        print(
            f'\n📥 Получение сообщений с {start_date.strftime("%Y-%m-%d")} по {end_date.strftime("%Y-%m-%d")}...'
        )

        messages = []
        try:
            async for message in self.client.iter_messages(target_group):
                if message.date < start_date:
                    break
                if message.date <= end_date:
                    messages.append(message)

                if len(messages) % 100 == 0:
                    print(f"📝 Получено {len(messages)} сообщений...")
        except Exception as e:
            print(f"❌ Ошибка получения сообщений: {str(e)}")
            return

        # Генерируем имя файла с UUID
        prefix = "messages"
        filename = self.generate_filename(prefix, target_group.title)

        print(f"💾 Сохранение {len(messages)} сообщений в {filename}...")

        users_cache = {}

        with open(filename, "w", encoding="UTF-8", newline="") as file:
            writer = csv.writer(file, delimiter=",")
            writer.writerow(
                [
                    "message_id",
                    "date",
                    "sender_id",
                    "sender_username",
                    "sender_name",
                    "message_text",
                    "group",
                    "group_id",
                    "sender_bio",
                    "message_gaming_keywords",
                    "sender_common_groups",
                ]
            )

            for i, message in enumerate(messages):
                if i % 25 == 0 or i == len(messages) - 1:
                    progress = (i + 1) / len(messages) * 100
                    print(
                        f"[{i+1}/{len(messages)}] Обработка: {progress:.1f}%"
                    )

                # Базовая информация об отправителе
                sender_info = {
                    "username": "",
                    "id": "",
                    "name": "",
                    "bio": "",
                    "gaming_keywords": "",
                    "common_groups": "",
                }

                if message.sender:
                    sender_info["id"] = message.sender.id
                    sender_info["name"] = " ".join(
                        filter(
                            None,
                            [
                                getattr(message.sender, "first_name", ""),
                                getattr(message.sender, "last_name", ""),
                            ],
                        )
                    )

                    if (
                        hasattr(message.sender, "username")
                        and message.sender.username
                    ):
                        sender_info["username"] = message.sender.username

                    # Кэшируем информацию о пользователях
                    if sender_info["id"] not in users_cache:
                        if fast_mode:
                            user_info = await self.get_user_fast_info(
                                message.sender
                            )
                        else:
                            # Проверяем тип отправителя перед детальным запросом
                            is_bot = getattr(message.sender, "bot", False)
                            is_channel = (
                                "Channel" in message.sender.__class__.__name__
                                if hasattr(message.sender, "__class__")
                                else False
                            )

                            if is_bot or is_channel:
                                user_info = await self.get_user_fast_info(
                                    message.sender
                                )
                            else:
                                user_info = await self.get_user_detailed_info(
                                    message.sender
                                )
                                await asyncio.sleep(
                                    0.2
                                )  # Минимальная задержка для API

                        users_cache[sender_info["id"]] = user_info
                    else:
                        user_info = users_cache[sender_info["id"]]

                    sender_info.update(
                        {
                            "bio": user_info["bio"],
                            "gaming_keywords": user_info["gaming_keywords"],
                            "common_groups": user_info["common_groups"],
                        }
                    )

                message_text = message.message or ""
                message_text = message_text.replace("\n", " ").replace(
                    "\r", " "
                )

                # Поиск gaming keywords только в тексте сообщения
                message_keywords = ""
                if message_text:
                    message_lower = message_text.lower()
                    found_message_keywords = [
                        kw for kw in GAMING_KEYWORDS if kw in message_lower
                    ]
                    if found_message_keywords:
                        message_keywords = ", ".join(found_message_keywords)

                writer.writerow(
                    [
                        message.id,
                        message.date.strftime("%Y-%m-%d %H:%M:%S"),
                        sender_info["id"],
                        sender_info["username"],
                        sender_info["name"],
                        message_text,
                        target_group.title,
                        target_group.id,
                        sender_info["bio"],
                        message_keywords,
                        sender_info["common_groups"],
                    ]
                )

        print(f"✅ Сохранено {len(messages)} сообщений в {filename}")
        print(f"📊 Кэшировано {len(users_cache)} уникальных пользователей")

    async def add_users_to_group(self):
        """Добавление пользователей из CSV в группу"""
        if len(sys.argv) < 2:
            print("❌ Укажите файл CSV как аргумент")
            return

        input_file = sys.argv[1]
        users = []

        try:
            with open(input_file, encoding="UTF-8") as file:
                reader = csv.reader(file, delimiter=",", lineterminator="\n")
                next(reader)
                for row in reader:
                    if len(row) < 3:
                        continue
                    users.append(
                        {
                            "username": row[0],
                            "id": int(row[1]) if row[1] else 0,
                            "access_hash": int(row[2]) if row[2] else 0,
                        }
                    )
        except FileNotFoundError:
            print(f"❌ Файл {input_file} не найден")
            return

        result = await self.client(
            GetDialogsRequest(
                offset_date=None,
                offset_id=0,
                offset_peer=InputPeerEmpty(),
                limit=200,
                hash=0,
            )
        )

        groups = [chat for chat in result.chats if getattr(chat, "megagroup", False)]  # type: ignore

        print("\n📋 Доступные группы:")
        for idx, group in enumerate(groups):
            print(f"{idx}: {group.title}")

        try:
            group_idx = int(input("\n👆 Введите номер группы: "))
            target_group = groups[group_idx]
            target_channel = InputChannel(
                target_group.id, target_group.access_hash
            )
        except (ValueError, IndexError):
            print("❌ Неверный номер группы")
            return

        try:
            add_method = int(
                input("\n🔧 Метод добавления (1-по username, 2-по ID): ")
            )
        except ValueError:
            print("❌ Неверный выбор метода")
            return

        print(f"\n🚀 Начинаем добавление {len(users)} пользователей...")

        for i, user in enumerate(users):
            try:
                print(f'[{i+1}/{len(users)}] Добавляем {user["username"]}')

                if add_method == 1:
                    user_to_add = await self.client.get_input_entity(
                        user["username"]
                    )
                elif add_method == 2:
                    user_to_add = InputUser(user["id"], user["access_hash"])
                else:
                    break

                await self.client(InviteToChannelRequest(target_channel, [user_to_add]))  # type: ignore
                print("⏱️  Ожидание 60 секунд...")
                await asyncio.sleep(60)

            except PeerFloodError:
                print("🚫 Ошибка флуда. Останавливаемся.")
                break
            except UserPrivacyRestrictedError:
                print("🔒 Ограничения приватности. Пропускаем.")
            except FloodWaitError as e:
                print(f"⏳ Флуд лимит. Ожидание {e.seconds} секунд...")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                print(f"❌ Ошибка: {str(e)}")

    def display_csv(self):
        """Отображение содержимого CSV файла"""
        if len(sys.argv) < 2:
            # Показываем доступные файлы в папке data
            self.ensure_data_folder()
            data_files = list(self.data_folder.glob("*.csv"))
            if data_files:
                print("📁 Доступные файлы в папке data:")
                for i, file in enumerate(data_files):
                    print(f"{i+1}. {file.name}")

                try:
                    choice = int(input("\n👆 Выберите файл (номер): ")) - 1
                    if 0 <= choice < len(data_files):
                        filename = str(data_files[choice])
                    else:
                        print("❌ Неверный номер файла")
                        return
                except ValueError:
                    print("❌ Введите число")
                    return
            else:
                print("❌ Нет файлов в папке data")
                return
        else:
            filename = sys.argv[1]
            # Если файл не найден, попробуем в папке data
            if not Path(filename).exists():
                data_file = self.data_folder / filename
                if data_file.exists():
                    filename = str(data_file)

        try:
            with open(filename, encoding="UTF-8") as file:
                reader = csv.reader(file, delimiter=",")
                print(f"\n📄 Содержимое файла: {Path(filename).name}")
                print("=" * 50)
                for i, row in enumerate(reader):
                    print(f"[{i+1}] {row}")
                    if i > 20:
                        print("... (показаны первые 20 строк)")
                        break
        except FileNotFoundError:
            print(f"❌ Файл {filename} не найден")
        except Exception as e:
            print(f"❌ Ошибка чтения файла: {e}")

    async def run(self):
        """Главное меню приложения"""
        print("🚀 Fast Telegram Scraper - Оптимизированная версия")
        print("=" * 55)

        await self.connect()

        choice = input(
            "\n📋 Выберите действие:\n"
            "1. 👥 Список участников группы\n"
            "2. ➕ Добавить пользователей в группу\n"
            "3. 📄 Отобразить содержимое CSV\n"
            "4. 💬 Получить сообщения группы по периоду\n"
            "\n👆 Ваш выбор: "
        )

        try:
            choice = int(choice)
            if choice == 1:
                await self.list_users_in_group()
            elif choice == 2:
                await self.add_users_to_group()
            elif choice == 3:
                self.display_csv()
            elif choice == 4:
                await self.fetch_group_messages()
            else:
                print("❌ Неверный выбор")
        except ValueError:
            print("❌ Введите числовое значение")
        except KeyboardInterrupt:
            print("\n\n👋 Работа прервана пользователем")
        finally:
            print("\n🔌 Отключение от Telegram...")
            self.client.disconnect()


async def main():
    scraper = FastTelegramScraper()
    await scraper.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 До свидания!")

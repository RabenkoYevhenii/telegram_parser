"""
Tools module for Telegram Scraper
Contains all business logic functions
"""

import asyncio
import csv
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

from telethon import TelegramClient
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import InputPeerEmpty

from config import GamingKeywords, Settings


class TelegramTools:
    """Collection of tools for Telegram operations"""

    def __init__(self, client: TelegramClient):
        self.client = client
        self._common_groups_cache: Optional[List[str]] = None
        self.settings = Settings()
        self.settings.ensure_data_folder()

    def generate_filename(self, prefix: str, group_title: str) -> str:
        """Generate filename with UUID"""
        sanitized_title = re.sub(r"[^a-z0-9]+", "-", group_title.lower())
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{prefix}-{sanitized_title}-{unique_id}.csv"
        return str(self.settings.data_folder / filename)

    async def connect_client(self) -> None:
        """Connect to Telegram and authenticate"""
        print("🔌 Подключение к Telegram...")
        await self.client.connect()

        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.settings.phone)
            code = input("📱 Введите код подтверждения: ")
            await self.client.sign_in(self.settings.phone, code)

        print("✅ Успешно подключен!")

    async def get_user_fast_info(self, user: Any) -> Dict[str, str]:
        """Fast user info without API calls"""
        info = {
            "bio": "",
            "gaming_keywords": "",
            "common_groups": "",
        }

        try:
            # Check object type
            if hasattr(user, "__class__"):
                class_name = user.__class__.__name__
                if "Channel" in class_name or "Chat" in class_name:
                    info["bio"] = "CHANNEL"
                    return info

            # Check if bot
            is_bot = getattr(user, "bot", False)
            if is_bot:
                info["bio"] = "BOT"
                return info

            # Cache common groups (get once)
            if self._common_groups_cache is None:
                try:
                    dialogs = await self.client.get_dialogs(limit=200)
                    self._common_groups_cache = [
                        d.title for d in dialogs if d.is_group
                    ][: self.settings.max_cache_groups]
                except Exception:
                    self._common_groups_cache = []

            info["common_groups"] = "; ".join(
                self._common_groups_cache[: self.settings.max_common_groups]
            )

        except Exception:
            # Ignore errors in fast mode
            pass

        return info

    async def get_user_detailed_info(self, user: Any) -> Dict[str, str]:
        """Detailed user info with API calls"""
        info = await self.get_user_fast_info(user)

        try:
            # Only get bio for regular users
            if info["bio"] not in ["BOT", "CHANNEL"]:
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

    async def get_groups(self) -> List[Any]:
        """Get list of available groups"""
        result = await self.client(
            GetDialogsRequest(
                offset_date=None,
                offset_id=0,
                offset_peer=InputPeerEmpty(),
                limit=200,
                hash=0,
            )
        )
        return [
            chat for chat in result.chats if getattr(chat, "megagroup", False)  # type: ignore
        ]

    def display_groups(self, groups: List[Any]) -> None:
        """Display available groups to user"""
        print("\n📋 Доступные группы:")
        for idx, group in enumerate(groups):
            print(f"{idx}: {group.title}")

    def get_user_group_choice(self, groups: List[Any]) -> Any:
        """Get user's group selection"""
        try:
            group_idx = int(input("\n👆 Введите номер группы: "))
            return groups[group_idx]
        except (ValueError, IndexError):
            print("❌ Неверный номер группы")
            return None

    def get_processing_mode(self) -> bool:
        """Get processing mode from user"""
        mode_choice = input(
            "\n⚡ Выберите режим обработки:\n"
            "1. 🚀 Быстрый (только имена, без био)\n"
            "2. 🔍 Подробный (с получением био)\n"
            "👆 Ваш выбор: "
        )
        return mode_choice != "2"

    def get_period_input(self) -> tuple[Optional[str], int]:
        """Get period type and quantity from user"""
        period_type = input(
            "\n📅 Выберите период:\n"
            "1. 📆 Дни\n"
            "2. 📊 Недели\n"
            "3. 🗓️ Месяцы\n"
            "👆 Ваш выбор: "
        )

        period_map = {"1": "days", "2": "weeks", "3": "months"}
        period_type = period_map.get(period_type)

        if not period_type:
            print("❌ Неверный выбор периода")
            return None, 0

        try:
            quantity = int(input(f"🔢 Количество {period_type}: "))
            return period_type, quantity
        except ValueError:
            print("❌ Введите числовое значение")
            return None, 0

    def find_message_keywords(self, message_text: str) -> str:
        """Find gaming keywords in message text"""
        if not message_text:
            return ""

        message_lower = message_text.lower()
        found_keywords = [
            kw for kw in GamingKeywords.KEYWORDS if kw in message_lower
        ]

        return ", ".join(found_keywords) if found_keywords else ""

    async def fetch_group_messages(self) -> None:
        """Fetch group messages by period"""
        groups = await self.get_groups()
        if not groups:
            print("❌ Группы не найдены")
            return

        self.display_groups(groups)
        target_group = self.get_user_group_choice(groups)
        if not target_group:
            return

        period_type, quantity = self.get_period_input()
        if not period_type:
            return

        fast_mode = self.get_processing_mode()

        # Calculate date range
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
            f'\n📥 Получение сообщений с {start_date.strftime("%Y-%m-%d %H:%M:%S")} '
            f'по {end_date.strftime("%Y-%m-%d %H:%M:%S")} (UTC)...'
        )

        # Fetch messages
        messages = []
        try:
            async for message in self.client.iter_messages(target_group):
                if message.date < start_date:
                    break
                if message.date <= end_date:
                    messages.append(message)

                if len(messages) % 100 == 0:
                    latest_date = (
                        message.date.strftime("%Y-%m-%d %H:%M:%S")
                        if messages
                        else ""
                    )
                    print(
                        f"📝 Получено {len(messages)} сообщений... (последнее: {latest_date})"
                    )
        except Exception as e:
            print(f"❌ Ошибка получения сообщений: {str(e)}")
            return

        # Generate filename with UUID
        prefix = "messages"
        filename = self.generate_filename(prefix, target_group.title)

        print(f"💾 Сохранение {len(messages)} сообщений в {filename}...")

        users_cache = {}

        with open(
            filename, "w", encoding=self.settings.csv_encoding, newline=""
        ) as file:
            writer = csv.writer(
                file,
                delimiter=self.settings.csv_delimiter,
                lineterminator=self.settings.csv_line_terminator,
            )
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
                if (
                    i % self.settings.progress_update_frequency == 0
                    or i == len(messages) - 1
                ):
                    progress = (i + 1) / len(messages) * 100
                    message_date = message.date.strftime("%Y-%m-%d %H:%M:%S")
                    print(
                        f"[{i+1}/{len(messages)}] Обработка: {progress:.1f}% | Сообщение от: {message_date}"
                    )

                # Basic sender info
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

                    # Cache user information
                    if sender_info["id"] not in users_cache:
                        if fast_mode:
                            user_info = await self.get_user_fast_info(
                                message.sender
                            )
                        else:
                            # Check sender type before detailed request
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
                                await asyncio.sleep(self.settings.api_delay)

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
                message_text = message_text.replace("\\n", " ").replace(
                    "\\r", " "
                )

                # Find gaming keywords ONLY in message text
                message_keywords = self.find_message_keywords(message_text)

                writer.writerow(
                    [
                        message.id,
                        message.date.strftime("%Y-%m-%d %H:%M:%S UTC"),
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

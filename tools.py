"""
Tools module for Telegram Scraper
Contains all business logic functions
"""

import asyncio
import csv
import json
import os
import pickle
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

import httpx
from telethon import TelegramClient
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.types import InputPeerEmpty

try:
    from google.auth.transport.requests import Request
    from google.oauth2.service_account import (
        Credentials as ServiceAccountCredentials,
    )
    from google.oauth2.credentials import Credentials as OAuth2Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False
    # These will be handled at runtime with proper error messages


from config import GamingKeywords, Settings


class TelegramTools:
    """Collection of tools for Telegram operations"""

    def __init__(self, client: Optional[TelegramClient] = None):
        self.client = client
        self._common_groups_cache: Optional[List[str]] = None
        self.settings = Settings()
        self.settings.ensure_folders()  # Ensure both data and sessions folders exist

    def generate_filename(self, prefix: str, group_title: str) -> str:
        """Generate filename with UUID"""
        sanitized_title = re.sub(r"[^a-z0-9]+", "-", group_title.lower())
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{prefix}-{sanitized_title}-{unique_id}.csv"
        return str(self.settings.data_folder / filename)

    async def connect_client(self) -> None:
        """Connect to Telegram and authenticate"""
        if not self.client:
            raise ValueError("Telegram client not initialized")

        # Validate required environment variables
        try:
            if (
                not self.settings.api_id
                or not self.settings.api_hash
                or not self.settings.phone
            ):
                raise ValueError(
                    "Отсутствуют обязательные параметры Telegram API"
                )
        except Exception as e:
            print("❌ Ошибка конфигурации:")
            print(f"   {e}")
            print("\n💡 Убедитесь, что в .env файле указаны:")
            print("   - API_ID")
            print("   - API_HASH")
            print("   - PHONE")
            raise

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

            # Cache common groups (get once) - only if client is available
            if self.client and self._common_groups_cache is None:
                try:
                    dialogs = await self.client.get_dialogs(limit=200)
                    self._common_groups_cache = [
                        d.title for d in dialogs if d.is_group
                    ][: self.settings.max_cache_groups]
                except Exception:
                    self._common_groups_cache = []

            if self._common_groups_cache:
                info["common_groups"] = "; ".join(
                    self._common_groups_cache[
                        : self.settings.max_common_groups
                    ]
                )

        except Exception:
            # Ignore errors in fast mode
            pass

        return info

    async def get_user_detailed_info(self, user: Any) -> Dict[str, str]:
        """Detailed user info with API calls"""
        info = await self.get_user_fast_info(user)

        try:
            # Only get bio for regular users and if client is available
            if self.client and info["bio"] not in ["BOT", "CHANNEL"]:
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
        if not self.client:
            raise ValueError("Telegram client not initialized")

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
        if not self.client:
            raise ValueError("Telegram client not initialized")

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
                        username = message.sender.username
                        # Add @ prefix if not present
                        if username and not username.startswith("@"):
                            username = f"@{username}"
                        sender_info["username"] = username

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

    def process_csv_to_json(self, csv_file_path: str) -> Dict[str, Dict]:
        """Process CSV file and group messages by user in JSON format"""
        users_data = {}

        try:
            with open(
                csv_file_path, encoding=self.settings.csv_encoding
            ) as file:
                reader = csv.DictReader(
                    file,
                    delimiter=self.settings.csv_delimiter,
                    lineterminator=self.settings.csv_line_terminator,
                )

                for row in reader:
                    sender_id = row.get("sender_id", "")
                    if not sender_id:
                        continue

                    # Initialize user data if not exists
                    if sender_id not in users_data:
                        # Process username with @ prefix
                        username = row.get("sender_username", "")
                        if username and not username.startswith("@"):
                            username = f"@{username}"

                        users_data[sender_id] = {
                            "sender_id": sender_id,
                            "sender_username": username,
                            "sender_name": row.get("sender_name", ""),
                            "sender_bio": row.get("sender_bio", ""),
                            "sender_common_groups": row.get(
                                "sender_common_groups", ""
                            ),
                            "group": row.get("group", ""),
                            "group_id": row.get("group_id", ""),
                            "messages": [],
                        }

                    # Add message to user's messages
                    message_data = {
                        "message_id": row.get("message_id", ""),
                        "date": row.get("date", ""),
                        "message_text": row.get("message_text", ""),
                        "message_gaming_keywords": row.get(
                            "message_gaming_keywords", ""
                        ),
                    }

                    users_data[sender_id]["messages"].append(message_data)

        except FileNotFoundError:
            print(f"❌ Файл {csv_file_path} не найден")
            return {}
        except Exception as e:
            print(f"❌ Ошибка обработки файла: {e}")
            return {}

        return users_data

    def filter_users_with_gaming_keywords(
        self, users_data: Dict[str, Dict]
    ) -> Dict[str, Dict]:
        """Filter users who have at least one message with gaming keywords"""
        filtered_users = {}

        for user_id, user_data in users_data.items():
            has_gaming_keywords = False

            # Check if any message has gaming keywords
            for message in user_data["messages"]:
                if message.get("message_gaming_keywords", "").strip():
                    has_gaming_keywords = True
                    break

            if has_gaming_keywords:
                filtered_users[user_id] = user_data

        print(
            f"🔍 Отфильтровано {len(filtered_users)} пользователей из {len(users_data)} с игровыми ключевыми словами"
        )
        return filtered_users

    async def validate_user_with_ai(self, user_data: Dict) -> bool:
        """Validate user data using OpenRouter AI API"""
        if not self.settings.openrouter_api_key:
            print("❌ OpenRouter API key не настроен")
            return False

        # Prepare user data for AI analysis
        user_summary = {
            "sender_username": user_data.get("sender_username", ""),
            "sender_name": user_data.get("sender_name", ""),
            "sender_bio": user_data.get("sender_bio", ""),
            "sender_common_groups": user_data.get("sender_common_groups", ""),
            "group": user_data.get("group", ""),
            "group_id": user_data.get("group_id", ""),
            "messages_count": len(user_data.get("messages", [])),
            "recent_messages": [
                {
                    "message_id": msg.get("message_id", ""),
                    "date": msg.get("date", ""),
                    "text": msg.get("message_text", ""),
                    "gaming_keywords": msg.get("message_gaming_keywords", ""),
                }
                for msg in user_data.get("messages", [])[
                    :5
                ]  # Only recent 5 messages
            ],
        }

        prompt = f"{self.settings.ai_validation_prompt}\n\n{json.dumps(user_summary, ensure_ascii=False, indent=2)}"

        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/telegram-scraper",
            "X-Title": "Telegram User Validator",
        }

        payload = {
            "model": self.settings.ai_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 100,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                )

                if response.status_code == 200:
                    result = response.json()
                    ai_response = result["choices"][0]["message"][
                        "content"
                    ].strip()

                    # Parse AI response
                    try:
                        # Remove markdown code blocks if present
                        ai_response_clean = ai_response.strip()
                        if ai_response_clean.startswith("```json"):
                            ai_response_clean = ai_response_clean[7:]
                        if ai_response_clean.startswith("```"):
                            ai_response_clean = ai_response_clean[3:]
                        if ai_response_clean.endswith("```"):
                            ai_response_clean = ai_response_clean[:-3]

                        ai_response_clean = ai_response_clean.strip()
                        validation_result = json.loads(ai_response_clean)
                        return validation_result.get("valid", False)
                    except json.JSONDecodeError:
                        print(f"⚠️ Некорректный ответ AI: {ai_response}")
                        return False
                else:
                    print(f"❌ Ошибка API: {response.status_code}")
                    return False

        except Exception as e:
            print(f"❌ Ошибка при обращении к AI: {e}")
            return False

    def get_google_oauth2_credentials(self):
        """Get OAuth 2.0 credentials for Google Sheets API"""
        if not GOOGLE_SHEETS_AVAILABLE:
            print("❌ Google Sheets API libraries not available")
            return None

        SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

        creds = None
        token_file = self.settings.google_token_file

        # Load existing token
        if os.path.exists(token_file):
            try:
                with open(token_file, "rb") as token:
                    creds = pickle.load(token)
            except Exception as e:
                print(f"⚠️ Error loading token file: {e}")
                creds = None

        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())  # type: ignore
                    print("✅ OAuth2 token refreshed")
                except Exception as e:
                    print(f"⚠️ Token refresh failed: {e}")
                    creds = None

            if not creds:
                # Start OAuth flow
                try:
                    # Check if using inline credentials or file
                    if (
                        self.settings.google_auth_method.lower()
                        == "oauth2_inline"
                        and self.settings.google_oauth_client_id
                        and self.settings.google_oauth_client_secret
                    ):

                        # Create OAuth flow with inline credentials
                        client_config = {
                            "installed": {
                                "client_id": self.settings.google_oauth_client_id,
                                "client_secret": self.settings.google_oauth_client_secret,
                                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                                "token_uri": "https://oauth2.googleapis.com/token",
                                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                                "redirect_uris": [
                                    "http://localhost:8080/",
                                    "http://127.0.0.1:8080/",
                                    "urn:ietf:wg:oauth:2.0:oob",
                                ],
                            }
                        }

                        flow = InstalledAppFlow.from_client_config(  # type: ignore
                            client_config, SCOPES
                        )
                        print(
                            "🔐 Starting OAuth 2.0 authentication with inline credentials..."
                        )

                    else:
                        # Use credentials file
                        flow = InstalledAppFlow.from_client_secrets_file(  # type: ignore
                            self.settings.google_oauth_credentials_file, SCOPES
                        )
                        print(
                            "🔐 Starting OAuth 2.0 authentication with credentials file..."
                        )

                    print(
                        "📱 Your browser will open for Google authentication"
                    )
                    creds = flow.run_local_server(port=8080)
                    print("✅ OAuth 2.0 authentication successful")

                except FileNotFoundError:
                    print(
                        f"❌ OAuth credentials file not found: {self.settings.google_oauth_credentials_file}"
                    )
                    print(
                        "💡 Download OAuth 2.0 client JSON from Google Cloud Console"
                    )
                    print(
                        "💡 Or use inline credentials with GOOGLE_AUTH_METHOD=oauth2_inline"
                    )
                    return None
                except Exception as e:
                    print(f"❌ OAuth 2.0 authentication failed: {e}")
                    if (
                        self.settings.google_auth_method.lower()
                        == "oauth2_inline"
                    ):
                        print(
                            "💡 Check your GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET"
                        )
                    return None

            # Save the credentials for the next run
            try:
                with open(token_file, "wb") as token:
                    pickle.dump(creds, token)
                print(f"💾 Token saved to {token_file}")
            except Exception as e:
                print(f"⚠️ Could not save token: {e}")

        return creds

    def get_google_sheets_service(self):
        """Initialize Google Sheets service with credentials (supports both auth methods)"""
        if not GOOGLE_SHEETS_AVAILABLE:
            raise ImportError(
                "Google Sheets API libraries not installed. Run: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
            )

        credentials = None

        # Choose authentication method
        if self.settings.google_auth_method.lower() in [
            "oauth2",
            "oauth2_file",
            "oauth2_inline",
        ]:
            print("🔐 Using OAuth 2.0 authentication...")
            credentials = self.get_google_oauth2_credentials()
            if not credentials:
                print("❌ OAuth 2.0 authentication failed")
                return None
        else:
            # Default to service account
            print("🔑 Using Service Account authentication...")
            try:
                credentials = ServiceAccountCredentials.from_service_account_file(  # type: ignore
                    self.settings.google_credentials_file,
                    scopes=["https://www.googleapis.com/auth/spreadsheets"],
                )
            except FileNotFoundError:
                print(
                    f"❌ Google credentials file not found: {self.settings.google_credentials_file}"
                )
                print(
                    "💡 Download service account JSON from Google Cloud Console"
                )
                print(
                    "💡 Or set GOOGLE_AUTH_METHOD=oauth2_inline and provide CLIENT_ID/CLIENT_SECRET in .env"
                )
                return None
            except Exception as e:
                print(f"❌ Error loading service account credentials: {e}")
                return None

        try:
            service = build("sheets", "v4", credentials=credentials)  # type: ignore
            print("✅ Google Sheets service initialized successfully")
            return service
        except Exception as e:
            print(f"❌ Error initializing Google Sheets service: {e}")
            return None

    def create_new_spreadsheet(self, title: str) -> Optional[str]:
        """Create a new Google Spreadsheet"""
        if not GOOGLE_SHEETS_AVAILABLE:
            print("❌ Google Sheets API not available")
            return None

        try:
            service = self.get_google_sheets_service()
            if not service:
                return None

            spreadsheet = {
                "properties": {"title": title},
                "sheets": [
                    {
                        "properties": {
                            "title": self.settings.google_worksheet_name
                        }
                    }
                ],
            }

            result = service.spreadsheets().create(body=spreadsheet).execute()
            spreadsheet_id = result.get("spreadsheetId")
            spreadsheet_url = (
                f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
            )

            print(f"✅ Created new spreadsheet: {title}")
            print(f"🔗 URL: {spreadsheet_url}")

            return spreadsheet_id

        except Exception as e:
            print(f"❌ Error creating spreadsheet: {e}")
            return None

    def get_google_sheets_choice(self) -> tuple[Optional[str], str]:
        """Get user's choice for Google Sheets upload"""
        choice = input(
            "\n📊 Google Sheets опции:\n"
            "1. 📄 Создать новую таблицу\n"
            "2. ➕ Добавить в существующую таблицу\n"
            "3. ⏭️ Пропустить загрузку в Google Sheets\n"
            "👆 Ваш выбор: "
        )

        if choice == "1":
            title = input("📝 Введите название новой таблицы: ")
            if not title.strip():
                title = f"Telegram Validated Users {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            return None, title  # None spreadsheet_id means create new

        elif choice == "2":
            if self.settings.google_spreadsheet_id:
                use_default = input(
                    f"📋 Использовать таблицу по умолчанию? (y/N): "
                )
                if use_default.lower() == "y":
                    return self.settings.google_spreadsheet_id, ""

            spreadsheet_id = input("🔗 Введите ID существующей таблицы: ")
            if not spreadsheet_id.strip():
                print("❌ ID таблицы не может быть пустым")
                return None, ""
            return spreadsheet_id, ""

        else:
            return None, ""

    def prepare_sheets_data(
        self, validated_users: Dict[str, Dict]
    ) -> List[List[str]]:
        """Prepare data for Google Sheets upload"""
        # Headers
        headers = [
            "Sender ID",
            "Username",
            "Profile URL",
            "Name",
            "Bio",
            "Common Groups",
            "Group",
            "Group ID",
            "Messages Count",
            "AI Validated",
            "Latest Message",
            "Gaming Keywords",
            "Last Message Date",
        ]

        rows = [headers]

        for user_id, user_data in validated_users.items():
            # Get latest message and its date
            messages = user_data.get("messages", [])
            latest_message = ""
            latest_keywords = ""
            last_message_date = ""

            if messages:
                # Sort by date and get latest
                sorted_messages = sorted(
                    messages, key=lambda x: x.get("date", ""), reverse=True
                )
                if sorted_messages:
                    latest_msg = sorted_messages[0]
                    latest_message = latest_msg.get("message_text", "")[
                        :200
                    ]  # Truncate
                    latest_keywords = latest_msg.get(
                        "message_gaming_keywords", ""
                    )
                    last_message_date = latest_msg.get("date", "")

            # Process username with @ prefix
            username = user_data.get("sender_username", "")
            if username and not username.startswith("@"):
                username = f"@{username}"

            # Generate Telegram profile URL
            sender_id = user_data.get("sender_id", "")
            profile_url = ""
            if username and username != "@":
                # Use username-based URL (more readable)
                profile_url = (
                    f"https://t.me/{username[1:]}"  # Remove @ for URL
                )
            elif sender_id:
                # Fallback to ID-based URL
                profile_url = f"tg://user?id={sender_id}"

            row = [
                sender_id,
                username,
                profile_url,
                user_data.get("sender_name", ""),
                user_data.get("sender_bio", "")[:500],  # Truncate bio
                user_data.get("sender_common_groups", ""),
                user_data.get("group", ""),
                user_data.get("group_id", ""),
                str(len(messages)),
                "Yes" if user_data.get("ai_validated") else "No",
                latest_message,
                latest_keywords,
                last_message_date,
            ]

            rows.append(row)

        return rows

    def upload_to_google_sheets(
        self, validated_users: Dict[str, Dict]
    ) -> bool:
        """Upload validated users to Google Sheets"""
        if not GOOGLE_SHEETS_AVAILABLE:
            print("❌ Google Sheets API not available")
            return False

        if not validated_users:
            print("❌ No validated users to upload")
            return False

        # Get user choice
        spreadsheet_id, new_title = self.get_google_sheets_choice()

        if spreadsheet_id is None and not new_title:
            print("⏭️ Skipping Google Sheets upload")
            return True

        try:
            service = self.get_google_sheets_service()
            if not service:
                return False

            # Create new spreadsheet if needed
            if spreadsheet_id is None:
                spreadsheet_id = self.create_new_spreadsheet(new_title)
                if not spreadsheet_id:
                    return False

            # Prepare data
            print("📊 Preparing data for upload...")
            rows = self.prepare_sheets_data(validated_users)

            # Determine range - append or overwrite
            worksheet_name = self.settings.google_worksheet_name

            # Check if we're appending to existing data
            try:
                # Try to get existing data to determine where to append
                result = (
                    service.spreadsheets()
                    .values()
                    .get(
                        spreadsheetId=spreadsheet_id,
                        range=f"{worksheet_name}!A:A",
                    )
                    .execute()
                )

                existing_rows = len(result.get("values", []))
                if existing_rows > 0:
                    # Append without headers
                    start_row = existing_rows + 1
                    range_name = f"{worksheet_name}!A{start_row}"
                    upload_data = rows[1:]  # Skip headers
                    print(
                        f"📌 Appending {len(upload_data)} rows starting from row {start_row}"
                    )
                else:
                    # No existing data, include headers
                    range_name = f"{worksheet_name}!A1"
                    upload_data = rows
                    print(
                        f"📌 Writing {len(upload_data)} rows including headers"
                    )

            except HttpError:  # type: ignore
                # Worksheet might not exist or spreadsheet might be new
                range_name = f"{worksheet_name}!A1"
                upload_data = rows
                print(f"📌 Writing {len(upload_data)} rows to new worksheet")

            # Upload data
            body = {"values": upload_data}

            result = (
                service.spreadsheets()
                .values()
                .update(
                    spreadsheetId=spreadsheet_id,
                    range=range_name,
                    valueInputOption="RAW",
                    body=body,
                )
                .execute()
            )

            updated_rows = result.get("updatedRows", 0)
            spreadsheet_url = (
                f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"
            )

            print(
                f"✅ Successfully uploaded {updated_rows} rows to Google Sheets"
            )
            print(f"🔗 View spreadsheet: {spreadsheet_url}")

            return True

        except HttpError as e:  # type: ignore
            print(f"❌ Google Sheets API error: {e}")
            return False
        except Exception as e:
            print(f"❌ Error uploading to Google Sheets: {e}")
            return False

    async def process_and_validate_data(self) -> None:
        """Main method to process CSV data and validate with AI"""
        # Get available CSV files in data folder
        csv_files = list(self.settings.data_folder.glob("messages-*.csv"))

        if not csv_files:
            print("❌ Файлы сообщений не найдены в папке data/")
            return

        if len(csv_files) == 1:
            csv_file = csv_files[0]
        else:
            print("\n📁 Доступные файлы сообщений:")
            for i, file in enumerate(csv_files):
                print(f"{i}: {file.name}")

            try:
                file_idx = int(input("\n👆 Выберите файл: "))
                csv_file = csv_files[file_idx]
            except (ValueError, IndexError):
                print("❌ Неверный номер файла")
                return

        print(f"\n📊 Обработка файла: {csv_file.name}")

        # Step 1: Process CSV to JSON format
        print("1️⃣ Группировка сообщений по пользователям...")
        users_data = self.process_csv_to_json(str(csv_file))
        if not users_data:
            return

        # Step 2: Filter users with gaming keywords
        print("2️⃣ Фильтрация пользователей с игровыми ключевыми словами...")
        filtered_users = self.filter_users_with_gaming_keywords(users_data)
        if not filtered_users:
            print("❌ Не найдено пользователей с игровыми ключевыми словами")
            return

        # Save filtered data to JSON
        filtered_filename = str(
            self.settings.data_folder
            / f"filtered-users-{uuid.uuid4().hex[:8]}.json"
        )
        with open(filtered_filename, "w", encoding="utf-8") as f:
            json.dump(filtered_users, f, ensure_ascii=False, indent=2)
        print(f"💾 Отфильтрованные данные сохранены в {filtered_filename}")

        # Step 3: AI validation
        if not self.settings.openrouter_api_key:
            print("⚠️ OpenRouter API key не настроен. Пропускаем AI валидацию.")
            print(
                "💡 Добавьте OPENROUTER_API_KEY в .env файл для AI валидации"
            )
            return

        print("3️⃣ AI валидация пользователей...")
        validated_users = {}
        total_users = len(filtered_users)

        for i, (user_id, user_data) in enumerate(filtered_users.items(), 1):
            print(
                f"[{i}/{total_users}] Валидация пользователя {user_data.get('sender_username', user_id)}..."
            )

            is_valid = await self.validate_user_with_ai(user_data)
            if is_valid:
                validated_users[user_id] = user_data
                validated_users[user_id]["ai_validated"] = True

            # Add delay to avoid rate limiting
            await asyncio.sleep(1)

        print(
            f"✅ AI валидация завершена: {len(validated_users)} из {total_users} пользователей прошли валидацию"
        )

        # Save validated data
        if validated_users:
            validated_filename = str(
                self.settings.data_folder
                / f"validated-users-{uuid.uuid4().hex[:8]}.json"
            )
            with open(validated_filename, "w", encoding="utf-8") as f:
                json.dump(validated_users, f, ensure_ascii=False, indent=2)
            print(f"💾 Валидированные данные сохранены в {validated_filename}")

            # Step 4: Google Sheets upload (optional)
            print("4️⃣ Загрузка в Google Sheets...")
            if GOOGLE_SHEETS_AVAILABLE:
                success = self.upload_to_google_sheets(validated_users)
                if success:
                    print("✅ Данные успешно загружены в Google Sheets")
                else:
                    print("❌ Ошибка при загрузке в Google Sheets")
            else:
                print(
                    "⚠️ Google Sheets API недоступен. Установите зависимости:"
                )
                print(
                    "pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
                )
        else:
            print("❌ Ни один пользователь не прошел AI валидацию")

    async def upload_existing_data_to_sheets(self) -> None:
        """Upload existing JSON data files to Google Sheets"""
        print("📊 Загрузка существующих данных в Google Sheets")
        print("=" * 50)

        # Check if Google Sheets is available
        if not GOOGLE_SHEETS_AVAILABLE:
            print("❌ Google Sheets API недоступен. Установите зависимости:")
            print(
                "pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client"
            )
            return

        # Find available JSON data files
        data_folder = self.settings.data_folder
        json_files = list(data_folder.glob("*.json"))

        if not json_files:
            print("❌ JSON файлы с данными не найдены в папке data/")
            print("💡 Сначала обработайте данные с помощью опции 2")
            return

        # Filter relevant files (exclude config/system files)
        relevant_files = [
            f
            for f in json_files
            if any(
                keyword in f.name
                for keyword in [
                    "filtered-users",
                    "validated-users",
                    "users-data",
                ]
            )
        ]

        if not relevant_files:
            print("❌ Подходящие файлы данных не найдены")
            print(
                "💡 Ищите файлы: filtered-users-*.json, validated-users-*.json"
            )
            return

        # Display available files
        print("\n📁 Доступные файлы данных:")
        for i, file in enumerate(relevant_files):
            file_size = file.stat().st_size
            modified_time = file.stat().st_mtime
            from datetime import datetime

            mod_date = datetime.fromtimestamp(modified_time).strftime(
                "%Y-%m-%d %H:%M"
            )

            print(f"{i}: {file.name} ({file_size // 1024}KB, {mod_date})")

        # Get user choice
        try:
            file_idx = int(input("\n👆 Выберите файл для загрузки: "))
            selected_file = relevant_files[file_idx]
        except (ValueError, IndexError):
            print("❌ Неверный номер файла")
            return

        # Load and validate JSON data
        try:
            with open(selected_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                print(
                    "❌ Неверный формат файла - ожидается JSON объект с пользователями"
                )
                return

            print(
                f"✅ Загружен файл {selected_file.name} с {len(data)} пользователями"
            )

        except json.JSONDecodeError as e:
            print(f"❌ Ошибка чтения JSON файла: {e}")
            return
        except Exception as e:
            print(f"❌ Ошибка загрузки файла: {e}")
            return

        # Display data summary
        if data:
            # Try to determine data type
            sample_user = next(iter(data.values()))
            has_ai_validation = sample_user.get("ai_validated") is not None
            has_messages = "messages" in sample_user

            print(f"\n📋 Информация о данных:")
            print(f"   Пользователей: {len(data)}")
            print(
                f"   AI валидация: {'✅ Да' if has_ai_validation else '❌ Нет'}"
            )
            print(f"   Сообщения: {'✅ Да' if has_messages else '❌ Нет'}")

            # Count AI validated users if available
            if has_ai_validation:
                validated_count = sum(
                    1 for user in data.values() if user.get("ai_validated")
                )
                print(f"   Валидированных: {validated_count}")

        # Confirm upload
        confirm = input(
            f"\n🔄 Загрузить {len(data)} пользователей в Google Sheets? (y/N): "
        )
        if confirm.lower() != "y":
            print("⏭️ Загрузка отменена")
            return

        # Upload to Google Sheets
        print("📤 Загрузка данных в Google Sheets...")
        success = self.upload_to_google_sheets(data)

        if success:
            print("✅ Данные успешно загружены в Google Sheets!")
        else:
            print("❌ Ошибка при загрузке в Google Sheets")
            print("💡 Проверьте настройки аутентификации Google")

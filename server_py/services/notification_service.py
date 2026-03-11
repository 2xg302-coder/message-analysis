import httpx
import logging
import asyncio
from typing import Optional
from config import settings

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        # Common
        self.mode = settings.QQ_BOT_MODE # 'go-cqhttp' or 'official'

        # go-cqhttp
        self.api_url = settings.QQ_BOT_API_URL
        self.access_token = settings.QQ_BOT_ACCESS_TOKEN
        self.target_group_id = settings.QQ_TARGET_GROUP_ID
        self.target_user_id = settings.QQ_TARGET_USER_ID

        # Official Bot
        self.app_id = settings.QQ_BOT_APP_ID
        self.token = settings.QQ_BOT_TOKEN
        self.channel_id = settings.QQ_CHANNEL_ID
        self.is_sandbox = settings.QQ_BOT_SANDBOX
        self.official_base_url = "https://sandbox.api.sgroup.qq.com" if self.is_sandbox else "https://api.sgroup.qq.com"

    async def send_qq_notification(self, title: str, summary: str, score: float, link: Optional[str] = None):
        """
        Send notification to QQ based on configured mode.
        """
        try:
            if self.mode == 'official':
                await self._send_official_notification(title, summary, score, link)
            else:
                await self._send_gocqhttp_notification(title, summary, score, link)
        except Exception as e:
            logger.error(f"Failed to send QQ notification: {e}")

    async def _send_official_notification(self, title: str, summary: str, score: float, link: Optional[str] = None):
        if not self.app_id or not self.token or not self.channel_id:
            logger.debug("Official QQ Bot credentials (AppID/Token/ChannelID) missing.")
            return

        content = f"【重要新闻】(影响度: {score})\n"
        content += f"标题: {title}\n"
        content += f"摘要: {summary}"
        if link:
            content += f"\n链接: {link}"

        # 官方 API：Bot {AppID}.{Token}
        headers = {
            "Authorization": f"Bot {self.app_id}.{self.token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.official_base_url}/channels/{self.channel_id}/messages"
        payload = {"content": content}

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(url, json=payload, headers=headers, timeout=5.0)
                resp.raise_for_status()
                logger.info(f"Official QQ notification sent to channel {self.channel_id}")
            except httpx.HTTPStatusError as e:
                logger.error(f"Official QQ API Error {e.response.status_code}: {e.response.text}")
            except Exception as e:
                logger.error(f"Error sending official notification: {e}")

    async def _send_gocqhttp_notification(self, title: str, summary: str, score: float, link: Optional[str] = None):
        if not self.api_url:
            logger.debug("QQ_BOT_API_URL not configured, skipping notification.")
            return

        message = f"【重要新闻】(影响度: {score})\n"
        message += f"标题: {title}\n"
        message += f"摘要: {summary}\n"
        if link:
            message += f"链接: {link}"

        headers = {}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        async with httpx.AsyncClient() as client:
            try:
                # Send to Group
                if self.target_group_id:
                    payload = {
                        "group_id": int(self.target_group_id),
                        "message": message
                    }
                    await self._send(client, "send_group_msg", payload, headers)

                # Send to User (Private)
                if self.target_user_id:
                    payload = {
                        "user_id": int(self.target_user_id),
                        "message": message
                    }
                    await self._send(client, "send_private_msg", payload, headers)
                    
            except Exception as e:
                logger.error(f"Failed to send go-cqhttp notification: {e}")

    async def _send(self, client: httpx.AsyncClient, endpoint: str, payload: dict, headers: dict):
        url = f"{self.api_url}/{endpoint}"
        try:
            resp = await client.post(url, json=payload, headers=headers, timeout=5.0)
            resp.raise_for_status()
            logger.info(f"QQ notification sent to {endpoint}: {payload.get('group_id') or payload.get('user_id')}")
        except httpx.HTTPStatusError as e:
            logger.error(f"QQ API Error {e.response.status_code}: {e.response.text}")
        except Exception as e:
            logger.error(f"Error sending to {endpoint}: {e}")

notification_service = NotificationService()

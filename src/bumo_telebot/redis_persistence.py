import pickle
from abc import ABC
from collections import defaultdict
from copy import deepcopy
from typing import Any, DefaultDict, Dict, Optional, Tuple

from redis import Redis
from telegram.ext import BasePersistence, PersistenceInput
from telegram.ext._utils.types import CDCData


class RedisPersistence(BasePersistence, ABC):
    """Using Redis to make the bot persistent"""

    def __init__(self, redis: Redis, on_flush: bool = False):
        persistence_input = PersistenceInput(
            bot_data=True, chat_data=False, user_data=False, callback_data=False
        )
        super().__init__(store_data=persistence_input, update_interval=3600)

        self.redis: Redis = redis
        self.on_flush = on_flush
        self.user_data: Optional[DefaultDict[int, Dict]] = None
        self.chat_data: Optional[DefaultDict[int, Dict]] = None
        self.bot_data: Optional[Dict] = None
        self.conversations: Optional[Dict[str, Dict[Tuple, Any]]] = None

    async def load_redis(self) -> None:
        try:
            if (data_bytes := self.redis.get("TelegramBotPersistence")) is None:
                self.conversations = dict()
                self.user_data = defaultdict(dict)
                self.chat_data = defaultdict(dict)
                self.bot_data = {}
            else:
                data = pickle.loads(data_bytes)
                self.user_data = defaultdict(dict, data["user_data"])
                self.chat_data = defaultdict(dict, data["chat_data"])
                # For backwards compatibility with files not containing bot data
                self.bot_data = data.get("bot_data", {})
                self.conversations = data["conversations"]
        except Exception as exc:
            raise TypeError(f"Something went wrong unpickling from Redis") from exc

    def dump_redis(self) -> None:
        data = {
            "conversations": self.conversations,
            "user_data": self.user_data,
            "chat_data": self.chat_data,
            "bot_data": self.bot_data,
        }
        data_bytes = pickle.dumps(data)
        self.redis.set("TelegramBotPersistence", data_bytes)

    def flush(self) -> None:
        """Will save all data in memory to pickle on Redis."""
        self.dump_redis()

    async def get_bot_data(self) -> Dict[Any, Any]:
        """Returns the bot_data from the pickle on Redis if it exists or an empty :obj:`dict`."""
        if self.bot_data:
            pass
        else:
            await self.load_redis()
        return deepcopy(self.bot_data)

    async def update_bot_data(self, data: Dict) -> None:
        """Will update the bot_data and depending on :attr:`on_flush` save the pickle on Redis."""
        if self.bot_data == data:
            return
        self.bot_data = data.copy()
        if not self.on_flush:
            self.dump_redis()

    async def refresh_bot_data(self, bot_data) -> None:
        """Will refresh the bot_data and depending on :attr:`on_flush` save the pickle on Redis."""
        return await self.update_bot_data(bot_data)

    def get_user_data(self) -> DefaultDict[int, Dict[Any, Any]]:
        """Returns the user_data from the pickle on Redis if it exists or an empty :obj:`defaultdict`."""
        pass

    def get_chat_data(self) -> DefaultDict[int, Dict[Any, Any]]:
        """Returns the chat_data from the pickle on Redis if it exists or an empty :obj:`defaultdict`."""
        pass

    def get_conversations(self, name: str) -> Dict:
        """Returns the conversations from the pickle on Redis if it exists or an empty dict."""
        pass

    def update_conversation(
        self, name: str, key: Tuple[int, ...], new_state: Optional[object]
    ) -> None:
        """Will update the conversations for the given handler and depending on :attr:`on_flush` save the pickle on Redis."""
        pass

    def update_user_data(self, user_id: int, data: Dict) -> None:
        """Will update the user_data and depending on :attr:`on_flush` save the pickle on Redis."""
        pass

    def update_chat_data(self, chat_id: int, data: Dict) -> None:
        """Will update the chat_data and depending on :attr:`on_flush` save the pickle on Redis."""
        pass

    def drop_chat_data(self, chat_id: int) -> None:
        """Will drop the chat_data for the given chat_id."""
        pass

    def drop_user_data(self, user_id: int) -> None:
        """Will drop the user_data for the given user_id."""
        pass

    def get_callback_data(self) -> Dict[str, Any]:
        """Returns the callback_data from the pickle on Redis if it exists or an empty dict."""
        pass

    def refresh_chat_data(self, chat_id, chat_data) -> None:
        """Will refresh the chat_data and depending on :attr:`on_flush` save the pickle on Redis."""
        pass

    def refresh_user_data(self, user_id, user_data) -> None:
        """Will refresh the user_data and depending on :attr:`on_flush` save the pickle on Redis."""
        pass

    def update_callback_data(self, data: CDCData) -> None:
        """Will update the callback_data and depending on :attr:`on_flush` save the pickle on Redis."""
        pass

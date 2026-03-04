from pydantic import BaseModel
from typing import List, Optional

class PhotoSize(BaseModel):
    file_id: str
    width: int
    height: int
    file_size: Optional[int] = None

class Chat(BaseModel):
    id: int

class Message(BaseModel):
    message_id: int
    chat: Chat
    text: Optional[str] = None
    photo: Optional[List[PhotoSize]] = None

class Update(BaseModel):
    update_id: int
    message: Optional[Message] = None

from pydantic import BaseModel, Field
from typing import List, Optional

class User(BaseModel):
    id: int
    is_bot: bool = False
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None

class Chat(BaseModel):
    id: int

class PhotoSize(BaseModel):
    file_id: str
    width: int
    height: int
    file_size: Optional[int] = None

class Message(BaseModel):
    message_id: int
    chat: Chat
    from_user: Optional[User] = Field(None, alias="from")
    text: Optional[str] = None
    photo: Optional[List[PhotoSize]] = None

    model_config = {"populate_by_name": True}

class CallbackQuery(BaseModel):
    id: str
    from_user: Optional[User] = Field(None, alias="from")
    message: Optional[Message] = None
    data: Optional[str] = None

    model_config = {"populate_by_name": True}

class Update(BaseModel):
    update_id: int
    message: Optional[Message] = None
    callback_query: Optional[CallbackQuery] = None

    model_config = {"populate_by_name": True}

from pydantic import BaseModel, Field

class User(BaseModel):
    id: int
    is_bot: bool = False
    first_name: str
    last_name: str | None = None
    username: str | None = None

class Chat(BaseModel):
    id: int

class PhotoSize(BaseModel):
    file_id: str
    width: int
    height: int
    file_size: int | None = None

class Message(BaseModel):
    message_id: int
    chat: Chat
    from_user: User | None = Field(None, alias="from")
    text: str | None = None
    photo: list[PhotoSize] | None = None

    model_config = {"populate_by_name": True}

class CallbackQuery(BaseModel):
    id: str
    from_user: User | None = Field(None, alias="from")
    message: Message | None = None
    data: str | None = None

    model_config = {"populate_by_name": True}

class Update(BaseModel):
    update_id: int
    message: Message | None = None
    callback_query: CallbackQuery | None = None

    model_config = {"populate_by_name": True}

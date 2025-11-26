from pydantic import BaseModel

class FileRequest(BaseModel):
    file: str

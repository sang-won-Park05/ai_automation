from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Article(BaseModel):

    source: str
    source_type: str

    title: str
    url: str

    published_at: Optional[datetime] = None
    author: Optional[str] = None

    summary: Optional[str] = None
    raw_content: Optional[str] = None
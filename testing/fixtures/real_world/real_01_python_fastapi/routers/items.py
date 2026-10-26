from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/items")

class Item(BaseModel):
    id: int
    name: str

@router.get("/")
def list_items():
    return [{"id": 1, "name": "sample"}]

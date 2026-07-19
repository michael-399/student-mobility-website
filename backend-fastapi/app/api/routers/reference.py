"""Reference-data routes: institutions list and lecturers list.

Both require authentication (any role) and are used to populate frontend
dropdowns.  Mounted at /institutions and /lecturers respectively.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import repositories as repo
from app.api.deps import get_current_user
from app.db.session import get_db
from app.serializers import serialize_institution, serialize_user

institutions_router = APIRouter(prefix="/institutions", tags=["institutions"])
lecturers_router = APIRouter(prefix="/lecturers", tags=["lecturers"])


@institutions_router.get("")
async def list_institutions(_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    items = await repo.list_institutions(db)
    return [serialize_institution(i) for i in items]


@lecturers_router.get("")
async def list_lecturers(_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    items = await repo.list_lecturers(db)
    return [serialize_user(u) for u in items]

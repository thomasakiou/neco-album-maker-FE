from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.state_schema import StateRead, StateCreate, StateUpdate
from app.domain.repositories.interfaces import IStateRepository
from app.api.v1.deps import get_state_repo
from app.core.db import get_db

router = APIRouter(prefix="/states", tags=["states"])


@router.get("/", response_model=List[StateRead])
async def list_states(repo: IStateRepository = Depends(get_state_repo)):
    states = await repo.find_all()
    return [StateRead.model_validate(state) for state in states]


@router.get("/{state_code}", response_model=StateRead)
async def get_state(
    state_code: str,
    repo: IStateRepository = Depends(get_state_repo)
):
    state = await repo.get_by_code(state_code)
    if not state:
        raise HTTPException(status_code=404, detail="State not found")
    return StateRead.model_validate(state)


@router.post("/", response_model=StateRead)
async def create_state(
    state_data: StateCreate,
    repo: IStateRepository = Depends(get_state_repo)
):
    from app.domain.models.state import State
    state = State(**state_data.model_dump())
    created = await repo.add(state)
    return StateRead.model_validate(created)


@router.put("/{state_code}", response_model=StateRead)
async def update_state(
    state_code: str,
    state_data: StateUpdate,
    repo: IStateRepository = Depends(get_state_repo)
):
    state = await repo.get_by_code(state_code)
    if not state:
        raise HTTPException(status_code=404, detail="State not found")
    
    for field, value in state_data.model_dump(exclude_unset=True).items():
        setattr(state, field, value)
    
    updated = await repo.update(state)
    return StateRead.model_validate(updated)


@router.delete("/{state_code}")
async def delete_state(
    state_code: str,
    repo: IStateRepository = Depends(get_state_repo)
):
    deleted = await repo.delete_by_code(state_code)
    if not deleted:
        raise HTTPException(status_code=404, detail="State not found")
    return {"message": "State deleted"}


@router.delete("/")
async def delete_all_states(
    force: bool = Query(False),
    repo: IStateRepository = Depends(get_state_repo),
    session: AsyncSession = Depends(get_db)
):
    if not force:
        raise HTTPException(status_code=400, detail="Add ?force=true to confirm deletion")
    
    async with session.begin():
        count = await repo.delete_all()
    return {"deleted": count}
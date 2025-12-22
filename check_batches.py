import asyncio
from sqlalchemy import select, func
from app.core.db import get_db
from app.domain.models.student import Student

async def check_batches():
    async for session in get_db():
        query = select(Student.batch, func.count(Student.id)).group_by(Student.batch)
        result = await session.execute(query)
        batches = result.all()
        print("Batches in DB:")
        for batch, count in batches:
            print(f"Batch: {batch}, Count: {count}")
        break

if __name__ == "__main__":
    asyncio.run(check_batches())

import asyncio
from sqlalchemy import create_engine, text

engine = create_engine('postgresql://postgres:ebimobowei81@localhost:5432/album_db')
with engine.connect() as conn:
    result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))
    tables = [r[0] for r in result.fetchall()]
    print('✓ Tables in album_db:', tables)
    
    # Check columns for each table
    for table in tables:
        if table != 'alembic_version':
            result = conn.execute(text(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name='{table}' ORDER BY ordinal_position"))
            columns = [(r[0], r[1]) for r in result.fetchall()]
            print(f'\n✓ {table} columns:')
            for col_name, col_type in columns:
                print(f'  - {col_name}: {col_type}')

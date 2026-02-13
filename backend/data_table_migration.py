import os

# Put your Supabase URL here
os.environ['DATABASE_URL'] = 'postgresql://postgres:kash!f515786@db.qprxzvyaptjxfiqahyty.supabase.co:5432/postgres'

from database import engine
from models import Base

Base.metadata.create_all(bind=engine)
print("✅ All tables created in Supabase!")
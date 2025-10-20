import os
from fastapi import Header, HTTPException, status
from dotenv import load_dotenv, find_dotenv
from supabase import create_client, Client


load_dotenv(find_dotenv())


def get_supabase_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("Supabase credentials are not configured")
    return create_client(url, key)


async def authorize_request(x_api_key: str = Header(None)):
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="API key required"
        )

    api_key_val = os.environ.get("ACCESS_KEY")
    if x_api_key != api_key_val:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )

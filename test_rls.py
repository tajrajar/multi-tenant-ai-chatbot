"""
Manual RLS isolation test.

This script logs in as two different real Supabase users (Alice and Bob,
each belonging to a different company) and confirms that each user can
ONLY see their own company's documents — never the other company's data.

This is NOT part of the application. It's a one-time verification script
to confirm our Row Level Security policies actually work, since testing
auth.uid() directly inside the Supabase SQL Editor is unreliable.

Requires SUPABASE_URL and SUPABASE_ANON_KEY in your .env file.
"""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]


def test_user_sees_only_their_company(email: str, password: str, expected_company: str):
    """Logs in as a user and prints what documents they can see."""
    client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

    auth_response = client.auth.sign_in_with_password(
        {"email": email, "password": password}
    )
    print(f"\nLogged in as: {email} (user id: {auth_response.user.id})")

    result = client.table("documents").select("file_name, company_id").execute()

    print(f"Documents visible to {email}:")
    for row in result.data:
        print(f"  - {row['file_name']}")

    if not result.data:
        print("  (no documents returned)")

    print(f"Expected: should see ONLY documents from {expected_company}")


if __name__ == "__main__":
    test_user_sees_only_their_company("alice@test.com", "TestPassword123!", "Company Alpha")
    test_user_sees_only_their_company("bob@test.com", "TestPassword123!", "Company Beta")
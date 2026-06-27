-- ============================================================
-- TICKET-002: Multi-tenant database schema with Row Level Security
--
-- Tables: companies, users, documents, document_chunks,
--         chats, messages, api_keys
--
-- Security model: every table has a company_id column.
-- RLS policies use get_my_company_id() to ensure a user can
-- only ever see rows belonging to their own company.
--
-- Verified working via real Supabase auth + Python client test
-- (not just written — actually tested end to end).
-- ============================================================

-- ----------------------------------------------------------
-- pgvector extension (for document embeddings / RAG search)
-- ----------------------------------------------------------
create extension if not exists vector;

-- ----------------------------------------------------------
-- Companies table: one row per client/tenant
-- ----------------------------------------------------------
create table companies (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- ----------------------------------------------------------
-- Users table: linked to Supabase Auth's auth.users table.
-- Each user belongs to exactly one company.
-- ----------------------------------------------------------
create table users (
    id uuid primary key references auth.users(id) on delete cascade,
    company_id uuid not null references companies(id) on delete cascade,
    email text not null,
    role text not null default 'VIEWER' check (role in ('OWNER', 'VIEWER')),
    created_at timestamptz not null default now()
);

create index idx_users_company_id on users(company_id);

-- ----------------------------------------------------------
-- Documents table: uploaded files
-- ----------------------------------------------------------
create table documents (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references companies(id) on delete cascade,
    uploaded_by uuid references users(id) on delete set null,
    file_name text not null,
    file_path text not null,
    status text not null default 'pending' check (status in ('pending', 'processing', 'ready', 'failed')),
    created_at timestamptz not null default now()
);

create index idx_documents_company_id on documents(company_id);

-- ----------------------------------------------------------
-- Document chunks: text pieces + embeddings, used for RAG
-- ----------------------------------------------------------
create table document_chunks (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references companies(id) on delete cascade,
    document_id uuid not null references documents(id) on delete cascade,
    chunk_text text not null,
    chunk_index int not null,
    embedding vector(1536),
    created_at timestamptz not null default now()
);

create index idx_document_chunks_company_id on document_chunks(company_id);
create index idx_document_chunks_document_id on document_chunks(document_id);

-- ----------------------------------------------------------
-- Chats: one row per conversation session
-- ----------------------------------------------------------
create table chats (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references companies(id) on delete cascade,
    created_by uuid references users(id) on delete set null,
    title text,
    created_at timestamptz not null default now()
);

create index idx_chats_company_id on chats(company_id);

-- ----------------------------------------------------------
-- Messages: individual messages inside a chat
-- ----------------------------------------------------------
create table messages (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references companies(id) on delete cascade,
    chat_id uuid not null references chats(id) on delete cascade,
    role text not null check (role in ('user', 'assistant', 'system')),
    content text not null,
    created_at timestamptz not null default now()
);

create index idx_messages_company_id on messages(company_id);
create index idx_messages_chat_id on messages(chat_id);

-- ----------------------------------------------------------
-- API keys: hashed only, never stored in plain text
-- ----------------------------------------------------------
create table api_keys (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references companies(id) on delete cascade,
    key_hash text not null unique,
    label text,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    revoked_at timestamptz
);

create index idx_api_keys_company_id on api_keys(company_id);

-- ============================================================
-- Row Level Security
-- ============================================================

alter table companies enable row level security;
alter table users enable row level security;
alter table documents enable row level security;
alter table document_chunks enable row level security;
alter table chats enable row level security;
alter table messages enable row level security;
alter table api_keys enable row level security;

-- ----------------------------------------------------------
-- Helper function: returns the calling user's company_id.
--
-- IMPORTANT: this must be SECURITY DEFINER. Without it, this
-- function querying "users" inside a policy ON "users" causes
-- infinite recursion (RLS policy triggers itself recursively).
-- SECURITY DEFINER lets this function bypass RLS internally,
-- breaking that loop safely.
-- ----------------------------------------------------------
create or replace function public.get_my_company_id()
returns uuid
language sql
security definer
stable
set search_path = public
as $$
    select company_id from public.users where id = auth.uid();
$$;

revoke all on function public.get_my_company_id() from public;
grant execute on function public.get_my_company_id() to authenticated;

-- ----------------------------------------------------------
-- Policies: each user can only see rows for their own company
-- ----------------------------------------------------------

create policy "Users can view their own company"
on companies for select
using (id = get_my_company_id());

create policy "Users can view users in their own company"
on users for select
using (company_id = get_my_company_id());

create policy "Users can view their own company's documents"
on documents for select
using (company_id = get_my_company_id());

create policy "Users can view their own company's document chunks"
on document_chunks for select
using (company_id = get_my_company_id());

create policy "Users can view their own company's chats"
on chats for select
using (company_id = get_my_company_id());

create policy "Users can view their own company's messages"
on messages for select
using (company_id = get_my_company_id());

create policy "Users can view their own company's api keys"
on api_keys for select
using (company_id = get_my_company_id());

-- ============================================================
-- Table grants for the "authenticated" role.
-- RLS policies above control WHICH rows are visible —
-- these grants control whether the role can query the table at all.
-- ============================================================

grant select on public.companies to authenticated;
grant select on public.users to authenticated;
grant select on public.documents to authenticated;
grant select on public.document_chunks to authenticated;
grant select on public.chats to authenticated;
grant select on public.messages to authenticated;
grant select on public.api_keys to authenticated;
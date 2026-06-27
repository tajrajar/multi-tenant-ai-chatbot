# Database Schema

This folder contains the SQL migration for the multi-tenant database schema (Ticket-002).

## How to apply

1. Open the Supabase SQL Editor for your project.
2. Run `001_initial_schema.sql` in full.
3. Enable the `pgvector` extension first if not already enabled (the script also attempts this via `create extension if not exists vector;`).

## Security model

Every table includes a `company_id` column. Row Level Security (RLS) is enabled on all tables, and policies use a `SECURITY DEFINER` helper function (`get_my_company_id()`) to ensure users can only ever see data belonging to their own company.

This isolation was verified end-to-end using two real Supabase Auth test users (different companies) queried through the Supabase Python client — not just assumed from the SQL alone.
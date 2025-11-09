-- ============================================================================
-- Setup Supabase Auth Integration with Profiles Table
-- ============================================================================
-- Run this SQL in Supabase SQL Editor after applying Alembic migrations
-- This script sets up:
-- 1. Foreign key from profiles to auth.users with CASCADE delete
-- 2. Row Level Security policies
-- 3. Automatic profile creation trigger
-- 4. Performance indexes
-- ============================================================================

-- ============================================
-- PART 1: Add Foreign Key to auth.users
-- ============================================

ALTER TABLE public.profiles
  ADD CONSTRAINT profiles_user_id_fkey
  FOREIGN KEY (id)
  REFERENCES auth.users(id)
  ON DELETE CASCADE;

-- ============================================
-- PART 2: Enable Row Level Security
-- ============================================

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.card_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.review_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.levels ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cards ENABLE ROW LEVEL SECURITY;

-- ============================================
-- PART 3: Profiles RLS Policies
-- ============================================

CREATE POLICY "Users can view own profile"
  ON public.profiles
  FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
  ON public.profiles
  FOR UPDATE
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

CREATE POLICY "Users can insert own profile"
  ON public.profiles
  FOR INSERT
  WITH CHECK (auth.uid() = id);

-- ============================================
-- PART 4: Card Progress RLS Policies
-- ============================================

CREATE POLICY "Users can view own card progress"
  ON public.card_progress
  FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own card progress"
  ON public.card_progress
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own card progress"
  ON public.card_progress
  FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- ============================================
-- PART 5: Review Logs RLS Policies
-- ============================================

CREATE POLICY "Users can view own review logs"
  ON public.review_logs
  FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own review logs"
  ON public.review_logs
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- ============================================
-- PART 6: Public Read Access (Levels & Cards)
-- ============================================

CREATE POLICY "Anyone can view levels"
  ON public.levels
  FOR SELECT
  USING (true);

CREATE POLICY "Anyone can view cards"
  ON public.cards
  FOR SELECT
  USING (true);

-- ============================================
-- PART 7: Grant Permissions to Auth Admin
-- ============================================

GRANT USAGE ON SCHEMA public TO supabase_auth_admin;
GRANT ALL ON public.profiles TO supabase_auth_admin;

-- ============================================
-- PART 8: Create Trigger Function for Auto Profile Creation
-- ============================================

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = ''
AS $$
BEGIN
  -- Insert new profile with data from user metadata
  INSERT INTO public.profiles (id, name, current_level, created_at, updated_at)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'name', 'New User'),
    1,  -- Start at level 1
    NOW(),
    NOW()
  );
  RETURN NEW;
EXCEPTION WHEN OTHERS THEN
  -- Log error but don't block user creation
  RAISE WARNING 'Failed to create profile for user %: %', NEW.id, SQLERRM;
  RETURN NEW;
END;
$$;

-- ============================================
-- PART 9: Create Trigger on auth.users
-- ============================================

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

-- ============================================
-- PART 10: Performance Indexes
-- ============================================

-- Index for due cards query (most frequent)
CREATE INDEX IF NOT EXISTS idx_card_progress_next_review
  ON public.card_progress(user_id, next_review);

-- Index for review analytics
CREATE INDEX IF NOT EXISTS idx_review_logs_user_created
  ON public.review_logs(user_id, reviewed_at DESC);

-- Index for card-level joins
CREATE INDEX IF NOT EXISTS idx_cards_level
  ON public.cards(level_id);

-- ============================================
-- PART 11: Verify Setup
-- ============================================

-- Check RLS policies
SELECT
  schemaname,
  tablename,
  policyname,
  permissive,
  roles,
  cmd
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;

-- Check foreign keys
SELECT
  tc.table_name,
  kcu.column_name,
  ccu.table_name AS foreign_table_name,
  ccu.column_name AS foreign_column_name,
  rc.delete_rule
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
  AND ccu.table_schema = tc.table_schema
JOIN information_schema.referential_constraints AS rc
  ON tc.constraint_name = rc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_schema = 'public'
ORDER BY tc.table_name;

-- Check triggers
SELECT
  event_object_schema,
  event_object_table,
  trigger_name,
  event_manipulation,
  action_timing,
  action_statement
FROM information_schema.triggers
WHERE event_object_schema IN ('auth', 'public')
ORDER BY event_object_table, trigger_name;

-- ============================================================================
-- Setup Complete!
-- ============================================================================
-- Test by creating a new user via Supabase Auth
-- Profile should be automatically created with current_level = 1
-- ============================================================================

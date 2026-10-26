-- Staged ingestion is a database-enforced state machine:
-- staging -> ready -> published, or staging/ready -> failed.
CREATE TABLE public.fingerprint_ingestion_runs (
    ingestion_id uuid PRIMARY KEY,
    movie_id text NOT NULL REFERENCES public.movies (id) ON DELETE CASCADE,
    modality text NOT NULL CHECK (modality IN ('video', 'audio')),
    status text NOT NULL DEFAULT 'staging'
        CHECK (status IN ('staging', 'ready', 'published', 'failed')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    ready_at timestamptz,
    published_at timestamptz,
    failed_at timestamptz
);

CREATE INDEX fingerprint_ingestion_runs_cleanup_idx
    ON public.fingerprint_ingestion_runs (status, updated_at)
    WHERE status IN ('staging', 'ready', 'failed');

CREATE TABLE public.fingerprint_ingestion_staging (
    ingestion_id uuid NOT NULL REFERENCES public.fingerprint_ingestion_runs (ingestion_id) ON DELETE CASCADE,
    movie_id text NOT NULL REFERENCES public.movies (id) ON DELETE CASCADE,
    hash bigint NOT NULL,
    timestamp_ms bigint NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX fingerprint_ingestion_staging_run_idx
    ON public.fingerprint_ingestion_staging (ingestion_id, movie_id);

CREATE TABLE public.audio_fingerprint_ingestion_staging (
    ingestion_id uuid NOT NULL REFERENCES public.fingerprint_ingestion_runs (ingestion_id) ON DELETE CASCADE,
    movie_id text NOT NULL REFERENCES public.movies (id) ON DELETE CASCADE,
    hash bigint NOT NULL,
    timestamp_ms bigint NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX audio_fingerprint_ingestion_staging_run_idx
    ON public.audio_fingerprint_ingestion_staging (ingestion_id, movie_id);

ALTER TABLE public.fingerprint_ingestion_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.fingerprint_ingestion_staging ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audio_fingerprint_ingestion_staging ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.fingerprint_ingestion_runs
    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON TABLE public.fingerprint_ingestion_staging
    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON TABLE public.audio_fingerprint_ingestion_staging
    FROM PUBLIC, anon, authenticated;
-- The service role can inspect runs but cannot bypass the guarded RPCs to
-- change state or write/delete staging rows directly.
REVOKE ALL ON TABLE public.fingerprint_ingestion_runs,
    public.fingerprint_ingestion_staging,
    public.audio_fingerprint_ingestion_staging FROM service_role;
GRANT SELECT ON TABLE public.fingerprint_ingestion_runs,
    public.fingerprint_ingestion_staging,
    public.audio_fingerprint_ingestion_staging TO service_role;

CREATE OR REPLACE FUNCTION public.create_fingerprint_ingestion(
    p_ingestion_id uuid,
    p_movie_id text,
    p_modality text
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $function$
BEGIN
    IF p_ingestion_id IS NULL OR p_movie_id IS NULL OR pg_catalog.btrim(p_movie_id) = ''
       OR p_modality NOT IN ('video', 'audio') THEN
        RAISE EXCEPTION 'A valid ingestion ID, movie ID, and modality are required.'
            USING ERRCODE = '22023';
    END IF;

    INSERT INTO public.fingerprint_ingestion_runs
        (ingestion_id, movie_id, modality)
    VALUES (p_ingestion_id, p_movie_id, p_modality);

    RETURN p_ingestion_id;
END;
$function$;

CREATE OR REPLACE FUNCTION public.stage_video_fingerprint_batch(
    p_ingestion_id uuid,
    p_movie_id text,
    p_fingerprints jsonb
)
RETURNS bigint
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $function$
DECLARE
    run_row public.fingerprint_ingestion_runs%ROWTYPE;
    inserted_count bigint;
BEGIN
    -- Lock order is always run row first, then movie/modality advisory lock.
    SELECT * INTO run_row
    FROM public.fingerprint_ingestion_runs
    WHERE ingestion_id = p_ingestion_id
    FOR UPDATE;

    IF NOT FOUND OR run_row.movie_id <> p_movie_id OR run_row.modality <> 'video'
       OR run_row.status <> 'staging' THEN
        RAISE EXCEPTION 'Video ingestion run is missing, mismatched, or not staging.'
            USING ERRCODE = '22023';
    END IF;
    IF p_fingerprints IS NULL OR pg_catalog.jsonb_typeof(p_fingerprints) <> 'array'
       OR pg_catalog.jsonb_array_length(p_fingerprints) = 0 THEN
        RAISE EXCEPTION 'A nonempty video fingerprint batch is required.'
            USING ERRCODE = '22023';
    END IF;

    INSERT INTO public.fingerprint_ingestion_staging
        (ingestion_id, movie_id, hash, timestamp_ms)
    SELECT p_ingestion_id, p_movie_id, item.hash, item.timestamp_ms
    FROM pg_catalog.jsonb_to_recordset(p_fingerprints)
        AS item(hash bigint, timestamp_ms bigint);

    GET DIAGNOSTICS inserted_count = ROW_COUNT;
    RETURN inserted_count;
END;
$function$;

CREATE OR REPLACE FUNCTION public.stage_audio_fingerprint_batch(
    p_ingestion_id uuid,
    p_movie_id text,
    p_fingerprints jsonb
)
RETURNS bigint
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $function$
DECLARE
    run_row public.fingerprint_ingestion_runs%ROWTYPE;
    inserted_count bigint;
BEGIN
    SELECT * INTO run_row
    FROM public.fingerprint_ingestion_runs
    WHERE ingestion_id = p_ingestion_id
    FOR UPDATE;

    IF NOT FOUND OR run_row.movie_id <> p_movie_id OR run_row.modality <> 'audio'
       OR run_row.status <> 'staging' THEN
        RAISE EXCEPTION 'Audio ingestion run is missing, mismatched, or not staging.'
            USING ERRCODE = '22023';
    END IF;
    IF p_fingerprints IS NULL OR pg_catalog.jsonb_typeof(p_fingerprints) <> 'array'
       OR pg_catalog.jsonb_array_length(p_fingerprints) = 0 THEN
        RAISE EXCEPTION 'A nonempty audio fingerprint batch is required.'
            USING ERRCODE = '22023';
    END IF;

    INSERT INTO public.audio_fingerprint_ingestion_staging
        (ingestion_id, movie_id, hash, timestamp_ms)
    SELECT p_ingestion_id, p_movie_id, item.hash, item.timestamp_ms
    FROM pg_catalog.jsonb_to_recordset(p_fingerprints)
        AS item(hash bigint, timestamp_ms bigint);

    GET DIAGNOSTICS inserted_count = ROW_COUNT;
    RETURN inserted_count;
END;
$function$;

CREATE OR REPLACE FUNCTION public.complete_fingerprint_ingestion(
    p_ingestion_id uuid,
    p_movie_id text,
    p_modality text
)
RETURNS bigint
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $function$
DECLARE
    run_row public.fingerprint_ingestion_runs%ROWTYPE;
    staged_count bigint;
BEGIN
    SELECT * INTO run_row
    FROM public.fingerprint_ingestion_runs
    WHERE ingestion_id = p_ingestion_id
    FOR UPDATE;

    IF NOT FOUND OR run_row.movie_id <> p_movie_id OR run_row.modality <> p_modality
       OR run_row.status <> 'staging' THEN
        RAISE EXCEPTION 'Ingestion run is missing, mismatched, or not staging.'
            USING ERRCODE = '22023';
    END IF;

    IF p_modality = 'video' THEN
        SELECT pg_catalog.count(*) INTO staged_count
        FROM public.fingerprint_ingestion_staging
        WHERE ingestion_id = p_ingestion_id AND movie_id = p_movie_id;
    ELSIF p_modality = 'audio' THEN
        SELECT pg_catalog.count(*) INTO staged_count
        FROM public.audio_fingerprint_ingestion_staging
        WHERE ingestion_id = p_ingestion_id AND movie_id = p_movie_id;
    ELSE
        RAISE EXCEPTION 'Unsupported ingestion modality.' USING ERRCODE = '22023';
    END IF;

    IF staged_count = 0 THEN
        RAISE EXCEPTION 'Cannot complete an empty ingestion run.' USING ERRCODE = '22023';
    END IF;

    UPDATE public.fingerprint_ingestion_runs
    SET status = 'ready', ready_at = pg_catalog.now(), updated_at = pg_catalog.now()
    WHERE ingestion_id = p_ingestion_id;
    RETURN staged_count;
END;
$function$;

CREATE OR REPLACE FUNCTION public.fail_fingerprint_ingestion(
    p_ingestion_id uuid,
    p_movie_id text,
    p_modality text
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $function$
DECLARE
    run_row public.fingerprint_ingestion_runs%ROWTYPE;
BEGIN
    IF p_ingestion_id IS NULL OR p_movie_id IS NULL OR p_modality IS NULL THEN
        RAISE EXCEPTION 'A valid ingestion ID, movie ID, and modality are required.'
            USING ERRCODE = '22023';
    END IF;

    SELECT * INTO run_row
    FROM public.fingerprint_ingestion_runs
    WHERE ingestion_id = p_ingestion_id
    FOR UPDATE;

    IF NOT FOUND
       OR run_row.movie_id IS DISTINCT FROM p_movie_id
       OR run_row.modality IS DISTINCT FROM p_modality THEN
        RAISE EXCEPTION 'Ingestion run is missing or mismatched.' USING ERRCODE = '22023';
    END IF;
    IF run_row.status NOT IN ('staging', 'ready') THEN
        RAISE EXCEPTION 'Only staging or ready runs can be failed.' USING ERRCODE = '22023';
    END IF;

    UPDATE public.fingerprint_ingestion_runs
    SET status = 'failed', failed_at = pg_catalog.now(), updated_at = pg_catalog.now()
    WHERE ingestion_id = p_ingestion_id;
    RETURN true;
END;
$function$;

CREATE OR REPLACE FUNCTION public.finalize_video_fingerprint_ingestion(
    p_ingestion_id uuid,
    p_movie_id text
)
RETURNS bigint
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $function$
DECLARE
    run_row public.fingerprint_ingestion_runs%ROWTYPE;
    staged_count bigint;
BEGIN
    SELECT * INTO run_row
    FROM public.fingerprint_ingestion_runs
    WHERE ingestion_id = p_ingestion_id
    FOR UPDATE;
    IF NOT FOUND OR run_row.movie_id <> p_movie_id OR run_row.modality <> 'video'
       OR run_row.status <> 'ready' THEN
        RAISE EXCEPTION 'Video ingestion run is missing, mismatched, or not ready.'
            USING ERRCODE = '22023';
    END IF;

    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(p_movie_id || ':video', 0)
    );
    SELECT pg_catalog.count(*) INTO staged_count
    FROM public.fingerprint_ingestion_staging
    WHERE ingestion_id = p_ingestion_id AND movie_id = p_movie_id;
    IF staged_count = 0 THEN
        RAISE EXCEPTION 'Cannot publish an empty video ingestion run.' USING ERRCODE = '22023';
    END IF;

    DELETE FROM public.fingerprints WHERE movie_id = p_movie_id;
    INSERT INTO public.fingerprints (hash, movie_id, timestamp_ms)
    SELECT hash, movie_id, timestamp_ms
    FROM public.fingerprint_ingestion_staging
    WHERE ingestion_id = p_ingestion_id AND movie_id = p_movie_id;
    DELETE FROM public.fingerprint_ingestion_staging
    WHERE ingestion_id = p_ingestion_id;
    UPDATE public.fingerprint_ingestion_runs
    SET status = 'published', published_at = pg_catalog.now(), updated_at = pg_catalog.now()
    WHERE ingestion_id = p_ingestion_id;
    RETURN staged_count;
END;
$function$;

CREATE OR REPLACE FUNCTION public.finalize_audio_fingerprint_ingestion(
    p_ingestion_id uuid,
    p_movie_id text
)
RETURNS bigint
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $function$
DECLARE
    run_row public.fingerprint_ingestion_runs%ROWTYPE;
    staged_count bigint;
BEGIN
    SELECT * INTO run_row
    FROM public.fingerprint_ingestion_runs
    WHERE ingestion_id = p_ingestion_id
    FOR UPDATE;
    IF NOT FOUND OR run_row.movie_id <> p_movie_id OR run_row.modality <> 'audio'
       OR run_row.status <> 'ready' THEN
        RAISE EXCEPTION 'Audio ingestion run is missing, mismatched, or not ready.'
            USING ERRCODE = '22023';
    END IF;

    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtextextended(p_movie_id || ':audio', 0)
    );
    SELECT pg_catalog.count(*) INTO staged_count
    FROM public.audio_fingerprint_ingestion_staging
    WHERE ingestion_id = p_ingestion_id AND movie_id = p_movie_id;
    IF staged_count = 0 THEN
        RAISE EXCEPTION 'Cannot publish an empty audio ingestion run.' USING ERRCODE = '22023';
    END IF;

    DELETE FROM public.audio_fingerprints WHERE movie_id = p_movie_id;
    INSERT INTO public.audio_fingerprints (hash, movie_id, timestamp_ms)
    SELECT hash, movie_id, timestamp_ms
    FROM public.audio_fingerprint_ingestion_staging
    WHERE ingestion_id = p_ingestion_id AND movie_id = p_movie_id;
    DELETE FROM public.audio_fingerprint_ingestion_staging
    WHERE ingestion_id = p_ingestion_id;
    UPDATE public.fingerprint_ingestion_runs
    SET status = 'published', published_at = pg_catalog.now(), updated_at = pg_catalog.now()
    WHERE ingestion_id = p_ingestion_id;
    RETURN staged_count;
END;
$function$;

REVOKE ALL ON FUNCTION public.create_fingerprint_ingestion(uuid, text, text)
    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.stage_video_fingerprint_batch(uuid, text, jsonb)
    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.stage_audio_fingerprint_batch(uuid, text, jsonb)
    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.complete_fingerprint_ingestion(uuid, text, text)
    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.fail_fingerprint_ingestion(uuid, text, text)
    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.finalize_video_fingerprint_ingestion(uuid, text)
    FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.finalize_audio_fingerprint_ingestion(uuid, text)
    FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.create_fingerprint_ingestion(uuid, text, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.stage_video_fingerprint_batch(uuid, text, jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.stage_audio_fingerprint_batch(uuid, text, jsonb) TO service_role;
GRANT EXECUTE ON FUNCTION public.complete_fingerprint_ingestion(uuid, text, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.fail_fingerprint_ingestion(uuid, text, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.finalize_video_fingerprint_ingestion(uuid, text) TO service_role;
GRANT EXECUTE ON FUNCTION public.finalize_audio_fingerprint_ingestion(uuid, text) TO service_role;

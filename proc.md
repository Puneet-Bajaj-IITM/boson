

As requested, I have compiled all the stored procedures currently in use for your review. Below are the details:

1. **Function:** `update_prompt_status`
```sql
CREATE OR REPLACE FUNCTION update_prompt_status(
    prompt_id INT,
    user_task TEXT
) RETURNS VOID AS $$
BEGIN
    IF user_task = 'create' THEN
        UPDATE prompts
        SET create_end_time = NOW(),
            status = CASE
                        WHEN phase = 'create' THEN 'done'
                        WHEN phase = 'review' THEN 'yts'
                        ELSE status
                     END
        WHERE id = prompt_id;
    ELSIF user_task = 'review' THEN
        UPDATE prompts
        SET review_end_time = NOW(),
            status = 'done'
        WHERE id = prompt_id;
    END IF;
END;
$$ LANGUAGE plpgsql;
```

2. **Function:** `initialize_response_scores`
```sql
CREATE OR REPLACE FUNCTION initialize_response_scores(
    p_create_user VARCHAR(50), 
    p_user_task VARCHAR(50), 
    p_filename VARCHAR(255)
) RETURNS TABLE(
    prompt_id INTEGER,
    question TEXT,
    response_1_id INTEGER,
    response_1 TEXT,
    judgement_1_1_id INTEGER,
    judgement_1_1_score INTEGER,
    judgement_1_1_rubric TEXT,
    judgement_1_1_reason TEXT,
    judgement_1_2_id INTEGER,
    judgement_1_2_score INTEGER,
    judgement_1_2_rubric TEXT,
    judgement_1_2_reason TEXT,
    judgement_1_3_id INTEGER,
    judgement_1_3_score INTEGER,
    judgement_1_3_rubric TEXT,
    judgement_1_3_reason TEXT,
    response_2_id INTEGER,
    response_2 TEXT,
    judgement_2_1_id INTEGER,
    judgement_2_1_score INTEGER,
    judgement_2_1_rubric TEXT,
    judgement_2_1_reason TEXT,
    judgement_2_2_id INTEGER,
    judgement_2_2_score INTEGER,
    judgement_2_2_rubric TEXT,
    judgement_2_2_reason TEXT,
    judgement_2_3_id INTEGER,
    judgement_2_3_score INTEGER,
    judgement_2_3_rubric TEXT,
    judgement_2_3_reason TEXT,
    response_3_id INTEGER,
    response_3 TEXT,
    judgement_3_1_id INTEGER,
    judgement_3_1_score INTEGER,
    judgement_3_1_rubric TEXT,
    judgement_3_1_reason TEXT,
    judgement_3_2_id INTEGER,
    judgement_3_2_score INTEGER,
    judgement_3_2_rubric TEXT,
    judgement_3_2_reason TEXT,
    judgement_3_3_id INTEGER,
    judgement_3_3_score INTEGER,
    judgement_3_3_rubric TEXT,
    judgement_3_3_reason TEXT
) AS $$
DECLARE
    v_prompt_id INTEGER;
    v_file_id INTEGER;
BEGIN
    SELECT id INTO v_file_id
    FROM files
    WHERE filename = p_filename
    LIMIT 1;

    IF v_file_id IS NULL THEN
        RAISE EXCEPTION 'No file found with the specified filename: %', p_filename;
    END IF;

    IF p_user_task = 'create' THEN
        UPDATE prompts
        SET create_user = p_create_user, status = 'wip', create_start_time = NOW()
        WHERE id = (
            SELECT id
            FROM prompts
            WHERE status = 'yts' AND phase = 'create' AND file_id = v_file_id
            LIMIT 1
            FOR UPDATE SKIP LOCKED
        )
        RETURNING id INTO v_prompt_id;
    ELSIF p_user_task = 'review' THEN
        UPDATE prompts
        SET review_user = p_create_user, status = 'wip', review_start_time = NOW()
        WHERE id = (
            SELECT id
            FROM prompts
            WHERE status = 'yts' AND phase = 'review' AND file_id = v_file_id
            LIMIT 1
            FOR UPDATE SKIP LOCKED
        )
        RETURNING id INTO v_prompt_id;
    END IF;

    IF v_prompt_id IS NULL THEN
        RAISE NOTICE 'No prompt was updated. Possibly no prompt with the specified criteria.';
        RETURN;
    END IF;

    RETURN QUERY
    SELECT
        p.id AS prompt_id,
        p.prompt_text AS question,
        r1.id AS response_1_id,
        r1.response_text AS response_1,
        j11.id AS judgement_1_1_id,
        j11.score AS judgement_1_1_score,
        j11.rubric AS judgement_1_1_rubric,
        j11.reason AS judgement_1_1_reason,
        j12.id AS judgement_1_2_id,
        j12.score AS judgement_1_2_score,
        j12.rubric AS judgement_1_2_rubric,
        j12.reason AS judgement_1_2_reason,
        j13.id AS judgement_1_3_id,
        j13.score AS judgement_1_3_score,
        j13.rubric AS judgement_1_3_rubric,
        j13.reason AS judgement_1_3_reason,
        r2.id AS response_2_id,
        r2.response_text AS response_2,
        j21.id AS judgement_2_1_id,
        j21.score AS judgement_2_1_score,
        j21.rubric AS judgement_2_1_rubric,
        j21.reason AS judgement_2_1_reason,
        j22.id AS judgement_2_2_id,
        j22.score AS judgement_2_2_score,
        j22.rubric AS judgement_2_2_rubric,
        j22.reason AS judgement_2_2_reason,
        j23.id AS judgement_2_3_id,
        j23.score AS judgement_2_3_score,
        j23.rubric AS judgement_2_3_rubric,
        j23.reason AS judgement_2_3_reason,
        r3.id AS response_3_id,
        r3.response_text AS response_3,
        j31.id AS judgement_3_1_id,
        j31.score AS judgement_3_1_score,
        j31.rubric AS judgement_3_1_rubric,
        j31.reason AS judgement_3_1_reason,
        j32.id AS judgement_3_2_id,
        j32.score AS judgement_3_2_score,
        j32.rubric AS judgement_3_2_rubric,
        j32.reason AS judgement_3_2_reason,
        j33.id AS judgement_3_3_id,
        j33.score AS judgement_3_3_score,
        j33.rubric AS judgement_3_3_rubric,
        j33.reason AS judgement_3_3_reason
    FROM
        prompts p
    LEFT JOIN responses r1 ON p.id = r1.prompt_id
    LEFT JOIN responses r2 ON p.id = r2.prompt_id AND r2.id != r1.id
    LEFT JOIN responses r3 ON p.id = r3.prompt_id AND r3.id NOT IN (r1.id, r2.id)
    LEFT JOIN judgements j11 ON r1.id = j11.response_id
    LEFT JOIN judgements j12 ON r1.id = j12.response_id AND j12.id != j11.id
    LEFT JOIN judgements j13 ON r1.id = j13.response_id AND j13.id NOT IN (j11.id, j12.id)
    LEFT JOIN judgements j21 ON r2.id = j21.response_id
    LEFT JOIN judgements j22 ON r2.id = j22.response_id AND j22.id != j21.id
    LEFT JOIN judgements j23 ON r2.id = j23.response_id AND j23.id NOT IN (j21.id, j22.id)
    LEFT JOIN judgements j31 ON r3.id = j31.response_id
    LEFT JOIN judgements j32 ON r3.id = j32.response_id AND j32.id != j31.id
    LEFT JOIN judgements j33 ON r3.id = j33.response_id AND j33.id NOT IN (j31.id, j32.id)
    WHERE
        p.id = v_prompt_id
        LIMIT 1;
END;
$$ LANGUAGE plpgsql;
```

3. **Function:** `insert_file_data`
```sql
CREATE OR REPLACE FUNCTION insert_file_data(p_filename TEXT, p_data JSONB)
RETURNS TEXT AS $$
DECLARE
    file_id INT;
    prompt_id INT;
    response_id INT;
    prompt_data JSONB;
    response_text TEXT;
    judgement_data JSONB;
    judgement JSONB;
BEGIN
    PERFORM 1 FROM files WHERE files.filename = p_filename;
    IF FOUND THEN
        RETURN 'File ' || p_filename || ' already exists in the database.';
    END IF;

    INSERT INTO files (filename) VALUES (p_filename) RETURNING id INTO file_id;

    FOR prompt_data IN SELECT * FROM jsonb_array_elements(p_data)
    LOOP
        INSERT INTO prompts (prompt_text, domain, task, meta_data, phase, status, file_id)
        VALUES (
            prompt_data->>'prompt',
            LEFT(prompt_data->'meta'->>'prompt_domain', 100),
            LEFT(prompt_data->'meta'->>'prompt_task', 100),
            prompt_data->'meta'::TEXT,
            'create',
            '

yts',
            file_id
        ) RETURNING id INTO prompt_id;

        FOR response_text IN SELECT jsonb_array_elements_text(prompt_data->'responses')
        LOOP
            INSERT INTO responses (prompt_id, response_text) VALUES (prompt_id, response_text) RETURNING id INTO response_id;

            FOR judgement IN SELECT * FROM jsonb_array_elements(response_text->'judgement')
            LOOP
                INSERT INTO judgements (response_id, score, rubric, reason)
                VALUES (
                    response_id,
                    judgement->>'score'::INTEGER,
                    LEFT(judgement->>'rubric', 100),
                    LEFT(judgement->>'reason', 250)
                );
            END LOOP;
        END LOOP;
    END LOOP;

    RETURN 'Data has been successfully inserted for file: ' || p_filename;
END;
$$ LANGUAGE plpgsql;
```

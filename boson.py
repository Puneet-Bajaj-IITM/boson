
import psycopg2
from psycopg2 import sql

def get_db_connection():
    return psycopg2.connect(
        dbname="boson",
        user="ubuntu",
        password="Ddd@1234",  # Replace with your password
        host="localhost"
    )



def setup_database():
    conn = get_db_connection()
    cur = conn.cursor()

    # Drop existing tables
    # cur.execute("""
    #     DO $$ DECLARE
    #         r RECORD;
    #     BEGIN
    #         FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = current_schema()) LOOP
    #             EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
    #         END LOOP;
    #     END $$;
    # """)

    # # Drop existing functions
    # cur.execute("""
    #     DO $$ DECLARE
    #         r RECORD;
    #     BEGIN
    #         FOR r IN (SELECT routine_name FROM information_schema.routines WHERE routine_type='FUNCTION' AND specific_schema = current_schema()) LOOP
    #             EXECUTE 'DROP FUNCTION IF EXISTS ' || quote_ident(r.routine_name) || ' CASCADE';
    #         END LOOP;
    #     END $$;
    # """)

    # Create users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(50) NOT NULL,
            user_role VARCHAR(50) NOT NULL
        )
    """)

    # Insert test data
    cur.execute("""
        INSERT INTO users (username, password, user_role) VALUES
        ('creator1', 'password1', 'creator'),
        ('creator2', 'password2', 'creator'),
        ('reviewer1', 'password3', 'reviewer'),
        ('admin', 'admin', 'admin')
        ON CONFLICT (username) DO NOTHING
    """)

    # Create files table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id SERIAL PRIMARY KEY,
            filename VARCHAR(255) UNIQUE NOT NULL
        )
    """)

    # Create prompts table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS prompts (
            id SERIAL PRIMARY KEY,
            line_id INTEGER,
            prompt_text TEXT NOT NULL,
            domain VARCHAR(255),
            task VARCHAR(255),
            meta_data JSONB,
            phase VARCHAR(20),
            status VARCHAR(20),
            file_id INTEGER REFERENCES files(id),
            create_user VARCHAR(20),
            review_user VARCHAR(20),
            create_start_time TIMESTAMP,
            create_end_time TIMESTAMP,
            create_skip_reason TEXT,
            create_skip_cat TEXT,
            review_skip_reason TEXT,
            review_skip_cat TEXT,
            review_start_time TIMESTAMP,
            review_end_time TIMESTAMP
        )
    """)

    # Create responses table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS responses (
            id SERIAL PRIMARY KEY,
            prompt_id INTEGER REFERENCES prompts(id),
            response_text TEXT NOT NULL
        )
    """)

    # Create judgements table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS judgements (
            id SERIAL PRIMARY KEY,
            response_id INTEGER REFERENCES responses(id),
            reason TEXT,
            rubric TEXT,
            score INTEGER
        )
    """)

    # Create labelled_responses table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS labelled_responses (
            id SERIAL PRIMARY KEY,
            response_id INTEGER UNIQUE REFERENCES responses(id),
            score INTEGER
        )
    """)

    # Create labelled_judgements table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS labelled_judgements (
            id SERIAL PRIMARY KEY,
            judgement_id INTEGER UNIQUE REFERENCES judgements(id),
            reason TEXT,
            score INTEGER
        )
    """)

    # Create reviewed_responses table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reviewed_responses (
            id SERIAL PRIMARY KEY,
            response_id INTEGER REFERENCES responses(id),
            score INTEGER
        )
    """)

    # Create reviewed_judgements table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reviewed_judgements (
            id SERIAL PRIMARY KEY,
            judgement_id INTEGER REFERENCES judgements(id),
            reason TEXT,
            score INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS archived_files (
            id SERIAL PRIMARY KEY,
            filename VARCHAR(255) UNIQUE NOT NULL
        )
    """)

    conn.commit()
    cur.close()
    conn.close()
setup_database()
print("Database setup complete.")


from pickle import NONE

import psycopg2
from psycopg2 import sql

def get_project_summary(from_day, from_month, from_year, to_day, to_month, to_year):
    # Define the date range
    from_date = f"{from_year}-{from_month}-{from_day}"
    to_date = f"{to_year}-{to_month}-{to_day}"
    if from_date > to_date:
        gr.Warning('Invalid Range Selected!')

    # Define the SQL query
    query = f"""
    SELECT review_skip_cat, COUNT(*) as total_prompts
    FROM prompts
    WHERE review_start_time >= '{from_date}' AND review_start_time<= '{to_date}'
    GROUP BY review_skip_cat
    """

    query2 = f"""
    SELECT create_skip_cat, COUNT(*) as total_prompts
    FROM prompts
    WHERE create_start_time >= '{from_date}' AND create_start_time<= '{to_date}'
    GROUP BY create_skip_cat
    """

    # Connect to the PostgreSQL database
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query)
        result = cur.fetchall()
        cur.execute(f"SELECT COUNT(*) FROM prompts WHERE create_start_time >= '{from_date}' AND create_start_time<= '{to_date}'")
        length = cur.fetchone()[0]
        cur.execute(query2)
        result2 = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error connecting to PostgreSQL database: {e}")
        return pd.DataFrame({'Skip Category': [], 'Total Prompts': []})

    # Prepare the data for the DataFrame
    categories = ['NFSW', 'Lack of Knowledge', 'Bad Data', 'No Skip']
    total_prompts = {category: 0 for category in categories}

    s = 0
    for row in result:
        category, count = row
        if category in total_prompts:
            s += count
            total_prompts[category] += count

    for row in result2:
        category, count = row
        if category in total_prompts:
            s += count
            total_prompts[category] += count

    total_prompts['No Skip'] = length - s

    # Create the DataFrame
    df = pd.DataFrame({
        'Skip Category': categories,
        'Total Prompts': [total_prompts[category] for category in categories]
    })

    return df

def initialize_p_summary():

    # Define the SQL query
    query = f"""
    SELECT review_skip_cat, COUNT(*) as total_prompts
    FROM prompts
    GROUP BY review_skip_cat
    """

    query2 = f"""
    SELECT create_skip_cat, COUNT(*) as total_prompts
    FROM prompts
    GROUP BY create_skip_cat
    """

    # Connect to the PostgreSQL database
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(query)
        result = cur.fetchall()
        cur.execute('SELECT COUNT(*) FROM prompts;')
        length = cur.fetchone()[0]
        cur.execute(query2)
        result2 = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error connecting to PostgreSQL database: {e}")
        return pd.DataFrame({'Skip Category': [], 'Total Prompts': []})

    # Prepare the data for the DataFrame
    categories = ['NFSW', 'Lack of Knowledge', 'Bad Data', 'No Skip']
    total_prompts = {category: 0 for category in categories}

    s = 0
    for row in result:
        category, count = row
        if category in total_prompts:
            s += count
            total_prompts[category] += count

    for row in result2:
        category, count = row
        if category in total_prompts:
            s += count
            total_prompts[category] += count

    total_prompts['No Skip'] = length - s

    # Create the DataFrame
    df = pd.DataFrame({
        'Skip Category': categories,
        'Total Prompts': [total_prompts[category] for category in categories]
    })

    return df

# Generate list of months
months = [f"{month:02d}" for month in range(1, 13)]

# Generate list of days
days = [f"{day:02d}" for day in range(1, 32)]

# Generate list of years (example range: 1900 to 2100)
years = [str(year) for year in range(2024, 2051)]

def insert_file_data(filename, data):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Convert the data dictionary to JSON
        data_json = json.dumps(data)

        # Execute the stored procedure
        cur.execute("SELECT insert_file_data(%s, %s::jsonb)", (filename, data_json))

        # Fetch the result
        result = cur.fetchone()[0]

        # Commit the transaction
        conn.commit()

        return result

    except (Exception, psycopg2.DatabaseError) as error:
        # Rollback the transaction in case of error
        if conn:
            conn.rollback()
        gr.Warning(error)

    finally:
        # Close the database connection
        if cur:
            cur.close()
        if conn:
            conn.close()


def get_pro_report(from_day, from_month, from_year, to_day, to_month, to_year):
    # Define the date range
    from_date = f'{from_year}-{from_month}-{from_day}'
    to_date = f'{to_year}-{to_month}-{to_day}'

    if from_date > to_date:
        gr.Warning('Invalid Range Selected!')


    # Initialize an empty list to store data
    data = []

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Call the stored procedure using CALL
        cur.execute("SELECT * FROM get_pro_report(%s::TIMESTAMP, %s::TIMESTAMP)", (from_date, to_date))

        # Fetch all results
        results = cur.fetchall()

        if results:
            # Process each row and append to data list
            for row in results:
                data.append({
                    'User Name': row[0],
                    'Completed Date': row[1],                  
                    'JSON File Name': row[3],
                    'Task': row[4],
                    'Status': row[2],
                    'Rating Average': row[5],
                    'Total Record Skipped': row[6],
                    'Total Record Completed': row[7],
                    'Duration (Min)': row[8]
                })

    except Exception as e:
        print(results)
        print(f"Error connecting to PostgreSQL database: {e}")

    finally:
        # Ensure cursor and connection are closed even if an error occurs
        if cur:
            cur.close()
        if conn:
            conn.close()

    # Convert list of dictionaries to DataFrame
    if data == []:
        gr.Warning('No Data Found')
    df = pd.DataFrame(data)
    return df


import psycopg2
import pandas as pd

def initialize_pro_report():
    df = pd.DataFrame(columns=['User Name', 'Completed Date', 'JSON File Name', 'Task', "Status",
                               'Rating Average', 'Total Record Skipped', 'Total Record Completed',
                               'Duration (Min)'])

    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Execute the DO block to call the stored procedure and capture output
        cur.execute('SELECT * FROM initialize_pro_report()')

        # Fetch all results from the cursor
        result = cur.fetchall()

        if result:
            # Assuming 'result' contains your data
            df = pd.DataFrame(result, columns=['User Name', 'Completed Date', 'Status', 'JSON File Name', 'Task',
                                              'Rating Average', 'Total Record Skipped', 'Total Record Completed',
                                              'Duration (Min)'])

            # Reordering columns
            df = df[['User Name', 'Completed Date', 'Task', 'Status', 'JSON File Name',
                    'Rating Average', 'Total Record Skipped', 'Total Record Completed',
                    'Duration (Min)']]

            # Now 'Status' column is moved after 'Task'


    except Exception as e:
        print(f"Error connecting to PostgreSQL database: {e}")

    finally:
        # Ensure cursor and connection are closed even if an error occurs
        if cur:
            cur.close()
        if conn:
            conn.close()
    return df



def process_jsonl_files(files):
    all_file_data = []

    for file in files:
        file_data = []
        filename = str(file.name.split('/')[-1])
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM files WHERE filename = %s", (filename,))
        result = cur.fetchone()
        if result:
            gr.Warning(f"Skipping File '{filename}' as it already exists")
        conn.commit()
        conn.close()
        with open(file.name, "r") as f:
            for line in f:
                json_data = json.loads(line)
                file_data.append(json_data)

        # Example: Insert first 3 records from each file into the database
        try:
            insert_file_data(filename, file_data)
            all_file_data.extend(file_data)
        except Exception as e:
            gr.Warning(f'Error in {filename} - {e}')

    return "Data processed and inserted successfully."

from tabulate import tabulate

def show_tables():
    conn = get_db_connection()
    cur = conn.cursor()

    # Query to retrieve all table names
    cur.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE';
    """)

    tables = cur.fetchall()

    print("Tables in the database:")
    for table in tables:
        table_name = table[0]
        cur.execute(f"SELECT * FROM {table_name} LIMIT 5")
        table_data = cur.fetchall()
        headers = [desc[0] for desc in cur.description]
        print(f"\nTable: {table_name}")
        print(tabulate(table_data, headers=headers, tablefmt="pretty"))

    cur.close()
    conn.close()


def create_stored_procedure(create_procedure_sql):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Execute the SQL command to create the stored procedure
        cur.execute(create_procedure_sql)
        conn.commit()
        print("Stored procedure created successfully.")
    finally:
        cur.close()
        conn.close()

proc = """
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
"""
create_stored_procedure(proc)
import json

info_d_func = """
CREATE OR REPLACE FUNCTION get_release_info(
    input_filenames TEXT[]
)
RETURNS TABLE (
    prompt_id INTEGER,
    user_name TEXT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    json_file_name VARCHAR(255),
    task TEXT,
    status TEXT,
    skip_cat TEXT,
    reason TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id AS prompt_id,
        p.create_user::TEXT AS user_name,
        p.create_start_time,
        p.create_end_time,
        f.filename::VARCHAR(255) AS json_file_name,
        'Create'::TEXT AS task,
        CASE WHEN p.review_user IS NOT NULL THEN 'Skip' ELSE p.status END::TEXT AS status,
        NULL::TEXT AS skip_cat,
        NULL::TEXT AS reason
    FROM prompts p
    JOIN files f ON p.file_id = f.id
    WHERE f.filename = ANY(input_filenames)
        AND p.create_user IS NOT NULL
        AND p.create_user <> ''
        AND p.status = 'wip'
        AND p.review_user IS NULL

    UNION ALL

    SELECT
        p.id AS prompt_id,
        p.review_user::TEXT AS user_name,
        p.review_start_time,
        p.review_end_time,
        f.filename::VARCHAR(255) AS json_file_name,
        'Review'::TEXT AS task,
        p.status::TEXT AS status,
        p.review_skip_cat::TEXT AS skip_cat,
        p.review_skip_reason::TEXT AS reason
    FROM prompts p
    JOIN files f ON p.file_id = f.id
    WHERE f.filename = ANY(input_filenames)
        AND p.review_user IS NOT NULL
        AND p.review_user <> ''
        AND p.status= 'wip'
        ;
END;
$$;



"""
create_stored_procedure(info_d_func)

info_d__with_username_func = """
CREATE OR REPLACE FUNCTION get_release_info_username(
    input_filenames TEXT[],
    input_usernames TEXT[]
)
RETURNS TABLE (
    prompt_id INTEGER,
    user_name TEXT,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    json_file_name VARCHAR(255),
    task TEXT,
    status TEXT,
    skip_cat TEXT,
    reason TEXT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id AS prompt_id,
        p.create_user::TEXT AS user_name,
        p.create_start_time,
        p.create_end_time,
        f.filename::VARCHAR(255) AS json_file_name,
        'Create'::TEXT AS task,
        CASE WHEN p.review_user IS NOT NULL THEN 'Skip' ELSE p.status END::TEXT AS status,
        NULL::TEXT AS skip_cat,
        NULL::TEXT AS reason
    FROM prompts p
    JOIN files f ON p.file_id = f.id
    WHERE f.filename = ANY(input_filenames)
        AND p.create_user IS NOT NULL
        AND p.create_user <> ''
        AND p.create_user = ANY(input_usernames)
        AND p.status = 'wip'
        AND p.review_user IS NULL

    UNION ALL

    SELECT
        p.id AS prompt_id,
        p.review_user::TEXT AS user_name,
        p.review_start_time,
        p.review_end_time,
        f.filename::VARCHAR(255) AS json_file_name,
        'Review'::TEXT AS task,
        p.status::TEXT AS status,
        p.review_skip_cat::TEXT AS skip_cat,
        p.review_skip_reason::TEXT AS reason
    FROM prompts p
    JOIN files f ON p.file_id = f.id
    WHERE f.filename = ANY(input_filenames)
        AND p.review_user IS NOT NULL
        AND p.review_user <> ''
        AND p.review_user = ANY(input_usernames)
        AND p.status = 'wip'
        ;
END;
$$;


"""
create_stored_procedure(info_d__with_username_func)

# SQL command to create the stored procedure
create_procedure_sql = """
CREATE OR REPLACE FUNCTION initialize_response_scores(p_create_user VARCHAR(50), p_user_task VARCHAR(50), p_filename VARCHAR(255))
RETURNS TABLE(
    prompt_id INTEGER,
    question TEXT,
    create_skip_reason TEXT,
    review_skip_reason TEXT,
    create_skip_cat TEXT,
    review_skip_cat TEXT,
    response_1_id INTEGER,
    response_1 TEXT,
    score_1 INTEGER,
    judgement_1_1_id INTEGER,
    judgement_1_1_score INTEGER,
    judgement_1_1_rubric TEXT,
    judgement_1_1_reason TEXT,
    judgement_1_2_id INTEGER,
    judgement_1_2_score INTEGER,
    judgement_1_2_rubric TEXT,
    judgement_1_2_reason TEXT,
    response_2_id INTEGER,
    response_2 TEXT,
    score_2 INTEGER,
    judgement_2_1_id INTEGER,
    judgement_2_1_score INTEGER,
    judgement_2_1_rubric TEXT,
    judgement_2_1_reason TEXT,
    judgement_2_2_id INTEGER,
    judgement_2_2_score INTEGER,
    judgement_2_2_rubric TEXT,
    judgement_2_2_reason TEXT,
    response_3_id INTEGER,
    response_3 TEXT,
    score_3 INTEGER,
    judgement_3_1_id INTEGER,
    judgement_3_1_score INTEGER,
    judgement_3_1_rubric TEXT,
    judgement_3_1_reason TEXT,
    judgement_3_2_id INTEGER,
    judgement_3_2_score INTEGER,
    judgement_3_2_rubric TEXT,
    judgement_3_2_reason TEXT
) AS $$
DECLARE
    v_prompt_id INTEGER;
    v_file_id INTEGER;
BEGIN
    -- Fetch file ID for the specified filename
    SELECT id INTO v_file_id
    FROM files
    WHERE filename = p_filename
    LIMIT 1;

    IF v_file_id IS NULL THEN
        RAISE EXCEPTION 'No file found with the specified filename: %', p_filename;
    END IF;

    -- Fetch a prompt with status 'yts' and the specified phase (create or review) and assign it to the create_user
    IF p_user_task = 'create' THEN
        SELECT id INTO v_prompt_id
        FROM prompts
        WHERE status = 'wip' AND phase = 'create' AND file_id = v_file_id AND create_user = p_create_user
        LIMIT 1;

        IF v_prompt_id IS NULL THEN
            UPDATE prompts
            SET create_user = p_create_user, status = 'wip', create_start_time = NOW()
            WHERE id = (
                SELECT id
                FROM prompts
                WHERE status = 'yts' AND phase = 'create' AND file_id = v_file_id
                ORDER BY id ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            RETURNING id INTO v_prompt_id;
        END IF;
    ELSIF p_user_task = 'review' THEN
        SELECT id INTO v_prompt_id
        FROM prompts
        WHERE status = 'wip' AND phase = 'review' AND file_id = v_file_id AND create_user = p_create_user
        LIMIT 1;

        IF v_prompt_id IS NULL THEN
            UPDATE prompts
            SET review_user = p_create_user, status = 'wip', review_start_time = NOW()
            WHERE id = (
                SELECT id
                FROM prompts
                WHERE status = 'yts' AND phase = 'review' AND file_id = v_file_id
                ORDER BY id ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            RETURNING id INTO v_prompt_id;
        END IF;
    END IF;

    -- Check if any row was updated
    IF v_prompt_id IS NULL THEN
        RAISE NOTICE 'No prompt was updated. Possibly no prompt with the specified criteria.';
        RETURN;
    END IF;

    -- Fetch corresponding responses and judgements, using labelled judgements if available
    RETURN QUERY
    SELECT
        p.id AS prompt_id,
        p.prompt_text AS question,
        p.create_skip_reason AS create_skip_reason,
        p.review_skip_reason AS review_skip_reason,
        p.create_skip_cat AS create_skip_cat,
        p.review_skip_cat AS review_skip_cat,
        r1.id AS response_1_id,
        r1.response_text AS response_1,
        lr1.score AS score_1,
        j11.id AS judgement_1_1_id,
        COALESCE(lj11.score, j11.score) AS judgement_1_1_score,
        j11.rubric AS judgement_1_1_rubric,
        COALESCE(lj11.reason, j11.reason) AS judgement_1_1_reason,
        j12.id AS judgement_1_2_id,
        COALESCE(lj12.score, j12.score) AS judgement_1_2_score,
        j12.rubric AS judgement_1_2_rubric,
        COALESCE(lj12.reason, j12.reason) AS judgement_1_2_reason,
        r2.id AS response_2_id,
        r2.response_text AS response_2,
        lr2.score AS score_2,
        j21.id AS judgement_2_1_id,
        COALESCE(lj21.score, j21.score) AS judgement_2_1_score,
        j21.rubric AS judgement_2_1_rubric,
        COALESCE(lj21.reason, j21.reason) AS judgement_2_1_reason,
        j22.id AS judgement_2_2_id,
        COALESCE(lj22.score, j22.score) AS judgement_2_2_score,
        j22.rubric AS judgement_2_2_rubric,
        COALESCE(lj22.reason, j22.reason) AS judgement_2_2_reason,
        r3.id AS response_3_id,
        r3.response_text AS response_3,
        lr3.score AS score_3,
        j31.id AS judgement_3_1_id,
        COALESCE(lj31.score, j31.score) AS judgement_3_1_score,
        j31.rubric AS judgement_3_1_rubric,
        COALESCE(lj31.reason, j31.reason) AS judgement_3_1_reason,
        j32.id AS judgement_3_2_id,
        COALESCE(lj32.score, j32.score) AS judgement_3_2_score,
        j32.rubric AS judgement_3_2_rubric,
        COALESCE(lj32.reason, j32.reason) AS judgement_3_2_reason
    FROM
        prompts p
    LEFT JOIN responses r1 ON p.id = r1.prompt_id
    LEFT JOIN responses r2 ON p.id = r2.prompt_id AND r2.id != r1.id
    LEFT JOIN responses r3 ON p.id = r3.prompt_id AND r3.id NOT IN (r1.id, r2.id)
    LEFT JOIN labelled_responses lr1 ON r1.id = lr1.response_id
    LEFT JOIN labelled_responses lr2 ON r2.id = lr2.response_id
    LEFT JOIN labelled_responses lr3 ON r3.id = lr3.response_id
    LEFT JOIN judgements j11 ON r1.id = j11.response_id
    LEFT JOIN labelled_judgements lj11 ON j11.id = lj11.judgement_id
    LEFT JOIN judgements j12 ON r1.id = j12.response_id AND j12.id != j11.id
    LEFT JOIN labelled_judgements lj12 ON j12.id = lj12.judgement_id
    LEFT JOIN judgements j21 ON r2.id = j21.response_id
    LEFT JOIN labelled_judgements lj21 ON j21.id = lj21.judgement_id
    LEFT JOIN judgements j22 ON r2.id = j22.response_id AND j22.id != j21.id
    LEFT JOIN labelled_judgements lj22 ON j22.id = lj22.judgement_id
    LEFT JOIN judgements j31 ON r3.id = j31.response_id
    LEFT JOIN labelled_judgements lj31 ON j31.id = lj31.judgement_id
    LEFT JOIN judgements j32 ON r3.id = j32.response_id AND j32.id != j31.id
    LEFT JOIN labelled_judgements lj32 ON j32.id = lj32.judgement_id
    WHERE
        p.id = v_prompt_id
        LIMIT 1;
END;
$$ LANGUAGE plpgsql;

"""


create_stored_procedure(create_procedure_sql)

sqlq = """
CREATE OR REPLACE FUNCTION insert_file_data(p_filename TEXT, p_data JSONB)
RETURNS TEXT AS $$
DECLARE
    file_id INT;
    line_id INT;
    prompt_id INT;
    response_id INT;
    prompt_data JSONB;
    response_text TEXT;
    judgement JSONB;
    rubric_count INT := 0;
    prompt_length INT;
    responses_length INT;
    judgements_length INT;
    random_index INTEGER;
    selected_rubric TEXT;
BEGIN
    -- Check if filename already exists
    PERFORM 1 FROM files WHERE files.filename = p_filename;
    IF FOUND THEN
        RETURN 'File ' || p_filename || ' already exists in the database.';
    END IF;

    -- Insert into files table
    INSERT INTO files (filename) VALUES (p_filename) RETURNING id INTO file_id;

    -- Get the length of the prompts array
    prompt_length := COALESCE(jsonb_array_length(p_data), 0);

    -- Loop through each object in the array
    FOR i IN 0 .. prompt_length - 1
    LOOP
        prompt_data := p_data->i;

        -- Insert into prompts table with truncated values
        INSERT INTO prompts (line_id, prompt_text, domain, task, meta_data, phase, status, file_id)
        VALUES (
            (i+1)::INTEGER,  -- Assuming you want to use (i+1) as the line_id
            prompt_data->>'prompt',
            (prompt_data->'meta'->>'prompt_domain')::TEXT,
            (prompt_data->'meta'->>'prompt_task')::TEXT,
            prompt_data->'meta',
            'create',
            'yts',
            file_id
        )
        RETURNING id INTO prompt_id;


        -- Get the length of the responses array
        responses_length := COALESCE(jsonb_array_length(prompt_data->'responses'), 0);

        -- Loop through responses and judgements for each object
        FOR j IN 0 .. responses_length - 1
        LOOP
            response_text := (prompt_data->'responses'->>j)::TEXT;

            -- Insert into responses table
            INSERT INTO responses (prompt_id, response_text) VALUES (prompt_id, response_text) RETURNING id INTO response_id;

            -- Get the length of the judgements array
            judgements_length := COALESCE(jsonb_array_length(prompt_data->'per_response_judgements'->j), 0);

              -- Loop through judgements for each response
            random_index := FLOOR(RANDOM() * judgements_length);

            FOR k IN 0 .. judgements_length - 1
            LOOP
                judgement := (prompt_data->'per_response_judgements'->j->((random_index + k) % judgements_length));

                IF rubric_count = 0 THEN
                    selected_rubric := judgement->>'rubric';
                END IF;

                -- Check if the rubric matches the selected rubric and if the count for this response exceeds 2
                IF rubric_count < 2 AND judgement->>'rubric' = selected_rubric THEN
                    -- Insert into judgements table
                    INSERT INTO judgements (response_id, reason, rubric, score)
                    VALUES (
                        response_id,
                        judgement->>'reason',
                        judgement->>'rubric',
                        (judgement->>'score')::INTEGER
                    );
                    rubric_count := rubric_count + 1;  -- Increment rubric count
                END IF;

                -- Exit the loop if we have inserted two judgements
                IF rubric_count = 2 THEN
                    EXIT;
                END IF;
            END LOOP; -- end of judgements loop
            rubric_count := 0;  -- Reset rubric count for the next response
        END LOOP; -- end of responses loop
    END LOOP; -- end of prompts loop

    RETURN 'Data from ' || p_filename || ' inserted successfully.';
END;
$$ LANGUAGE plpgsql;

"""

create_stored_procedure(sqlq)

create_stored_procedure_sql2 = """
    CREATE OR REPLACE FUNCTION update_response_scores(
        p_score_1 INTEGER,
        p_score_2 INTEGER,
        p_score_3 INTEGER,
        p_response_1_id INTEGER,
        p_response_2_id INTEGER,
        p_response_3_id INTEGER
    )
    RETURNS VOID AS $$
    DECLARE
        placeholder_score INTEGER := -1;
    BEGIN
        -- Insert or update labelled response for p_response_1_id
        IF p_response_1_id IS NOT NULL THEN
            IF p_score_1 IS DISTINCT FROM 0 AND p_score_1 IS NOT NULL THEN
                INSERT INTO labelled_responses (response_id, score)
                VALUES (p_response_1_id, p_score_1)
                ON CONFLICT (response_id) DO UPDATE SET score = EXCLUDED.score;
            ELSE
                INSERT INTO labelled_responses (response_id, score)
                VALUES (p_response_1_id, placeholder_score)
                ON CONFLICT (response_id) DO NOTHING;
            END IF;
        END IF;

        -- Insert or update labelled response for p_response_2_id
        IF p_response_2_id IS NOT NULL THEN
            IF p_score_2 IS DISTINCT FROM 0 AND p_score_2 IS NOT NULL THEN
                INSERT INTO labelled_responses (response_id, score)
                VALUES (p_response_2_id, p_score_2)
                ON CONFLICT (response_id) DO UPDATE SET score = EXCLUDED.score;
            ELSE
                INSERT INTO labelled_responses (response_id, score)
                VALUES (p_response_2_id, placeholder_score)
                ON CONFLICT (response_id) DO NOTHING;
            END IF;
        END IF;

        -- Insert or update labelled response for p_response_3_id
        IF p_response_3_id IS NOT NULL THEN
            IF p_score_3 IS DISTINCT FROM 0 AND p_score_3 IS NOT NULL THEN
                INSERT INTO labelled_responses (response_id, score)
                VALUES (p_response_3_id, p_score_3)
                ON CONFLICT (response_id) DO UPDATE SET score = EXCLUDED.score;
            ELSE
                INSERT INTO labelled_responses (response_id, score)
                VALUES (p_response_3_id, placeholder_score)
                ON CONFLICT (response_id) DO NOTHING;
            END IF;
        END IF;

        -- Check if any score is -1
        IF p_score_1 = -1 OR p_score_2 = -1 OR p_score_3 = -1 THEN
            -- Mark prompt phase as 'review' and status as 'yts'
            UPDATE prompts
            SET phase = 'review', status = 'yts'
            WHERE id = (SELECT prompt_id FROM responses WHERE id = p_response_1_id);
        ELSE
            -- Mark prompt status as 'wip' if any score is between 1 to 5
            UPDATE prompts
            SET status = 'wip'
            WHERE id = (SELECT prompt_id FROM responses WHERE id = p_response_1_id);
        END IF;
    END;
    $$ LANGUAGE plpgsql;

"""

create_stored_procedure(create_stored_procedure_sql2)

create_stored_procedure_sql3 = """
    CREATE OR REPLACE FUNCTION update_judgements(id_1 INTEGER, id_2 INTEGER,
                                                score_1 INTEGER, score_2 INTEGER,
                                                reason_1 TEXT, reason_2 TEXT)
    RETURNS VOID AS $$
    BEGIN
        INSERT INTO labelled_judgements (judgement_id, score, reason)
        VALUES (id_1, score_1, reason_1)
        ON CONFLICT (judgement_id) DO UPDATE
        SET score = EXCLUDED.score, reason = EXCLUDED.reason;

        INSERT INTO labelled_judgements (judgement_id, score, reason)
        VALUES (id_2, score_2, reason_2)
        ON CONFLICT (judgement_id) DO UPDATE
        SET score = EXCLUDED.score, reason = EXCLUDED.reason;

    END;
    $$ LANGUAGE plpgsql;

"""

create_stored_procedure(create_stored_procedure_sql3)


create_stored_procedure_sql4 = """
CREATE OR REPLACE FUNCTION update_judgements_and_prompt(
    id_1 INTEGER, id_2 INTEGER,
    score_1 INTEGER, score_2 INTEGER,
    reason_1 TEXT, reason_2 TEXT,
    prompt_id INTEGER)
RETURNS VOID AS $$
BEGIN
    INSERT INTO labelled_judgements (judgement_id, score, reason)
    VALUES (id_1, score_1, reason_1)
    ON CONFLICT (judgement_id) DO UPDATE
    SET score = EXCLUDED.score, reason = EXCLUDED.reason;

    INSERT INTO labelled_judgements (judgement_id, score, reason)
    VALUES (id_2, score_2, reason_2)
    ON CONFLICT (judgement_id) DO UPDATE
    SET score = EXCLUDED.score, reason = EXCLUDED.reason;

    UPDATE prompts
    SET phase = 'review', status = 'yts'
    WHERE id = prompt_id;
END;
$$ LANGUAGE plpgsql;
"""

create_stored_procedure(create_stored_procedure_sql4)




from psycopg2.extras import RealDictCursor
from pprint import pprint

def load_question(username, user_task, filename):
    conn = get_db_connection()
    user_task = user_task.lower()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Call the stored procedure
        cur.execute("""
            SELECT * FROM initialize_response_scores(%s, %s, %s)
        """, (username.lower(), user_task.lower(), filename))

        row = cur.fetchone()  # Fetch only one row
        conn.commit()

        if row:
            return {
                "prompt_id": row['prompt_id'],
                "question": row["question"],
                "create_skip_reason": row["create_skip_reason"],
                "review_skip_reason": row["review_skip_reason"],
                "create_skip_cat": row["create_skip_cat"],
                "review_skip_cat": row["review_skip_cat"],
                "response_1_id": row["response_1_id"],
                "response_1": row["response_1"],
                "score_1": row["score_1"],
                "judgement_1_1_id": row["judgement_1_1_id"],
                "judgement_1_1_score": row["judgement_1_1_score"],
                "judgement_1_1_rubric": row["judgement_1_1_rubric"],
                "judgement_1_1_reason": row["judgement_1_1_reason"],
                "judgement_1_2_id": row["judgement_1_2_id"],
                "judgement_1_2_score": row["judgement_1_2_score"],
                "judgement_1_2_rubric": row["judgement_1_2_rubric"],
                "judgement_1_2_reason": row["judgement_1_2_reason"],
                "response_2_id": row["response_2_id"],
                "response_2": row["response_2"],
                "score_2": row["score_2"],
                "judgement_2_1_id": row["judgement_2_1_id"],
                "judgement_2_1_score": row["judgement_2_1_score"],
                "judgement_2_1_rubric": row["judgement_2_1_rubric"],
                "judgement_2_1_reason": row["judgement_2_1_reason"],
                "judgement_2_2_id": row["judgement_2_2_id"],
                "judgement_2_2_score": row["judgement_2_2_score"],
                "judgement_2_2_rubric": row["judgement_2_2_rubric"],
                "judgement_2_2_reason": row["judgement_2_2_reason"],
                "response_3_id": row["response_3_id"],
                "response_3": row["response_3"],
                "score_3": row["score_3"],
                "judgement_3_1_id": row["judgement_3_1_id"],
                "judgement_3_1_score": row["judgement_3_1_score"],
                "judgement_3_1_rubric": row["judgement_3_1_rubric"],
                "judgement_3_1_reason": row["judgement_3_1_reason"],
                "judgement_3_2_id": row["judgement_3_2_id"],
                "judgement_3_2_score": row["judgement_3_2_score"],
                "judgement_3_2_rubric": row["judgement_3_2_rubric"],
                "judgement_3_2_reason": row["judgement_3_2_reason"]
            }
        else:
            return None
    finally:
        cur.close()
        conn.close()


def load_scoring_quest(username, row):
    if row is None:
        gr.Info("There are no more Prompts for Labelling, Please select another file")
        return (gr.Tabs(selected=1), username.lower()) + (None,) * 47
    return (
        gr.Tabs(), username.lower(), row['prompt_id'], gr.Textbox(value=row["question"], autoscroll=False),  gr.Textbox(value=row["response_1"], autoscroll=False),gr.Textbox(value= row["response_2"], autoscroll=False), gr.Textbox(value=row["response_3"], autoscroll=False),
        row["response_1_id"], row["response_2_id"], row["response_3_id"], 0, 0, 0,
        row["judgement_1_1_id"], row["judgement_1_2_id"], row["judgement_1_1_score"], row["judgement_1_2_score"],
        gr.Textbox(value=row["judgement_1_1_reason"], autoscroll=False), gr.Textbox(value=row["judgement_1_2_reason"], autoscroll=False), gr.Textbox(value=row["judgement_1_1_rubric"], autoscroll=False),
        gr.Textbox(value=row["judgement_1_2_rubric"], autoscroll=False), row["judgement_2_1_id"], row["judgement_2_2_id"],
        row["judgement_2_1_score"], row["judgement_2_2_score"],gr.Textbox(value=row["judgement_2_1_reason"], autoscroll=False), gr.Textbox(value=row["judgement_2_2_reason"], autoscroll=False),
        gr.Textbox(value=row["judgement_2_1_rubric"], autoscroll=False), gr.Textbox(value=row["judgement_2_2_rubric"], autoscroll=False), row["judgement_3_1_id"],
        row["judgement_3_2_id"], row["judgement_3_1_score"], row["judgement_3_2_score"],
        gr.Textbox(value=row["judgement_3_1_reason"], autoscroll=False),  gr.Textbox(value=row["judgement_3_2_reason"], autoscroll=False), gr.Textbox(value=row["judgement_3_1_rubric"], autoscroll=False), gr.Textbox(value=row["judgement_3_2_rubric"], autoscroll=False)
        ,row['score_1'], row['score_2'], row['score_3'], row['create_skip_reason'], row['review_skip_reason'], row['create_skip_cat'], row['review_skip_cat']
        )


def update_response_scores(score_1, score_2, score_3, response_1_id, response_2_id, response_3_id):
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Call the stored procedure to update response scores and prompt phase/status
        cur.callproc("update_response_scores", (score_1, score_2, score_3, response_1_id, response_2_id, response_3_id))
        conn.commit()
    finally:
        cur.close()
        conn.close()

def get_judgement_data(judgement_id):

    try:
        # Establish a connection to the database
        conn = get_db_connection()
        cur = conn.cursor()

        # Define the query to fetch data for the given judgement_id
        query = sql.SQL("""
            SELECT reason, score
            FROM judgements
            WHERE id = %s
        """)

        # Execute the query
        cur.execute(query, (judgement_id,))
        result = cur.fetchone()

        # Close the cursor and connection
        cur.close()
        conn.close()

        # Check if the result is None or both fields are None
        if result is None or (result[0] is None and result[1] is None):
            return None
        else:
            return result

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def save_and_next_j1(curr_prompt, username, user_task, filename, id_1_j1, id_2_j1 ,id_1_j2, id_2_j2 ,id_1_j3, id_2_j3 , score_1_j1, score_2_j1, reason_1_j1, reason_2_j1):
    try:
        # Open a cursor to perform database operations
        conn = get_db_connection()
        cur = conn.cursor()

        cur.callproc("update_judgements", (id_1_j1, id_2_j1, score_1_j1, score_2_j1, reason_1_j1, reason_2_j1))
        # Commit the transaction
        conn.commit()

        # Close the cursor and connection
        cur.close()
        conn.close()
        curr_prompt["judgement_1_1_score"] = score_1_j1
        curr_prompt["judgement_1_1_reason"] = reason_1_j1
        curr_prompt["judgement_1_2_score"] = score_2_j1
        curr_prompt["judgement_1_2_reason"] = reason_2_j1


        if get_judgement_data(id_1_j2) or get_judgement_data(id_2_j2) :
            return gr.Tabs(selected=4), gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=True),gr.Tabs(visible=False), curr_prompt
        if get_judgement_data(id_1_j3) or get_judgement_data(id_2_j3) :
            return gr.Tabs(selected=5), gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=True), curr_prompt

        prompt_data = curr_prompt
        prompt_id = prompt_data['prompt_id']
        update_prompt_status_in_db(prompt_id, user_task.lower())
        q = load_question(username.lower(), user_task.lower(), filename)
        if q is None:
            return gr.Tabs(selected=1), gr.Tabs(visible=False), gr.Tabs(visible=True),gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=False), ''
        return gr.Tabs(selected=2), gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=True), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=False), q

    except Exception as e:
        print(f"Error updating judgements: {e}")


import psycopg2
import pandas as pd
from datetime import datetime

import pandas as pd
import psycopg2

def load_file_info_d_with_username(filenames, usernames):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        all_results = []

        cur.execute("SELECT * FROM get_release_info_username(%s, %s)", (filenames, usernames,))
        results = cur.fetchall()
        all_results.extend(results)


        cur.close()
        conn.close()

    except psycopg2.Error as e:
        print(f"Error connecting to PostgreSQL database: {e}")
        return pd.DataFrame({
            'ID': [],
            'JSON Filename': [],
            'User Name': [],
            'Task': [],
            'Status': [],
            'Start Datetime': [],
            'End Datetime': [],
            'Skip Category': [],
            'Reason for Skip': []
        })

    # Create DataFrame from results
    df = pd.DataFrame(all_results, columns=['prompt_id' ,'user_name','start_time','end_time','json_file_name','task','status','skip_cat','reason'])

    # Rename columns to match desired output format
    df.rename(columns={
        'prompt_id': 'ID',
        'json_file_name': 'JSON Filename',
        'user_name': 'User Name',
        'task': 'Task',
        'status': 'Status',
        'start_time': 'Start Datetime',
        'end_time': 'End Datetime',
        'skip_cat': 'Skip Category',
        'reason': 'Reason for Skip'
    }, inplace=True)
    choices = df[df['Status'] == 'wip']['ID'].unique().tolist()
    if choices == []:
        gr.Warning('No Prompts in WIP for selected combination !')
    return df, gr.Dropdown(choices=choices, multiselect=True, interactive=True, label='ID')

def initialize_file_info_d():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT filename from files;")
    filenames = cur.fetchall()
    cur.execute("SELECT * FROM get_release_info(%s)", (filenames,))
    results = cur.fetchall()
    cur.close()
    conn.close()
      # Create DataFrame from results
    df = pd.DataFrame(results, columns=['prompt_id' ,'user_name','start_time','end_time','json_file_name','task','status','skip_cat','reason'])

    # Rename columns to match desired output format
    df.rename(columns={
        'prompt_id': 'ID',
        'json_file_name': 'JSON Filename',
        'user_name': 'User Name',
        'task': 'Task',
        'status': 'Status',
        'start_time': 'Start Datetime',
        'end_time': 'End Datetime',
        'skip_cat': 'Skip Category',
        'reason': 'Reason for Skip'
    }, inplace=True)

    return df

def load_file_info_d(filenames):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        all_results = []

        cur.execute("SELECT * FROM get_release_info(%s)", (filenames,))
        results = cur.fetchall()
        all_results.extend(results)


        cur.close()
        conn.close()

    except psycopg2.Error as e:
        print(f"Error connecting to PostgreSQL database: {e}")
        return pd.DataFrame({
            'ID': [],
            'JSON Filename': [],
            'User Name': [],
            'Task': [],
            'Status': [],
            'Start Datetime': [],
            'End Datetime': [],
            'Skip Category': [],
            'Reason for Skip': []
        })

    # Create DataFrame from results
    df = pd.DataFrame(all_results, columns=['prompt_id' ,'user_name','start_time','end_time','json_file_name','task','status','skip_cat','reason'])

    # Rename columns to match desired output format
    df.rename(columns={
        'prompt_id': 'ID',
        'json_file_name': 'JSON Filename',
        'user_name': 'User Name',
        'task': 'Task',
        'status': 'Status',
        'start_time': 'Start Datetime',
        'end_time': 'End Datetime',
        'skip_cat': 'Skip Category',
        'reason': 'Reason for Skip'
    }, inplace=True)

    return df, get_usernames_for_info_d(filenames, df)

def get_files_for_file_info_d():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT filename from files;")
    filenames = cur.fetchall()
    cur.close()
    conn.close()
    return gr.Dropdown(label='Filename', choices=[filename[0] for filename in filenames], multiselect=True, interactive=True)


def skip_and_next_j1(skip_reason, username, user_task, filename ,curr_prompt,id_1_j1, id_2_j1 ,id_1_j2, id_2_j2 ,id_1_j3, id_2_j3, score_1_j1, score_2_j1, reason_1_j1, reason_2_j1, skip_cat):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Call the combined stored procedure

        cur.callproc("update_judgements_and_prompt", (id_1_j1, id_2_j1, score_1_j1, score_2_j1, reason_1_j1, reason_2_j1, curr_prompt['prompt_id']))
        cur.execute(
            f"UPDATE prompts SET {user_task.lower()}_skip_reason = %s , {user_task.lower()}_skip_cat = %s , phase = 'review', status = '{ 'yts' if user_task.lower() == 'create' else 'skip'}' WHERE id = %s",
            (skip_reason, skip_cat, curr_prompt['prompt_id'])
        )

        conn.commit()
        cur.close()
        conn.close()
        curr_prompt["judgement_1_1_score"] = score_1_j1
        curr_prompt["judgement_1_1_reason"] = reason_1_j1
        curr_prompt["judgement_1_2_score"] = score_2_j1
        curr_prompt["judgement_1_2_reason"] = reason_2_j1
        curr_prompt[f"{user_task.lower()}_skip_reason"] = skip_reason
        curr_prompt[f"{user_task.lower()}_skip_cat"] = skip_cat

        prompt_data = curr_prompt
        prompt_id = prompt_data['prompt_id']
        update_prompt_status_in_db(prompt_id, user_task.lower())
        q = load_question(username.lower(), user_task.lower(), filename)
        if q is None:
            return gr.Tabs(selected=1), gr.Tabs(visible=False), gr.Tabs(visible=True), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), q
        return gr.Tabs(selected=2), gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=True), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=False), q

    except Exception as e:
        print(f"Error in skip_and_next_j1: {e}")

def save_and_next_j2(curr_prompt, username, user_task, filename, id_1_j2, id_2_j2 ,id_1_j3, id_2_j3 ,score_1_j2, score_2_j2, reason_1_j2, reason_2_j2):
    try:
        # Open a cursor to perform database operations
        conn = get_db_connection()
        cur = conn.cursor()

        cur.callproc("update_judgements", (id_1_j2, id_2_j2, score_1_j2, score_2_j2, reason_1_j2, reason_2_j2))


        # Commit the transaction
        conn.commit()

        # Close the cursor and connection
        cur.close()
        conn.close()
        curr_prompt["judgement_2_1_score"] = score_1_j2
        curr_prompt["judgement_2_1_reason"] = reason_1_j2
        curr_prompt["judgement_2_2_score"] = score_2_j2
        curr_prompt["judgement_2_2_reason"] = reason_2_j2

        if get_judgement_data(id_1_j3) or get_judgement_data(id_2_j3) :
            return gr.Tabs(selected=5), gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=True), curr_prompt

        prompt_data = curr_prompt
        prompt_id = prompt_data['prompt_id']
        update_prompt_status_in_db(prompt_id, user_task.lower())
        q = load_question(username.lower(), user_task.lower(), filename)
        if q is None:
            return gr.Tabs(selected=1), gr.Tabs(visible=False), gr.Tabs(visible=True), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), q
        return gr.Tabs(selected=2), gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=True), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=False), q

    except Exception as e:
        print(f"Error updating judgements: {e}")



def skip_and_next_j2(skip_reason , username, user_task, filename, curr_prompt,id_1_j2, id_2_j2 ,id_1_j3, id_2_j3, score_1_j2, score_2_j2, reason_1_j2, reason_2_j2, skip_cat):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Call the combined stored procedure

        cur.callproc("update_judgements_and_prompt", (id_1_j2, id_2_j2, score_1_j2, score_2_j2, reason_1_j2, reason_2_j2, curr_prompt['prompt_id']))
        cur.execute(
            f"UPDATE prompts SET {user_task.lower()}_skip_reason = %s , {user_task.lower()}_skip_cat = %s , phase = 'review', status = '{ 'yts' if user_task.lower() == 'create' else 'skip'}' WHERE id = %s",
            (skip_reason, skip_cat, curr_prompt['prompt_id'])
        )
        conn.commit()
        cur.close()
        conn.close()
        curr_prompt["judgement_2_1_score"] = score_1_j2
        curr_prompt["judgement_2_1_reason"] = reason_1_j2
        curr_prompt["judgement_2_2_score"] = score_2_j2
        curr_prompt["judgement_2_2_reason"] = reason_2_j2
        curr_prompt[f"{user_task.lower()}_skip_reason"] = skip_reason
        curr_prompt[f"{user_task.lower()}_skip_cat"] = skip_cat
        prompt_data = curr_prompt
        prompt_id = prompt_data['prompt_id']
        update_prompt_status_in_db(prompt_id, user_task.lower())
        q = load_question(username.lower(), user_task.lower(), filename)
        if q is None:
            return gr.Tabs(selected=1), gr.Tabs(visible=False), gr.Tabs(visible=True), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), q
        return  gr.Tabs(selected=2), gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=True), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=False), q


    except Exception as e:
        print(f"Error in skip_and_next_j1: {e}")

def save_and_next_j3(username, user_task, filename, curr_prompt, id_1_j3, id_2_j3 ,score_1_j3, score_2_j3, reason_1_j3, reason_2_j3):
    try:
        # Open a cursor to perform database operations
        conn = get_db_connection()
        cur = conn.cursor()

        cur.callproc("update_judgements", (id_1_j3, id_2_j3, score_1_j3, score_2_j3, reason_1_j3, reason_2_j3))
        # Commit the transaction
        conn.commit()

        # Close the cursor and connection
        cur.close()
        conn.close()
        curr_prompt["judgement_3_1_score"] = score_1_j3
        curr_prompt["judgement_3_1_reason"] = reason_1_j3
        curr_prompt["judgement_3_2_score"] = score_2_j3
        curr_prompt["judgement_3_2_reason"] = reason_2_j3

        prompt_data = curr_prompt
        prompt_id = prompt_data['prompt_id']
        update_prompt_status_in_db(prompt_id, user_task.lower())
        q = load_question(username.lower(), user_task.lower(), filename)
        if q is None:
            return gr.Tabs(selected=1), gr.Tabs(visible=False), gr.Tabs(visible=True), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), q, curr_prompt
        return  gr.Tabs(selected=2), gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=True), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=False), q, curr_prompt

    except Exception as e:
        print(f"Error updating judgements: {e}")



def skip_and_next_j3(skip_reason, username, user_task, filename, curr_prompt, id_1_j3, id_2_j3, score_1_j3, score_2_j3, reason_1_j3, reason_2_j3, skip_cat):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Call the combined stored procedure

        cur.callproc("update_judgements_and_prompt", (id_1_j3, id_2_j3, score_1_j3, score_2_j3, reason_1_j3, reason_2_j3, curr_prompt['prompt_id']))
        cur.execute(
            f"UPDATE prompts SET {user_task.lower()}_skip_reason = %s , {user_task.lower()}_skip_cat = %s , phase = 'review', status = '{ 'yts' if user_task.lower() == 'create' else 'skip'}' WHERE id = %s",
            (skip_reason, skip_cat, curr_prompt['prompt_id'])
        )
        conn.commit()
        cur.close()
        conn.close()
        curr_prompt["judgement_3_1_score"] = score_1_j3
        curr_prompt["judgement_3_1_reason"] = reason_1_j3
        curr_prompt["judgement_3_2_score"] = score_2_j3
        curr_prompt["judgement_3_2_reason"] = reason_2_j3
        curr_prompt[f"{user_task.lower()}_skip_reason"] = skip_reason
        curr_prompt[f"{user_task.lower()}_skip_cat"] = skip_cat

        prompt_data = curr_prompt
        prompt_id = prompt_data['prompt_id']
        update_prompt_status_in_db(prompt_id, user_task.lower())
        q = load_question(username.lower(), user_task.lower(), filename)
        if q is None:
            return gr.Tabs(selected=1), gr.Tabs(visible=False), gr.Tabs(visible=True), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), q, curr_prompt

        return gr.Tabs(selected=2), gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=True), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=False), q, curr_prompt



    except Exception as e:
        print(f"Error in skip_and_next_j1: {e}")




# load_question("admin", "create", 'New Text Document.jsonl')

def get_prompt_counts(filename):
    conn = get_db_connection()
    cur = conn.cursor()

    # SQL query to count the total number of prompts and the number of "Done" prompts for the given file
    cur.execute("""
      SELECT
          (SELECT COUNT(*) FROM prompts JOIN files ON prompts.file_id = files.id WHERE files.filename = %s) AS total_count,
          (SELECT COUNT(*) FROM prompts JOIN files ON prompts.file_id = files.id WHERE files.filename = %s AND prompts.status = 'done' AND prompts.phase = 'create') AS create_done,
          (SELECT COUNT(*) FROM prompts JOIN files ON prompts.file_id = files.id WHERE files.filename = %s AND prompts.status = 'yts' AND prompts.phase = 'review') AS create_skipped,
          (SELECT COUNT(*) FROM prompts JOIN files ON prompts.file_id = files.id WHERE files.filename = %s AND prompts.status = 'wip' AND prompts.phase = 'create') AS create_wip,
          (SELECT COUNT(*) FROM prompts JOIN files ON prompts.file_id = files.id WHERE files.filename = %s AND prompts.status = 'yts' AND prompts.phase = 'create') AS create_yts,
          (SELECT COUNT(*) FROM prompts JOIN files ON prompts.file_id = files.id WHERE files.filename = %s AND prompts.status = 'done' AND prompts.phase = 'review') AS review_done,
          (SELECT COUNT(*) FROM prompts JOIN files ON prompts.file_id = files.id WHERE files.filename = %s AND prompts.status = 'skip' AND prompts.phase = 'review') AS review_skipped,
          (SELECT COUNT(*) FROM prompts JOIN files ON prompts.file_id = files.id WHERE files.filename = %s AND prompts.status = 'wip' AND prompts.phase = 'review') AS review_wip,
          (SELECT COUNT(*) FROM prompts JOIN files ON prompts.file_id = files.id WHERE files.filename = %s AND prompts.status = 'yts' AND prompts.phase = 'review') AS review_yts
    """, (filename, filename, filename, filename, filename, filename, filename, filename, filename))
    total_count, create_done, create_skipped, create_WIP, create_YTS, review_done, review_skipped, review_WIP, review_YTS = cur.fetchone()

    cur.close()
    conn.close()

    return total_count, create_done, create_skipped, create_WIP, create_YTS, review_done, review_skipped, review_WIP, review_YTS

import psycopg2
import json
import os

import json
import psycopg2


def fetch_filenames():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT f.filename
        FROM files f
        LEFT JOIN prompts p ON f.id = p.file_id
        GROUP BY f.filename
        HAVING COUNT(*) = SUM(CASE
                                WHEN p.phase IN ('create', 'review')
                                    AND (p.status = 'done' OR (p.status = 'skip' AND p.phase = 'review'))
                                THEN 1
                                ELSE 0
                              END);

    """)
    filenames = cur.fetchall()
    cur.close()
    conn.close()
    # if not filenames:
    #     gr.Warning('No File Labelled till now!')
    return gr.Dropdown(choices = [filename[0] for filename in filenames], multiselect=True, label='Files to Export')


def fetch_expected_fields(cur, filename):
    cur.execute("""
        SELECT COUNT(*)
        FROM prompts
        WHERE file_id = (SELECT id FROM files WHERE filename = %s);
    """, (filename,))
    return cur.fetchone()[0]

def fetch_data(cur, filename):
    cur.execute("""
        SELECT
            p.line_id AS line_id,
            p.prompt_text AS question,
            p.create_skip_reason AS create_skip_reason,
            p.review_skip_reason AS review_skip_reason,
            p.create_skip_cat AS create_skip_cat,
            p.review_skip_cat AS review_skip_cat,
            r.id AS response_id,
            r.response_text AS response,
            lr.score response_score,
            j.id AS judgement_id,
            j.rubric AS judgement_rubric,
            j.score AS judger_1_score,
            j.reason AS judger_1_response,
            lj.score AS judger_1_updated_score,
            lj.reason AS judger_1_updated_response,
            j2.id AS judgement_id_2,
            j2.rubric AS judgement_rubric_2,
            j2.score AS judger_2_score,
            j2.reason AS judger_2_response,
            lj2.score AS judger_2_updated_score,
            lj2.reason AS judger_2_updated_response
        FROM
            prompts p
        LEFT JOIN
            responses r ON p.id = r.prompt_id
        LEFT JOIN
            labelled_responses lr ON r.id = lr.response_id
        LEFT JOIN
            reviewed_responses rr ON r.id = rr.response_id
        LEFT JOIN
            judgements j ON r.id = j.response_id
        LEFT JOIN
            labelled_judgements lj ON j.id = lj.judgement_id
        LEFT JOIN
            reviewed_judgements rj ON j.id = rj.judgement_id
        LEFT JOIN
            judgements j2 ON r.id = j2.response_id AND j2.id != j.id
        LEFT JOIN
            labelled_judgements lj2 ON j2.id = lj2.judgement_id
        LEFT JOIN
            reviewed_judgements rj2 ON j2.id = rj2.judgement_id
        LEFT JOIN
            files f ON p.file_id = f.id
        WHERE
            p.phase IN ('create', 'review')
        AND
            (p.status = 'done' OR (p.status = 'skip' AND p.phase = 'review'))
        AND
            f.filename = %s
        ORDER BY
            p.id, r.id, j.id;
    """, (filename,))
    return cur.fetchall()

def organize_data(rows, expected_fields):
    data = {}
    for row in rows:
        (
            line_id, question, create_skip_reason, review_skip_reason,
            create_skip_cat, review_skip_cat, response_id, response_text,
            response_score, judgement_id, judgement_rubric, judger_1_score,
            judger_1_response, judger_1_updated_score, judger_1_updated_response,
            judgement_id_2, judgement_rubric_2, judger_2_score, judger_2_response,
            judger_2_updated_score, judger_2_updated_response
        ) = row

        if line_id not in data:
            data[line_id] = {
                "line_id": line_id,
                "question": question,
                "responses": [],
                "scores": [],
                "is_skip": bool(review_skip_cat),
                "is_skip_reason": f"{review_skip_cat or ''}: {review_skip_reason or ''}".strip(", ") if review_skip_cat else "",
                "judger_responses": []
            }

        judgement_entry = {
            "question": question,
            "response": response_text,
            "rubric": judgement_rubric,
            "judger_1_score": judger_1_score,
            "judger_1_response": judger_1_response,
            "judger_1_updated_score": judger_1_updated_score,
            "judger_1_updated_response": judger_1_updated_response,
            "judger_2_score": judger_2_score,
            "judger_2_response": judger_2_response,
            "judger_2_updated_score": judger_2_updated_score,
            "judger_2_updated_response": judger_2_updated_response,
            "is_skip": bool(review_skip_cat),
            "is_skip_reason": f"{review_skip_cat or ''}: {review_skip_reason or ''}".strip(", ") if review_skip_cat else "",
        }
        x = True

        for jud in data[line_id]["judger_responses"]:
            if jud['response'] == judgement_entry['response']:
                x = False
                break
        if x:
            data[line_id]["judger_responses"].append(judgement_entry)

        if response_text not in data[line_id]["responses"]:
            data[line_id]["responses"].append(response_text)
            data[line_id]["scores"].append(response_score)

    return data if len(data.keys()) == expected_fields else None

def write_to_jsonl(filename, data):
    with open(f"{filename}", "w") as f:
        for entry in data.values():

            json.dump(entry, f)
            f.write('\n')

def export_to_jsonl(filenames):
    try:
        if filenames is None:
            gr.Warning('No File Selected')
        conn = get_db_connection()
        cur = conn.cursor()

        # filenames = fetch_filenames(cur)

        for filename in filenames:
            expected_fields = fetch_expected_fields(cur, filename)
            rows = fetch_data(cur, filename)
            data = organize_data(rows, expected_fields)

            if data:
                write_to_jsonl(filename, data)
            else:
                gr.Warning(f'Skipping {filename} due to incomplete labelling!')
                print(f"Expected {expected_fields} fields, but got {len(data.keys())} for {filename}")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        if conn:
            cur.close()
            conn.close()
            file_paths = [os.path.abspath(filename) for filename in filenames]
            return file_paths

# Usage example


def update_prompt_status_in_db(prompt_id, user_task):

    try:
        # Establish a connection to the database
        conn = get_db_connection()
        cur = conn.cursor()
        # Call the stored procedure
        cur.execute("SELECT update_prompt_status(%s, %s)", (prompt_id, user_task.lower(),))
        conn.commit()

        # Close the cursor and connection
        cur.close()
        conn.close()

        return "Prompt status updated successfully."
    except Exception as e:
        print(f"An error occurred: {e}")
        return "An error occurred while updating the prompt status."



# prompt_id = 1
# user_task = 'create'
# print(update_prompt_status_in_db(1, user_task))

# get_prompt_counts("suspicious_samples_run3 2.jsonl")

# show_tables()

import gradio as gr
import json

# Save scores and reasons for the current question and move to the next question
def save_and_next(n_clicks, curr_prompt, id_1_j1, id_2_j1 ,id_1_j2, id_2_j2 ,id_1_j3, id_2_j3 , username, user_task,filename, score_1, score_2, score_3, response_1_id, response_2_id, response_3_id):

    update_response_scores(score_1, score_2, score_3, response_1_id, response_2_id, response_3_id)
    if n_clicks != 0:
        n_clicks -= 1
    curr_prompt["score_1"] = score_1
    curr_prompt["score_2"] = score_2
    curr_prompt["score_3"] = score_3
    if not(score_1 and score_2 and score_3):
        gr.Warning('Please fill scores for all fields')
    if get_judgement_data(id_1_j1) or get_judgement_data(id_2_j1) :
        return gr.Tabs(selected=3), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=True), gr.Tabs(visible=False), gr.Tabs(visible=False) ,curr_prompt, n_clicks
    if get_judgement_data(id_1_j2) or get_judgement_data(id_2_j2) :
        return gr.Tabs(selected=4), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=True), gr.Tabs(visible=False), curr_prompt, n_clicks
    if get_judgement_data(id_1_j3) or get_judgement_data(id_2_j3) :
        return gr.Tabs(selected=5), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=True),curr_prompt, n_clicks

    prompt_data = curr_prompt
    prompt_id = prompt_data['prompt_id']
    update_prompt_status_in_db(prompt_id, user_task.lower())
    q = load_question(username.lower(), user_task.lower(), filename)
    if q is None:
        return gr.Tabs(selected=1), gr.Tabs(visible=False), gr.Tabs(visible=True), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), q, n_clicks
    return gr.Tabs(selected=2), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=True), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), q, n_clicks



# Skip the current question and move to the next question
def skip_and_next(n_clicks, skip_reason, curr_prompt, id_1_j1, id_2_j1 ,id_1_j2, id_2_j2 ,id_1_j3, id_2_j3 ,username, user_task,filename, response_1_id, response_2_id, response_3_id, skip_cat):

    update_response_scores(-1, -1, -1, response_1_id, response_2_id, response_3_id)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        f"UPDATE prompts SET {user_task.lower()}_skip_reason = %s , {user_task.lower()}_skip_cat = %s , phase = 'review', status = '{ 'yts' if user_task.lower() == 'create' else 'skip'}' WHERE id = %s",
        (skip_reason, skip_cat, curr_prompt['prompt_id'])
    )
    conn.commit()
    cur.close()
    conn.close()
    curr_prompt["score_1"] = 0
    curr_prompt["score_2"] = 0
    curr_prompt["score_3"] = 0
    curr_prompt[f"{user_task.lower()}_skip_reason"] = skip_reason
    curr_prompt[f"{user_task.lower()}_skip_cat"] = skip_cat
    if n_clicks != 0:
        n_clicks -= 1

    prompt_data = curr_prompt
    prompt_id = prompt_data['prompt_id']
    update_prompt_status_in_db(prompt_id, user_task.lower())
    q = load_question(username.lower(), user_task.lower(), filename)
    if q is None:
        return gr.Tabs(selected=1), gr.Tabs(visible=False), gr.Tabs(visible=True), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), q, n_clicks
    return gr.Tabs(selected=2), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=True), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), q, n_clicks


# Save scores and reasons for the current question and submit
def submit_scores(username, user_task, score_1, score_2, score_3, response_1_id, response_2_id, response_3_id, prompt_id):
    update_response_scores(score_1, score_2, score_3,  response_1_id, response_2_id, response_3_id)
    if not(score_1 and score_2 and score_3):
        return gr.Markdown("Thank You!, You can see your responses in Results Tab"), gr.Markdown("PLEASE FILL CORRECTLY"),  gr.JSON("response_scores")


import gradio as gr
import psycopg2
from psycopg2 import sql
import datetime

pro_report_func = """
CREATE OR REPLACE FUNCTION get_pro_report(
    from_date TIMESTAMP,
    to_date TIMESTAMP
)
RETURNS TABLE (
    user_name VARCHAR(50),
    completed_date TIMESTAMP,
    status VARCHAR(5),
    json_file_name VARCHAR(255),
    task VARCHAR(10),
    rating_average NUMERIC,
    total_record_skipped BIGINT,
    total_record_completed BIGINT,
    duration_min NUMERIC
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Query for create phase
    RETURN QUERY
    SELECT
        p.create_user,
        p.create_end_time,
        p.status::VARCHAR(5),
        f.filename,
        'create'::VARCHAR(10),
        COALESCE(AVG(lr.score) + AVG(lj.score), 0.0)::NUMERIC, -- Ensure rating_average is NUMERIC
        SUM(CASE WHEN p.create_skip_cat IS NOT NULL THEN 1 ELSE 0 END)::BIGINT,
        COUNT(p.id)::BIGINT, -- Ensure total_record_completed is BIGINT
        ROUND(EXTRACT(EPOCH FROM (p.create_end_time - p.create_start_time)) / 60.0, 2)
    FROM prompts p
    JOIN files f ON p.file_id = f.id
    LEFT JOIN labelled_responses lr ON p.id = lr.response_id
    LEFT JOIN labelled_judgements lj ON lr.response_id = lj.judgement_id
    WHERE p.phase = 'create'
        AND p.create_user IS NOT NULL
        AND p.create_user <> ''
        AND p.create_start_time >= from_date
        AND p.create_end_time <= to_date
    GROUP BY p.create_user, p.create_end_time, p.status, f.filename, p.create_start_time;

    -- Query for review phase
    RETURN QUERY
    SELECT
        p.review_user,
        p.review_end_time,
        p.status::VARCHAR(5),
        f.filename,
        'review'::VARCHAR(10),
        COALESCE(AVG(lr.score) + AVG(lj.score), 0.0)::NUMERIC, -- Ensure rating_average is NUMERIC
        SUM(CASE WHEN p.review_skip_cat IS NOT NULL THEN 1 ELSE 0 END)::BIGINT,
        COUNT(p.id)::BIGINT, -- Ensure total_record_completed is BIGINT
        ROUND(EXTRACT(EPOCH FROM (p.review_end_time - p.review_start_time)) / 60.0, 2)
    FROM prompts p
    JOIN files f ON p.file_id = f.id
    LEFT JOIN labelled_responses lr ON p.id = lr.response_id
    LEFT JOIN labelled_judgements lj ON lr.response_id = lj.judgement_id
    WHERE p.phase = 'review'
        AND p.review_user IS NOT NULL
        AND p.review_user <> ''
        AND p.review_start_time >= from_date
        AND p.review_end_time <= to_date
    GROUP BY p.review_user, p.review_end_time,p.status, f.filename, p.review_start_time;
END;
$$;


"""
initialize_pro_report_func = """
CREATE OR REPLACE FUNCTION initialize_pro_report()
RETURNS TABLE (
    user_name VARCHAR(50),
    completed_date TIMESTAMP,
    status VARCHAR(5),
    json_file_name VARCHAR(255),
    task VARCHAR(10),
    rating_average NUMERIC,
    total_record_skipped BIGINT,
    total_record_completed BIGINT,
    duration_min NUMERIC
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Query for create phase
    RETURN QUERY
    SELECT
        p.create_user,
        p.create_end_time,
        p.status::VARCHAR(5),
        f.filename,
        'create'::VARCHAR(10),
        COALESCE(AVG(lr.score) + AVG(lj.score), 0.0)::NUMERIC, -- Ensure rating_average is NUMERIC
        SUM(CASE WHEN p.create_skip_cat IS NOT NULL THEN 1 ELSE 0 END)::BIGINT,
        COUNT(p.id)::BIGINT, -- Ensure total_record_completed is BIGINT
        ROUND(EXTRACT(EPOCH FROM (p.create_end_time - p.create_start_time)) / 60.0, 2)
    FROM prompts p
    JOIN files f ON p.file_id = f.id
    LEFT JOIN labelled_responses lr ON p.id = lr.response_id
    LEFT JOIN labelled_judgements lj ON lr.response_id = lj.judgement_id
    WHERE p.phase = 'create'
        AND p.create_user IS NOT NULL
        AND p.create_user <> ''
    GROUP BY p.create_user, p.create_end_time,p.status, f.filename, p.create_start_time;

    -- Query for review phase
    RETURN QUERY
    SELECT
        p.review_user,
        p.review_end_time,
        p.status::VARCHAR(5),
        f.filename,
        'review'::VARCHAR(10),
        COALESCE(AVG(lr.score) + AVG(lj.score), 0.0)::NUMERIC, -- Ensure rating_average is NUMERIC
        SUM(CASE WHEN p.review_skip_cat IS NOT NULL THEN 1 ELSE 0 END)::BIGINT,
        COUNT(p.id)::BIGINT, -- Ensure total_record_completed is BIGINT
        ROUND(EXTRACT(EPOCH FROM (p.review_end_time - p.review_start_time)) / 60.0, 2)
    FROM prompts p
    JOIN files f ON p.file_id = f.id
    LEFT JOIN labelled_responses lr ON p.id = lr.response_id
    LEFT JOIN labelled_judgements lj ON lr.response_id = lj.judgement_id
    WHERE p.phase = 'review'
        AND p.review_user IS NOT NULL
        AND p.review_user <> ''
    GROUP BY p.review_user, p.review_end_time,p.status, f.filename, p.review_start_time;
END;
$$;


"""
create_stored_procedure(pro_report_func)

create_stored_procedure(initialize_pro_report_func)

dashboard_proc = """
CREATE OR REPLACE FUNCTION get_dashboard(
    from_date TIMESTAMP,
    to_date TIMESTAMP
)
RETURNS TABLE (
    v_json_file_name TEXT,
    v_total_records BIGINT,
    v_completed BIGINT,
    v_skipped BIGINT,
    v_create_wip BIGINT,
    v_create_yts BIGINT,
    v_review_yts BIGINT,
    v_review_wip BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH temp_dashboard AS (
        SELECT
            f.filename AS "JSON File Name",
            COUNT(p.id) AS "Total Records",
            SUM(CASE WHEN p.status = 'done' THEN 1 ELSE 0 END) AS "Completed",
            SUM(CASE WHEN p.status = 'skip' THEN 1 ELSE 0 END) AS "Skipped",
            SUM(CASE WHEN p.status = 'wip' AND p.phase = 'create' THEN 1 ELSE 0 END) AS "Create WIP",
            SUM(CASE WHEN p.status = 'yts' AND p.phase = 'create' THEN 1 ELSE 0 END) AS "Create YTS",
            SUM(CASE WHEN p.status = 'yts' AND p.phase = 'review' THEN 1 ELSE 0 END) AS "Review YTS",
            SUM(CASE WHEN p.status = 'wip' AND p.phase = 'review' THEN 1 ELSE 0 END) AS "Review WIP"
        FROM prompts p
        JOIN files f ON p.file_id = f.id
        WHERE p.create_start_time >= from_date AND p.create_end_time <= to_date
           OR p.review_start_time >= from_date AND p.review_end_time <= to_date
        GROUP BY f.filename
    )
    SELECT
        "JSON File Name"::TEXT,
        "Total Records"::BIGINT,
        "Completed"::BIGINT,
        "Skipped"::BIGINT,
        "Create WIP"::BIGINT,
        "Create YTS"::BIGINT,
        "Review YTS"::BIGINT,
        "Review WIP"::BIGINT
    FROM temp_dashboard
    ORDER BY "JSON File Name";
END;
$$;

"""

initialize_dashboard = """
CREATE OR REPLACE FUNCTION initialize_dashboard()
RETURNS TABLE (
    v_json_file_name TEXT,
    v_total_records BIGINT,
    v_completed BIGINT,
    v_skipped BIGINT,
    v_create_wip BIGINT,
    v_create_yts BIGINT,
    v_review_yts BIGINT,
    v_review_wip BIGINT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH temp_dashboard AS (
        SELECT
            f.filename AS "JSON File Name",
            COUNT(p.id) AS "Total Records",
            SUM(CASE WHEN p.status = 'done' THEN 1 ELSE 0 END) AS "Completed",
            SUM(CASE WHEN p.status = 'skip' THEN 1 ELSE 0 END) AS "Skipped",
            SUM(CASE WHEN p.status = 'wip' AND p.phase = 'create' THEN 1 ELSE 0 END) AS "Create WIP",
            SUM(CASE WHEN p.status = 'yts' AND p.phase = 'create' THEN 1 ELSE 0 END) AS "Create YTS",
            SUM(CASE WHEN p.status = 'yts' AND p.phase = 'review' THEN 1 ELSE 0 END) AS "Review YTS",
            SUM(CASE WHEN p.status = 'wip' AND p.phase = 'review' THEN 1 ELSE 0 END) AS "Review WIP"
        FROM prompts p
        JOIN files f ON p.file_id = f.id
        GROUP BY f.filename
    )
    SELECT
        "JSON File Name"::TEXT,
        "Total Records"::BIGINT,
        "Completed"::BIGINT,
        "Skipped"::BIGINT,
        "Create WIP"::BIGINT,
        "Create YTS"::BIGINT,
        "Review YTS"::BIGINT,
        "Review WIP"::BIGINT
    FROM temp_dashboard
    ORDER BY "JSON File Name";

    -- Optionally, you can drop the temporary table here, but it's not necessary
    -- DROP TABLE IF EXISTS temp_dashboard;
END;
$$;

"""

create_stored_procedure(dashboard_proc)
create_stored_procedure(initialize_dashboard)
import psycopg2
import pandas as pd
from datetime import datetime

def get_dashboard(from_day, from_month, from_year, to_day, to_month, to_year):
    # Define the date range
    from_date = f'{from_year}-{from_month}-{from_day}'
    to_date = f'{to_year}-{to_month}-{to_day}'

    if from_date > to_date:
        gr.Warning('Invalid Range Selected!')

    # Connect to the PostgreSQL database
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Call the stored procedure
        cur.execute('SELECT * FROM get_dashboard(%s::TIMESTAMP, %s::TIMESTAMP)', (from_date, to_date))

        # Fetch all results
        columns = ['JSON File Name', 'Total Records', 'Completed','Skipped', 'Create WIP', 'Create YTS', 'Review YTS', 'Review WIP']
        result = cur.fetchall()

        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error connecting to PostgreSQL database: {e}")
        return pd.DataFrame({
             'JSON File Name': [],
             'Total Records': [],
             'Completed': [],
             'Skipped': [],
             'Create WIP': [],
             'Create YTS': [],
             'Review YTS': [],
             'Review WIP': []
             })

    # Create the DataFrame
    if result == []:
        gr.Warning('No Data Found')
    df = pd.DataFrame(result, columns=columns)

    return df


# Function to execute the stored procedure and fetch results
def initialize_dashboard():
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Call the stored procedure
        cur.execute('SELECT * FROM initialize_dashboard()')
        result = cur.fetchall()


        # Close cursor and connection
        cur.close()
        conn.close()

        # If result is not empty, convert to DataFrame
        if result:
            columns = ['JSON File Name', 'Total Records', 'Completed','Skipped', 'Create WIP', 'Create YTS', 'Review YTS', 'Review WIP']
            df = pd.DataFrame(result, columns=columns)
            return df
        else:
            gr.Warning('No Data Found')
            return pd.DataFrame({
                'JSON File Name': [],
                'Total Records': [],
                'Completed': [],
                'Skipped': [],
                'Create WIP': [],
                'Create YTS': [],
                'Review YTS': [],
                'Review WIP': [],
                'Action': []
            })

    except psycopg2.Error as e:
        print(f"Error executing stored procedure: {e}")
        return None



# Function to verify user credentials
def verify_user(username, password):
    conn = get_db_connection()
    cur = conn.cursor()
    query = sql.SQL("SELECT username FROM users WHERE username = %s AND password = %s")
    cur.execute(query, (username.lower(), password))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result is not None

import psycopg2
from datetime import datetime
import pandas as pd


def login(username, password, user_task):
    if verify_user(username.lower(), password):
        return username.lower(), user_task
    gr.Warning("Please Enter Correct credentials!")

def get_files(username, user_task):
  if username != '':
    conn = get_db_connection()
    cur = conn.cursor()

  #   # Query to retrieve user role
  #   cur.execute("SELECT user_role FROM users WHERE username = %s", (username,))
  #   user_role = cur.fetchone()[0]
  #   print('user role is ' ,user_role)

    try:
        # Secure query using parameterized statements
        query = """
              SELECT DISTINCT f.filename
              FROM files f
              INNER JOIN prompts p ON f.id = p.file_id
              WHERE p.phase = %s AND p.status = 'yts'
              AND f.filename NOT IN (
                  SELECT filename FROM archived_files
              )
        """
        cur.execute(query, (user_task.lower(),))
        filenames = cur.fetchall()

        return [filename[0] for filename in filenames]
    finally:
        cur.close()
        conn.close()


css = """
.skip {background-color: #FFCCCB}
"""

with gr.Blocks(title='Boson - Task 1', css=css) as app:
    username = gr.State(value="")
    curr_username = gr.Textbox(username, visible=False)
    prompt = gr.State(value = {})
    p =  {
                "prompt_id": None,
                "question": None,
                "create_skip_reason": None,
                "review_skip_reason": None,
                "create_skip_cat": None,
                "review_skip_cat": None,
                "response_1_id": None,
                "response_1": None,
                "score_1": 0,
                "judgement_1_1_id": None,
                "judgement_1_1_score": None,
                "judgement_1_1_rubric": None,
                "judgement_1_1_reason": None,
                "judgement_1_2_id": None,
                "judgement_1_2_score": None,
                "judgement_1_2_rubric": None,
                "judgement_1_2_reason": None,
                "response_2_id": None,
                "response_2": None,
                "score_2": 0,
                "judgement_2_1_id": None,
                "judgement_2_1_score": None,
                "judgement_2_1_rubric": None,
                "judgement_2_1_reason": None,
                "judgement_2_2_id": None,
                "judgement_2_2_score": None,
                "judgement_2_2_rubric": None,
                "judgement_2_2_reason": None,
                "response_3_id": None,
                "response_3": None,
                "score_3": 0,
                "judgement_3_1_id": None,
                "judgement_3_1_score": None,
                "judgement_3_1_rubric": None,
                "judgement_3_1_reason": None,
                "judgement_3_2_id" : None,
                "judgement_3_2_score": None,
                "judgement_3_2_rubric": None,
                "judgement_3_2_reason": None
            }
    curr_prompt = gr.State(value=p)
    prompt_id = gr.Textbox('', visible=False)
    user_task = gr.State(value="")
    curr_user_task = gr.Textbox(username, visible=False)

    def update_user_info(username, task_name, filename):
        return f"""
        **User Information:** **Username:** {username.lower()}, **Task:** {task_name}, **Filename:** {filename}
        """

    def update_prompt_counts(curr_username, filename, user_task, curr_usertask):
        total_count, create_done, create_skipped, create_WIP, create_YTS, review_done, review_skipped, review_WIP, review_YTS = get_prompt_counts(filename)

        # Check for None and handle accordingly
        user_task_lower = user_task.lower() if user_task else ''
        curr_usertask_lower = curr_usertask.lower() if curr_usertask else ''
        task = user_task_lower if user_task_lower else curr_usertask_lower

        if task is not None:
            done, skipped, WIP, YTS, reviewyts = create_done + review_done, create_skipped + review_skipped, create_WIP + review_WIP , create_YTS , review_YTS
            markdown_text = f"Total Records: {total_count}, Completed: {done}, Skipped: {skipped}, Create WIP: {create_WIP}, Create YTS: {YTS}, Review YTS - {review_YTS}, Review WIP - {review_WIP} "
        else:
            markdown_text = None

        if curr_username == 'admin':
            return gr.Markdown(value=None, visible=False)
        return gr.Markdown(value=markdown_text, visible=True)

    # Initial user information (for demonstration purposes)
    initial_username = ""
    initial_task_name = ""
    initial_filename = ""
    create_skip_reason = gr.Textbox(label='Reason', value=None, interactive=True, visible=False)
    review_skip_reason = gr.Textbox(label='Reason', value=None, interactive=True, visible=False)
    create_skip_cat = gr.Dropdown(label= 'Skip Category', choices = ['NFSW', 'Lack of Knowledge', 'Bad Data', 'Clear Skip', 'Others'], visible=False)
    review_skip_cat = gr.Dropdown(label= 'Skip Category', choices = ['NFSW', 'Lack of Knowledge', 'Bad Data', 'Clear Skip', 'Others'], visible=False)

    # Create Gradio components
    with gr.Row(equal_height=True):

        with gr.Column(scale=4):
            user_info_display = gr.Markdown(update_user_info(initial_username, initial_task_name, initial_filename), visible=False)
        with gr.Column(scale=3):
            markdown_display = gr.Markdown(initial_filename, visible=False)
        with gr.Column(scale=1):
            btn_refresh = gr.Button(value="Logout", visible=False)
            btn_refresh.click(None, js="window.location.reload()")

    def refresh_user_info(username, task_name, filename):
        return gr.Markdown(update_user_info(username, task_name, filename), visible=True)

    with gr.Tabs() as tabs:
        with gr.Tab('Productivity Report', visible=False) as p_report_tab:
            with gr.Accordion("Filter", open=False):
                with gr.Row():
                    gr.Markdown('FROM')
                    from_day_pr = gr.Dropdown(label='Day' ,choices=days)
                    from_month_pr = gr.Dropdown(label='Month', choices=months)
                    from_year_pr = gr.Dropdown(label='Year', choices=years)
                    gr.Markdown('TO')
                    to_day_pr = gr.Dropdown(label='Day', choices=days)
                    to_month_pr = gr.Dropdown(label='Month', choices=months)
                    to_year_pr = gr.Dropdown(label='Year', choices=years)
                with gr.Row():
                    filter_btn_pr = gr.Button('Filter')

                    def show_filter(from_day, from_month, from_year, to_day, to_month, to_year):
                        if from_day and from_month and from_year and to_day and to_month and to_year:
                            return gr.Button(interactive=True)
                        return gr.Button(interactive=False)

                    from_day_pr.change(show_filter, inputs=[from_day_pr, from_month_pr, from_year_pr, to_day_pr, to_month_pr, to_year_pr], outputs=filter_btn_pr)
                    to_day_pr.change(show_filter, inputs=[from_day_pr, from_month_pr, from_year_pr, to_day_pr, to_month_pr, to_year_pr], outputs=filter_btn_pr)
                    to_month_pr.change(show_filter, inputs=[from_day_pr, from_month_pr, from_year_pr, to_day_pr, to_month_pr, to_year_pr], outputs=filter_btn_pr)
                    to_year_pr.change(show_filter, inputs=[from_day_pr, from_month_pr, from_year_pr, to_day_pr, to_month_pr, to_year_pr], outputs=filter_btn_pr)
                    from_month_pr.change(show_filter, inputs=[from_day_pr, from_month_pr, from_year_pr, to_day_pr, to_month_pr, to_year_pr], outputs=filter_btn_pr)
                    from_year_pr.change(show_filter, inputs=[from_day_pr, from_month_pr, from_year_pr, to_day_pr, to_month_pr, to_year_pr], outputs=filter_btn_pr)

            pro_report = gr.Dataframe(
                headers=['User Name','Completed Date','JSON File Name','Task','Status', 'Rating Average','Total Record Skipped','Total Record Completed', 'Duration (Min)'],
                datatype=["str", "date",'str', 'str', 'str', 'number', 'number', 'number', 'number'],
                row_count=12,
                col_count=(9, "fixed"),
                interactive=False,
                value=initialize_pro_report
            )
            filter_btn_pr.click(
                    fn=get_pro_report,
                    inputs=[from_day_pr, from_month_pr, from_year_pr, to_day_pr, to_month_pr, to_year_pr],
                    outputs=pro_report
            )
        with gr.Tab('Project Summary', visible=False) as p_summary_tab:
            with gr.Accordion("Filter", open=False):
                with gr.Row():
                    gr.Markdown('FROM')
                    from_day_ps = gr.Dropdown(label='Day' ,choices=days)
                    from_month_ps = gr.Dropdown(label='Month', choices=months)
                    from_year_ps = gr.Dropdown(label='Year', choices=years)
                    gr.Markdown('TO')
                    to_day_ps = gr.Dropdown(label='Day', choices=days)
                    to_month_ps = gr.Dropdown(label='Month', choices=months)
                    to_year_ps = gr.Dropdown(label='Year', choices=years)
                with gr.Row():
                    filter_btn_ps = gr.Button('Filter', interactive=False)
                    def show_filter(from_day, from_month, from_year, to_day, to_month, to_year):
                        if from_day and from_month and from_year and to_day and to_month and to_year:
                            return gr.Button(interactive=True)
                        return gr.Button(interactive=False)

                    from_day_ps.change(show_filter, inputs=[from_day_ps, from_month_ps, from_year_ps, to_day_ps, to_month_ps, to_year_ps], outputs=filter_btn_ps)
                    to_day_ps.change(show_filter, inputs=[from_day_ps, from_month_ps, from_year_ps, to_day_ps, to_month_ps, to_year_ps], outputs=filter_btn_ps)
                    to_month_ps.change(show_filter, inputs=[from_day_ps, from_month_ps, from_year_ps, to_day_ps, to_month_ps, to_year_ps], outputs=filter_btn_ps)
                    to_year_ps.change(show_filter, inputs=[from_day_ps, from_month_ps, from_year_ps, to_day_ps, to_month_ps, to_year_ps], outputs=filter_btn_ps)
                    from_month_ps.change(show_filter, inputs=[from_day_ps, from_month_ps, from_year_ps, to_day_ps, to_month_ps, to_year_ps], outputs=filter_btn_ps)
                    from_year_ps.change(show_filter, inputs=[from_day_ps, from_month_ps, from_year_ps, to_day_ps, to_month_ps, to_year_ps], outputs=filter_btn_ps)



            p_summary = gr.Dataframe(
                headers=['Skip Category', 'Total Prompts'],
                datatype=["str", "number"],
                row_count=4,
                col_count=(2, "fixed"),
                interactive=False,
                value=initialize_p_summary
            )
            filter_btn_ps.click(
                    fn=get_project_summary,
                    inputs=[from_day_ps, from_month_ps, from_year_ps, to_day_ps, to_month_ps, to_year_ps],
                    outputs=p_summary
            )

        with gr.Tab('Dashboard', visible=False) as dashboard_tab:
            with gr.Accordion("Filter", open=False):
                with gr.Row():
                    gr.Markdown('FROM')
                    from_day_d = gr.Dropdown(label='Day' ,choices=days)
                    from_month_d = gr.Dropdown(label='Month', choices=months)
                    from_year_d = gr.Dropdown(label='Year', choices=years)
                    gr.Markdown('TO')
                    to_day_d = gr.Dropdown(label='Day', choices=days)
                    to_month_d = gr.Dropdown(label='Month', choices=months)
                    to_year_d = gr.Dropdown(label='Year', choices=years)
                with gr.Row():
                    filter_btn_d = gr.Button('Filter', interactive=False)
                    from_day_d.change(show_filter, inputs=[from_day_d, from_month_d, from_year_d, to_day_d, to_month_d, to_year_d], outputs=filter_btn_d)
                    to_day_d.change(show_filter, inputs=[from_day_d, from_month_d, from_year_d, to_day_d, to_month_d, to_year_d], outputs=filter_btn_d)
                    to_month_d.change(show_filter, inputs=[from_day_d, from_month_d, from_year_d, to_day_d, to_month_d, to_year_d], outputs=filter_btn_d)
                    to_year_d.change(show_filter, inputs=[from_day_d, from_month_d, from_year_d, to_day_d, to_month_d, to_year_d], outputs=filter_btn_d)
                    from_month_d.change(show_filter, inputs=[from_day_d, from_month_d, from_year_d, to_day_d, to_month_d, to_year_d], outputs=filter_btn_d)
                    from_year_d.change(show_filter, inputs=[from_day_d, from_month_d, from_year_d, to_day_d, to_month_d, to_year_d], outputs=filter_btn_d)
            with gr.Accordion("Archive Files", open=False):
                with gr.Row():
                    def get_files_to_archive():
                        try:
                            conn = get_db_connection()
                            cur = conn.cursor()

                            # Ensure archived_files table exists
                            cur.execute("""
                                CREATE TABLE IF NOT EXISTS archived_files (
                                    id SERIAL PRIMARY KEY,
                                    filename VARCHAR(255) UNIQUE NOT NULL
                                )
                            """)

                            # Fetch filenames from files not in archived_files
                            cur.execute("""
                                SELECT filename
                                FROM files
                                WHERE filename NOT IN (SELECT filename FROM archived_files)
                            """)
                            files = cur.fetchall()


                            cur.close()
                            conn.commit()
                            conn.close()

                            files_to_archive = [f[0] for f in files]
                            return gr.Dropdown(choices = files_to_archive, multiselect=True, label='Files to Archive')

                        except Exception as e:
                            print(f"Error retrieving files to archive: {e}")
                            gr.Warning('No File to Archive')
                            return []

                    files_to_archive = gr.Dropdown(choices = [], multiselect=True, label='Files to Archive')
                    curr_username.change(
                        fn=get_files_to_archive,
                        inputs=[],
                        outputs=files_to_archive
                    )
                    def archive_files(files):
                        conn = get_db_connection()
                        cur = conn.cursor()

                        # Insert filenames into archived_files
                        for filename in files:
                            cur.execute("INSERT INTO archived_files (filename) VALUES (%s)", (filename,))

                        conn.commit()
                        cur.close()
                        conn.close()

                        gr.Info('Files archived successfully!')

                    archive_btn = gr.Button('Archive Files')
                    archive_btn.click(
                        fn=archive_files,
                        inputs=[files_to_archive],
                        outputs=None
                    )



            dashboard = gr.Dataframe(
                headers=['JSON File Name' ,'Total Records','Completed','Skipped','Create WIP','Create YTS','Review YTS','Review WIP'],
                datatype=["str", "number", 'number', 'number', 'number', 'number', 'number', 'number'],
                row_count=12,
                col_count=(8, "fixed"),
                interactive=False,
                value=initialize_dashboard
            )
            filter_btn_d.click(
                    fn=get_dashboard,
                    inputs=[from_day_d, from_month_d, from_year_d, to_day_d, to_month_d, to_year_d],
                    outputs=dashboard
            )



        with gr.Tab('Admin Panel', visible=False, id=10) as admin:
            with gr.Row(equal_height=True):
                with gr.Accordion(" Add New User or Change Credentials", open=False):
                  with gr.Row():
                    with gr.Column(scale=1):
                        x = gr.Markdown(' ')
                    with gr.Column(scale=2, variant='panel'):
                        gr.Markdown("# Add New User or Change Credentials")
                        new_username = gr.Textbox(label="Username")
                        new_password = gr.Textbox(label="Password", type="password")
                        new_role = gr.Dropdown(label="Role", choices=['admin', 'creator', 'reviewer'])
                        with gr.Row():
                            add_btn = gr.Button("Add New User")
                            upd_btn = gr.Button("Update Credentials")
                    with gr.Column(scale=1):
                        x = gr.Markdown(' ')

                    def add_user(username, password, role):
                        conn = get_db_connection()
                        cur = conn.cursor()

                        # Check if the user already exists
                        cur.execute("SELECT * FROM users WHERE username = %s", (username.lower(),))
                        existing_user = cur.fetchone()

                        if existing_user:
                            conn.close()
                            gr.Warning('User already exists.')
                            return None

                        # Add the new user if the user does not exist
                        cur.execute("INSERT INTO users (username, password, user_role) VALUES (%s, %s, %s)", (username.lower(), password, role))
                        conn.commit()
                        conn.close()
                        return gr.Info('New User Added Successfully !!')


                    def upd_user(username, new_password, new_role):
                        conn = get_db_connection()
                        cur = conn.cursor()

                        # Check if the user exists
                        cur.execute("SELECT * FROM users WHERE username = %s", (username.lower(),))
                        existing_user = cur.fetchone()

                        if not existing_user:
                            conn.close()
                            gr.Warning('User does not exist.')
                            return None

                        # Update the user's credentials if the user exists
                        cur.execute("UPDATE users SET password = %s, user_role = %s WHERE username = %s", (new_password, new_role, username.lower()))
                        conn.commit()
                        conn.close()
                        return gr.Info('User credentials updated successfully !!')

                    add_btn.click(
                        fn=add_user,
                        inputs=[new_username, new_password, new_role],
                        outputs=None
                    )
                    upd_btn.click(
                        fn=upd_user,
                        inputs=[new_username, new_password, new_role],
                        outputs=None
                    )
            with gr.Column():
                with gr.Row():
                    files_to_export = gr.Dropdown(choices = [], multiselect=True, label='Files to Export')
                curr_username.change(
                    fn=fetch_filenames,
                    inputs=None,
                    outputs=files_to_export
                )
                with gr.Row():
                    create_button = gr.Button("Export Files")
            with gr.Row():
                output_files = gr.Files(label='Exported files')
                files = gr.Files(label='Upload files',file_types=['.jsonl'])

            create_button.click(export_to_jsonl, inputs=files_to_export, outputs=output_files)
            def show_logout(btn):
                return gr.Button(visible=True)
            tabs.change(
                show_logout,
                btn_refresh,
                btn_refresh
            )

            files.upload(process_jsonl_files, files)


        with gr.Tab("Login", id=0) as login_tab:
            def reset_password(username, old_password, new_password):
                conn = get_db_connection()
                cur = conn.cursor()

                # Check if the user exists
                cur.execute("SELECT password FROM users WHERE username = %s", (username.lower(),))
                existing_user = cur.fetchone()

                if not existing_user:
                    conn.close()
                    gr.Warning('User does not exist.')
                    return None

                # Check if the old password is correct
                stored_password = existing_user[0]
                if stored_password != old_password:
                    conn.close()
                    gr.Warning('Old password is incorrect.')
                    return None

                # Update the password if the old password is correct
                cur.execute("UPDATE users SET password = %s WHERE username = %s", (new_password, username.lower()))
                conn.commit()
                conn.close()
                return gr.Info('Password reset successfully.')


            with gr.Row(equal_height=True):
                with gr.Column(scale=1):
                    x = gr.Markdown('')

                with gr.Column(variant='panel', scale=2):
                    with gr.Accordion(open=False, label='Reset Password'):
                        gr.Markdown("## Reset Password")
                        reset_username = gr.Textbox(label="Username")
                        old_password = gr.Textbox(label="Old Password", type="password")
                        new_password = gr.Textbox(label="New Password", type="password")
                        reset_btn = gr.Button("Reset Password")
                    user_def = gr.State('')
                    pass_def = gr.State('')
                    task_def = gr.State('')
                    l_user = gr.Textbox(label="Username")
                    l_pass = gr.Textbox(label="Password", type="password")
                    l_task = gr.Dropdown(label="Choose Task", choices=['Create' , 'Review'])
                    l_submit = gr.Button('Submit', interactive=False)

                    reset_btn.click(
                        fn=reset_password,
                        inputs=[reset_username, old_password, new_password],
                        outputs=None
                    )
                with gr.Column(scale=1):
                    x = gr.Markdown('')

            def validate(s1, s2, s3):
                if s1 is not None and s2 is not None and s3 is not None:
                    return gr.Button(interactive=True)
                return gr.Button(interactive=False)

            def validate_scores(s1,s2,s3):
                if s1 is not None and s2 is not None and s3 is not None and int(s1) > 0 and int(s2) >0 and int(s3) >0:

                    return gr.Button(interactive=True)
                return gr.Button(interactive=False)
            l_user.change(validate, inputs=[l_user, l_pass, l_task], outputs=[l_submit])
            l_task.change(validate, inputs=[l_user, l_pass, l_task], outputs=[l_submit])
            l_pass.change(validate, inputs=[l_user, l_pass, l_task], outputs=[l_submit])

            l_submit.click(
                fn=login,
                inputs=[l_user, l_pass, l_task ],
                outputs=[curr_username, curr_user_task]
            )
            def show_admin(curr_username):
                if curr_username.lower() == 'admin':
                    return gr.Tabs(visible=True),gr.Tabs(visible=True), gr.Tabs(selected=10)
                return gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(selected=1)
            curr_username.change(show_admin, curr_username, outputs=[admin, p_summary_tab, tabs])
            curr_username.change(show_admin, curr_username, outputs=[dashboard_tab, p_report_tab, tabs])

            def update_files(username, user_task):
                if username is None:
                    return gr.Dropdown( choices=['No files available'])
                files = get_files(username.lower(), user_task.lower())

                if (files != []) and (files is not None):
                    files = [file.split('/')[-1] for file in files]
                    return  gr.Dropdown( choices=files, interactive=True)
                return gr.Dropdown( choices=['No files available'])
        def load_question_first(username, curr_user_task, file_selection):

            q = load_question(username.lower(), curr_user_task.lower(), file_selection)

            return gr.Tabs(selected=2), q
        with gr.Tab("Selection", id=1, visible=False) as selection_tab:
          with gr.Row(equal_height=True):
            with gr.Column(scale=1):
              x = gr.Markdown(' ')
            with gr.Column(scale=2):
              file_selection = gr.Dropdown(label="Choose File", choices=['No files availabale'])
              btn = gr.Button('Submit')
            with gr.Column(scale=1):
              x = gr.Markdown(' ')
            btn.click(
                fn=load_question_first,
                inputs=[curr_username , curr_user_task, file_selection],
                outputs=[tabs, curr_prompt]
            )
            btn.click(
                fn=refresh_user_info,
                inputs = [curr_username, curr_user_task, file_selection],
                outputs = user_info_display
            )
            tabs.change(
                fn=update_prompt_counts,
                inputs=[curr_username, file_selection, curr_user_task, user_task],
                outputs=markdown_display
            )

            def change_tab(id):
                id = int(id)
                if id == 1:
                    return gr.Tabs(selected=id), gr.Tabs(visible=False), gr.Tabs(visible=True), gr.Tabs(visible=True)
                elif id ==2:
                    return gr.Tabs(selected=id), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=True)
            curr_user_task.change(update_files, inputs=[curr_username, curr_user_task], outputs=[file_selection])
            files.upload(update_files, inputs=[curr_username, curr_user_task], outputs=[file_selection])
            curr_username.change(show_admin, curr_username, outputs=[admin, p_summary_tab, tabs])
            curr_username.change(show_admin, curr_username, outputs=[dashboard_tab, p_report_tab, tabs])

            files.upload(update_files, inputs=[curr_username, curr_user_task], outputs=[file_selection])

        with gr.Tab('Release WIP', visible=False) as release_wip_tab:
            with gr.Row():
                file_for_info_d = gr.Dropdown(choices=[], multiselect=True, label='Filename')
                tabs.change(
                    fn=get_files_for_file_info_d,
                    inputs=[],
                    outputs=[file_for_info_d]
                )
                username_for_info_d = gr.Dropdown(choices=[], interactive=False, multiselect=True, label='Username')
                id_for_info_d = gr.Dropdown(label='ID', multiselect=True, interactive=False, choices=[])
                release_for_info_d = gr.Button('Release', interactive=False)

                def get_usernames_for_info_d(files, df):
                    filtered_df = df[df['JSON Filename'].isin(files)]
                    unique_usernames = filtered_df['User Name'].unique().tolist()
                    return gr.Dropdown(choices=unique_usernames, label='Username', multiselect=True, interactive=True)



            with gr.Row():
                file_info_d = gr.Dataframe(
                    headers=['ID','JSON Filename','User Name','Task','Status','Start Datetime','End Datetime','Skip Category','Reason for Skip'],
                    datatype=["str", "str", "str", 'str', 'str', 'str', 'date', 'date', 'str'],
                    row_count=12,
                    col_count=(9, "fixed"),
                    interactive=False,
                    visible=True,
                    value=initialize_file_info_d
                )

                file_for_info_d.change(
                    fn=load_file_info_d,
                    inputs=[file_for_info_d],
                    outputs=[file_info_d, username_for_info_d]
                )

                username_for_info_d.change(
                    fn=load_file_info_d_with_username,
                    inputs=[file_for_info_d, username_for_info_d],
                    outputs=[file_info_d, id_for_info_d],
                )

                def mark_yts(id_list):
                    conn = get_db_connection()
                    try:
                        # Create a cursor object using the connection
                        with conn.cursor() as cur:
                            # Construct the SQL query with IN operator
                            query = "UPDATE prompts SET status = 'yts' WHERE id IN %s"

                            # Execute the query with the id_list as a tuple
                            id_list = [str(x) for x in id_list]
                            cur.execute(query, (tuple(id_list),))

                            # Commit the transaction
                            conn.commit()
                            gr.Info(f"Marked ID - { ','.join(id_list)} as YTS")

                    except Exception as e:
                        print(f"Error: {e}")
                        gr.Error(f'Error while moving - {e}')
                        conn.rollback()  # Rollback the transaction in case of error

                    finally:
                        # Close cursor and connection
                        cur.close()
                        conn.close()

                id_for_info_d.change(
                    fn = lambda x: gr.Button(interactive=True) if x is not None else gr.Button(interactive=False),
                    inputs = [ id_for_info_d ],
                    outputs = release_for_info_d
                )
                
                release_for_info_d.click(
                    fn=mark_yts,
                    inputs=[id_for_info_d],
                    outputs=[]
                )
                curr_username.change(show_admin, curr_username, outputs=[release_wip_tab, release_wip_tab, tabs])

        with gr.Tab("SubTask1", id=2, visible=False) as subtask1:

            with gr.Row(equal_height=True):
                with gr.Column(scale=0.35):
                    question = gr.Textbox(label="Question",autoscroll=False,max_lines=20, lines=20, interactive=False)
                    res_skip = gr.Markdown(visible=False, elem_classes="skip")

                    with gr.Row():
                        n_clicks = gr.State(0)
                        score_list = gr.State([])


                        prev_button = gr.Button('Prev', interactive=False, visible=True)


                        next_button = gr.Button("Next", interactive=False)
                        def uninter():
                            return gr.Button(interactive=False)
                        curr_prompt.change(
                            fn=uninter,
                            inputs=None,
                            outputs=[next_button]
                        )
                        with gr.Accordion("Skip", open=False) as acc_0:
                            skip = gr.Button('Skip', interactive=False)
                            skip_cat = gr.Dropdown(label= 'Skip Category', choices = ['NFSW', 'Lack of Knowledge', 'Bad Data', 'Clear Skip', 'Others'], value= curr_prompt.value['review_skip_cat'] or curr_prompt.value['create_skip_cat'])
                            response_skip_reason = gr.Textbox(label='Reason', value =  curr_prompt.value['review_skip_reason'] or curr_prompt.value['create_skip_reason'] ,autoscroll=False, interactive=True)

                        def show(value):
                            if value is not None and value != '' and value != 'Clear Skip' and value != 'Others':
                                return gr.Button(interactive=True), gr.Button(interactive=False), gr.Button(interactive=False)
                            elif value == 'Others':
                                return gr.Button(interactive=False), gr.Button(interactive=False), gr.Button(interactive=False)
                            return gr.Button(interactive=False),  gr.Button(interactive=True), gr.Button(interactive=True)
                        skip_cat.change(show, skip_cat, [skip, next_button, prev_button])
                        response_skip_reason.change(
                            fn = lambda x: gr.Button(interactive=True) if x is not None and x != '' else gr.Button(interactive=False),
                            inputs=[response_skip_reason],
                            outputs=[skip]
                        )

                        def reset_acc(curr_prompt):
                            return gr.Accordion(open=False), gr.Accordion(open=False), gr.Accordion(open=False), gr.Accordion(open=False), gr.Button(interactive=False), gr.Button(interactive=False),gr.Button(interactive=False),gr.Button(interactive=False), gr.Textbox(value=None),  gr.Textbox(value=None),  gr.Textbox(value=None),  gr.Textbox(value=None),  gr.Dropdown(label = 'Skip Category', choices = ['NFSW', 'Lack of Knowledge', 'Bad Data', 'Clear Skip', 'Others'], value= curr_prompt['review_skip_cat'] or curr_prompt['create_skip_cat']),  gr.Dropdown(label = 'Skip Category', choices = ['NFSW', 'Lack of Knowledge', 'Bad Data', 'Clear Skip', 'Others'], value= curr_prompt['review_skip_cat'] or curr_prompt['create_skip_cat']),  gr.Dropdown(label = 'Skip Category', choices = ['NFSW', 'Lack of Knowledge', 'Bad Data', 'Clear Skip', 'Others'], value= curr_prompt['review_skip_cat'] or curr_prompt['create_skip_cat']), gr.Dropdown(label = 'Skip Category', choices = ['NFSW', 'Lack of Knowledge', 'Bad Data', 'Clear Skip', 'Others'], value= curr_prompt['review_skip_cat'] or curr_prompt['create_skip_cat'])


                with gr.Column():
                    with gr.Row():
                        response_1_id = gr.Textbox(label="Response 1 ID",autoscroll=False, max_lines=11, lines=11, interactive=False, visible=False)
                        response_2_id = gr.Textbox(label="Response 2 ID",autoscroll=False, max_lines=11, lines=11,interactive=False, visible=False)
                        response_3_id = gr.Textbox(label="Response 3 ID",autoscroll=False, max_lines=11, lines=11, interactive=False, visible=False)
                        response_1 = gr.Textbox(label="Response 1",autoscroll=False, max_lines=20, lines=20, interactive=False)
                        response_2 = gr.Textbox(label="Response 2",autoscroll=False, max_lines=20,lines=20, interactive=False)
                        response_3 = gr.Textbox(label="Response 3",autoscroll=False, max_lines=20,lines=20, interactive=False)

                    with gr.Row():
                        score_1 = gr.Radio(label="Score 1", choices=[1, 2, 3, 4, 5])
                        score_2 = gr.Radio(label="Score 2", choices=[1, 2, 3, 4, 5])
                        score_3 = gr.Radio(label="Score 3", choices=[1, 2, 3, 4, 5])



                        score_1.change(validate_scores, inputs=[score_1, score_2, score_3], outputs=[next_button])
                        score_2.change(validate_scores, inputs=[score_1, score_2, score_3], outputs=[next_button])
                        score_3.change(validate_scores, inputs=[score_1, score_2, score_3], outputs=[next_button])


        curr_username.change(change_tab, [gr.Textbox(value=1,autoscroll=False, visible=False)], outputs=[tabs, login_tab, selection_tab, subtask1])


        with gr.Tab("SubTask2", id=3, visible=False) as judgement_1:

            judgements_1 = gr.State(value=curr_prompt.value)
            gr.Markdown("## Subtask 2: Judgement Correction")
            n_clicks_j1 = gr.State(0)
            j1_list = gr.State([])
            with gr.Row(equal_height=True):
                with gr.Column(scale=4):
                    question_j1 = gr.Textbox(label= 'Question',autoscroll=False, value=question.value,max_lines=6,lines=6, interactive=False)
                    response_j1 = gr.Textbox(label="Response",autoscroll=False, value=response_1.value, max_lines=6,lines=6 ,interactive=False)
                    res_skip_j1 = gr.Markdown(visible=False, elem_classes="skip")
                    with gr.Row():
                        clear_btn_1 = gr.Button('Prev', visible=True)
                        def render_0():
                            return gr.Tabs(selected=2), gr.Tabs(visible=False), gr.Tabs(visible=True)
                        clear_btn_1.click(
                            fn=render_0,
                            inputs=None,
                            outputs=[tabs, judgement_1, subtask1]
                        )

                        next_button_j1 = gr.Button("Next")
                        with gr.Accordion("Skip", open=False) as acc_1:
                            skip_button_j1 = gr.Button('Skip', interactive=False)
                            skip_cat_j1 = gr.Dropdown(label = 'Skip Category', choices = ['NFSW', 'Lack of Knowledge', 'Bad Data', 'Clear Skip', 'Others'], value= curr_prompt.value['review_skip_cat'] or curr_prompt.value['create_skip_cat'])
                            skip_reason_j1 = gr.Textbox(label = 'Reason',autoscroll=False, value =  curr_prompt.value['review_skip_reason'] or curr_prompt.value['create_skip_reason'] , interactive=True)
                            skip_cat_j1.change(show, skip_cat_j1, [skip_button_j1, next_button_j1, clear_btn_1])
                            skip_reason_j1.change(
                                fn = lambda x: gr.Button(interactive=True) if x is not None and x != '' else gr.Button(interactive=False),
                                inputs=[skip_reason_j1],
                                outputs=[skip_button_j1]
                            )

                with gr.Column(scale=12):
                    rubric_1_j1 = gr.Textbox(label="Rubric",autoscroll=False, max_lines=1,lines=1, interactive=False, value=curr_prompt.value['judgement_1_1_rubric'])
                    rubric_2_j1 = gr.Textbox(visible=False)
                    with gr.Row():
                       
                        with gr.Column():
                            id_1_j1 = gr.Textbox(label="ID 1",autoscroll=False, max_lines=2,lines=2, visible=False, value=curr_prompt.value['judgement_1_1_id'])
                            score_1_j1 = gr.Radio(label="Score 1", choices=[1, 2, 3, 4, 5], value=curr_prompt.value['judgement_1_1_score'])
                            reason_1_j1 = gr.Textbox(label="Reason 1", autoscroll=False, max_lines=13, lines=13, value=curr_prompt.value['judgement_1_1_reason'])
                        with gr.Column():
                            id_2_j1 = gr.Textbox(label="ID 2",autoscroll=False, max_lines=2, lines=2, visible=False, value=curr_prompt.value['judgement_1_2_id'])
                            score_2_j1 = gr.Radio(label="Score 2", choices=[1, 2, 3, 4, 5], value=curr_prompt.value['judgement_1_2_score'])
                            reason_2_j1 = gr.Textbox(label="Reason 2",autoscroll=False, max_lines=13, lines=13, value=curr_prompt.value['judgement_1_2_reason'])




        with gr.Tab("SubTask2", id=4, visible=False) as judgement_2:
            judgements_2 = gr.State(value=curr_prompt.value)
            gr.Markdown("## Subtask 2: Judgement Correction")
            n_clicks_j2 = gr.State(0)
            j2_list = gr.State([])
            with gr.Row(equal_height=True):
                with gr.Column(scale=4):
                    question_j2 = gr.Textbox(label= 'Question',max_lines=6,lines=6,value=question.value,autoscroll=False,  interactive=False)
                    response_j2 = gr.Textbox(label="Response", value=response_2.value,autoscroll=False, max_lines=6, lines=6, interactive=False)
                    res_skip_j2 = gr.Markdown(visible=False, elem_classes="skip")
                    with gr.Row():
                        clear_btn_2 = gr.Button('Prev', visible=True)
                        def render_1():
                            return gr.Tabs(selected=3), gr.Tabs(visible=False), gr.Tabs(visible=True)
                        clear_btn_2.click(
                            fn=render_1,
                            inputs=None,
                            outputs=[tabs, judgement_2, judgement_1]
                        )
                        next_button_j2 = gr.Button("Next")

                        with gr.Accordion("Skip", open=False) as acc_2:
                            skip_button_j2 = gr.Button('Skip', interactive=False)
                            skip_cat_j2 = gr.Dropdown(label = 'Skip Category', choices = ['NFSW', 'Lack of Knowledge', 'Bad Data', 'Clear Skip', 'Others'], value= curr_prompt.value['review_skip_cat'] or curr_prompt.value['create_skip_cat'])
                            skip_reason_j2 = gr.Textbox(label = 'Reason' ,value =  curr_prompt.value['review_skip_reason'] or curr_prompt.value['create_skip_reason'] , autoscroll=False, interactive=True)
                            skip_cat_j2.change(show, skip_cat_j2, [skip_button_j2, next_button_j2, clear_btn_2])
                           
                            skip_reason_j2.change(
                                fn = lambda x: gr.Button(interactive=True) if x is not None and x != '' else gr.Button(interactive=False),
                                inputs=[skip_reason_j2],
                                outputs=[skip_button_j2]
                            )

                with gr.Column(scale=12):
                    rubric_1_j2 = gr.Textbox(label="Rubric",autoscroll=False, max_lines=1,lines=1, interactive=False, value=curr_prompt.value['judgement_2_1_rubric'])
                    rubric_2_j2 = gr.Textbox(visible=False)
                    with gr.Row():
                        
                        with gr.Column():
                            id_1_j2 = gr.Textbox(label="ID 1", autoscroll=False,max_lines=2,lines=2, visible=False, value=curr_prompt.value['judgement_2_1_id'])                    
                            score_1_j2 = gr.Radio(label="Score 1", choices=[1, 2, 3, 4, 5], value=curr_prompt.value['judgement_2_1_score'])
                            reason_1_j2 = gr.Textbox(label="Reason 1",autoscroll=False, max_lines=13, lines=13, value=curr_prompt.value['judgement_2_1_reason'])
                        with gr.Column():
                            id_2_j2 = gr.Textbox(label="ID 2", max_lines=2, lines=2,autoscroll=False, visible=False, value=curr_prompt.value['judgement_2_2_id'])
                            score_2_j2 = gr.Radio(label="Score 2", choices=[1, 2, 3, 4, 5], value=curr_prompt.value['judgement_2_2_score'])
                            reason_2_j2 = gr.Textbox(label="Reason 2",autoscroll=False, max_lines=13, lines=13, value=curr_prompt.value['judgement_2_2_reason'])



        with gr.Tab("SubTask2", id=5, visible=False) as judgement_3:
            judgements_3 = gr.State(value=curr_prompt.value)
            gr.Markdown("## Subtask 2: Judgement Correction")
            n_clicks_j3 = gr.State(0)
            j3_list = gr.State([])
            with gr.Row(equal_height=True):
                with gr.Column(scale=4):
                    question_j3 = gr.Textbox(label='Question',autoscroll=False, max_lines=6,lines=6,value=question.value,  interactive=False)
                    response_j3 = gr.Textbox(label="Response",autoscroll=False,value=response_3.value, max_lines=6,lines=6, interactive=False)
                    res_skip_j3 = gr.Markdown(visible=False, elem_classes="skip")
                    with gr.Row():
                        clear_btn_3 = gr.Button('Prev', visible=True)
                        next_button_j3 = gr.Button("Next")
                        def render_2():
                            return gr.Tabs(selected=4), gr.Tabs(visible=False), gr.Tabs(visible=True)
                        clear_btn_3.click(
                            fn=render_2,
                            inputs=None,
                            outputs=[tabs, judgement_3, judgement_2]

                        )




                        with gr.Accordion("Skip", open=False) as acc_3:
                            skip_button_j3 = gr.Button('Skip', interactive=False)
                            skip_cat_j3 = gr.Dropdown(label = 'Skip Category', choices = ['NFSW', 'Lack of Knowledge', 'Bad Data', 'Clear Skip', 'Others'], value= curr_prompt.value['review_skip_cat'] or curr_prompt.value['create_skip_cat'])
                            skip_reason_j3 = gr.Textbox(label = 'Reason', value = curr_prompt.value['review_skip_reason'] or curr_prompt.value['create_skip_reason'] ,autoscroll=False, interactive=True)
                            skip_cat_j3.change(show, skip_cat_j3, [skip_button_j3, next_button_j3, clear_btn_3])
                            skip_reason_j3.change(
                                fn = lambda x: gr.Button(interactive=True) if x is not None and x != '' else gr.Button(interactive=False),
                                inputs=[skip_reason_j3],
                                outputs=[skip_button_j3]
                            )

                with gr.Column(scale=12):
                    rubric_1_j3 = gr.Textbox(label="Rubric",autoscroll=False, max_lines=1,lines=1, interactive=False, value=curr_prompt.value['judgement_3_1_rubric'])
                    rubric_2_j3 = gr.Textbox(visible=False)
                    with gr.Row():
                        
                        with gr.Column():
                            id_1_j3 = gr.Textbox(label="ID 1", max_lines=2, lines=2,autoscroll=False, visible=False, value=curr_prompt.value['judgement_3_1_id'])
                            score_1_j3 = gr.Radio(label="Score 1", choices=[1, 2, 3, 4, 5], value=curr_prompt.value['judgement_3_1_score'])
                            reason_1_j3 = gr.Textbox(label="Reason 1",autoscroll=False, max_lines=13, lines=13, value=curr_prompt.value['judgement_3_1_reason'])
                        with gr.Column():
                            id_2_j3 = gr.Textbox(label="ID 2", max_lines=2, lines=2, autoscroll=False, visible=False, value=curr_prompt.value['judgement_3_2_id'])
                            score_2_j3 = gr.Radio(label="Score 2", choices=[1, 2, 3, 4, 5], value=curr_prompt.value['judgement_3_2_score'])
                            reason_2_j3 = gr.Textbox(label="Reason 2",autoscroll=False, max_lines=13, lines=13, value=curr_prompt.value['judgement_3_2_reason'])
                        def sync_values(question, response_1, response_2, response_3):
                            return question, question, question, response_1, response_2, response_3


                        curr_prompt.change(
                            fn = reset_acc,
                            inputs=curr_prompt,
                            outputs = [acc_0, acc_1, acc_2, acc_3, skip, skip_button_j1, skip_button_j2, skip_button_j3, response_skip_reason,skip_reason_j1, skip_reason_j2, skip_reason_j3, skip_cat_j1, skip_cat_j2,skip_cat_j3, skip_cat]
                          )

                        def render_3():
                            return gr.Tabs(selected=5), gr.Tabs(visible=False), gr.Tabs(visible=True)


                        def show_btn_j3(n_clicks, j3_list):
                            if n_clicks+1 < len(j3_list):
                                return gr.Button(interactive=True, visible=True)
                            return gr.Button(interactive=False, visible=True)
                        prompts_list = gr.State([])
                        tabs.change(
                            fn=show_btn_j3,
                            inputs=[n_clicks, prompts_list],
                            outputs=prev_button
                        )

                        def add_to_p_list(curr_prompt, prompts_list):
                            for i in range(len(prompts_list)):
                                if prompts_list[i]['prompt_id'] == curr_prompt['prompt_id']:
                                    prompts_list[i] = curr_prompt
                                    # if i == 0:
                                    #     gr.Warning('No more pormpts to go back !!')
                                    return prompts_list
                            prompts_list.append(curr_prompt)
                            return prompts_list

                        curr_prompt.change(add_to_p_list, inputs=[curr_prompt, prompts_list], outputs=prompts_list)
                        def load_prev_prompt(prompts_list, n_clicks):
                            try:
                                p = prompts_list[-n_clicks-1]
                            except:
                                p = prompts_list[-n_clicks]
                                gr.Warning('No more prompts in history to go back !!')

                            n_clicks += 1
                            return gr.Tabs(selected=5), gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=True), p, n_clicks
                        prev_button.click(
                            fn=load_prev_prompt,
                            inputs=[prompts_list, n_clicks],
                            outputs=[tabs, login_tab, selection_tab, subtask1, judgement_1, judgement_2, judgement_3, curr_prompt, n_clicks]
                        )
                        curr_prompt.change(load_scoring_quest, inputs=[curr_username, curr_prompt], outputs=[tabs, curr_username, prompt_id, question, response_1, response_2, response_3, response_1_id, response_2_id, response_3_id, score_1, score_2, score_3, id_1_j1, id_2_j1 ,score_1_j1, score_2_j1, reason_1_j1, reason_2_j1, rubric_1_j1, rubric_2_j1, id_1_j2, id_2_j2,score_1_j2, score_2_j2, reason_1_j2, reason_2_j2, rubric_1_j2, rubric_2_j2, id_1_j3, id_2_j3 ,score_1_j3, score_2_j3, reason_1_j3, reason_2_j3, rubric_1_j3, rubric_2_j3, score_1, score_2, score_3 , create_skip_reason, review_skip_reason, skip_cat, review_skip_cat])
                        question.change(sync_values , inputs=[question, response_1, response_2, response_3], outputs=[question_j1, question_j2, question_j3, response_j1, response_j2, response_j3])
                        next_button.click(save_and_next, inputs=[n_clicks, curr_prompt, id_1_j1, id_2_j1 ,id_1_j2, id_2_j2 ,id_1_j3, id_2_j3 ,curr_username, curr_user_task, file_selection ,score_1, score_2, score_3, response_1_id, response_2_id, response_3_id], outputs=[tabs, login_tab, selection_tab, subtask1, judgement_1, judgement_2, judgement_3, curr_prompt, n_clicks])
                        skip.click(skip_and_next, inputs=[n_clicks, response_skip_reason, curr_prompt, id_1_j1, id_2_j1 ,id_1_j2, id_2_j2 ,id_1_j3, id_2_j3 , curr_username, curr_user_task,file_selection, response_1_id, response_2_id, response_3_id, skip_cat], outputs=[tabs, login_tab, selection_tab, subtask1, judgement_1, judgement_2, judgement_3, curr_prompt, n_clicks])
                        curr_prompt.change(
                            fn=update_prompt_counts,
                            inputs=[curr_username , file_selection, curr_user_task, user_task],
                            outputs=markdown_display
                        )

                        # Do same for judgement 2 and 3 and then submit
                        next_button_j1.click(
                            save_and_next_j1,
                            inputs=[curr_prompt, curr_username, curr_user_task,file_selection,id_1_j1, id_2_j1 ,id_1_j2, id_2_j2 ,id_1_j3, id_2_j3,score_1_j1, score_2_j1, reason_1_j1, reason_2_j1],
                            outputs=[tabs, login_tab, selection_tab, subtask1, judgement_1, judgement_2, judgement_3,curr_prompt]
                        )

                        skip_button_j1.click(
                            skip_and_next_j1,
                            inputs=[skip_reason_j1, curr_username, curr_user_task,file_selection,curr_prompt, id_1_j1, id_2_j1 ,id_1_j2, id_2_j2, id_1_j3, id_2_j3, score_1_j1, score_2_j1, reason_1_j1, reason_2_j1, skip_cat_j1],
                            outputs=[tabs,login_tab, selection_tab, subtask1, judgement_1, judgement_2, judgement_3, curr_prompt]
                        )
                        # Do same for judgement 2 and 3 and then submit
                        next_button_j2.click(
                            save_and_next_j2,
                            inputs=[curr_prompt, curr_username, curr_user_task,file_selection,id_1_j2, id_2_j2 ,id_1_j3, id_2_j3 ,score_1_j2, score_2_j2, reason_1_j2, reason_2_j2],
                            outputs=[tabs, login_tab, selection_tab, subtask1, judgement_1, judgement_2, judgement_3, curr_prompt]
                        )

                        skip_button_j2.click(
                            skip_and_next_j2,
                            inputs=[skip_reason_j2,curr_username, curr_user_task,file_selection,curr_prompt, id_1_j2, id_2_j2,id_1_j3, id_2_j3 ,score_1_j2, score_2_j2, reason_1_j2, reason_2_j2, skip_cat_j2],
                            outputs=[tabs, login_tab, selection_tab, subtask1, judgement_1, judgement_2, judgement_3, curr_prompt]
                        )
                        prev_prompt= gr.State({})


                        next_button_j3.click(
                            save_and_next_j3,
                            inputs=[curr_username, curr_user_task,file_selection,curr_prompt,id_1_j3, id_2_j3 ,score_1_j3, score_2_j3, reason_1_j3, reason_2_j3],
                            outputs=[tabs, login_tab, selection_tab, subtask1, judgement_1, judgement_2, judgement_3, curr_prompt, prev_prompt]
                        )
                        prev_prompt.change(
                            fn= add_to_p_list,
                            inputs=[prev_prompt, prompts_list],
                            outputs=prompts_list
                        )

                        skip_button_j3.click(
                            skip_and_next_j3,
                            inputs=[skip_reason_j3,curr_username, curr_user_task,file_selection,curr_prompt, id_1_j3, id_2_j3 ,score_1_j3, score_2_j3,reason_1_j3, reason_2_j3, skip_cat_j3],
                            outputs=[tabs, login_tab, selection_tab, subtask1, judgement_1, judgement_2, judgement_3, curr_prompt, prev_prompt]
                        )
                        def show_reason(r1, r2, c1, c2,  curr_user_task, curr_prompt):
                            if curr_user_task.lower() == 'review':
                                r2 = curr_prompt['create_skip_reason']
                                c2 = curr_prompt['create_skip_cat']
                                if r2 :
                                    r = f', Reason - {r2}'
                                else :
                                    r = ''
                                # r1 = curr_prompt['review_skip_reason']
                                # r2 = curr_prompt['create_skip_reason']
                                v = f"Category - {c2}" + r
                                return gr.Markdown(visible=True, value=v), gr.Markdown(visible=True, value=v), gr.Markdown(visible=True, value=v), gr.Markdown(visible=True, value=v)
                            return gr.Markdown(visible=False), gr.Markdown(visible=False), gr.Markdown(visible=False), gr.Markdown(visible=False)
                        curr_prompt.change(load_scoring_quest, inputs=[curr_username, curr_prompt], outputs=[tabs, curr_username, prompt_id, question, response_1, response_2, response_3, response_1_id, response_2_id, response_3_id, score_1, score_2, score_3, id_1_j1, id_2_j1 ,score_1_j1, score_2_j1, reason_1_j1, reason_2_j1, rubric_1_j1, rubric_2_j1, id_1_j2, id_2_j2,score_1_j2, score_2_j2, reason_1_j2, reason_2_j2, rubric_1_j2, rubric_2_j2, id_1_j3, id_2_j3 ,score_1_j3, score_2_j3, reason_1_j3, reason_2_j3, rubric_1_j3, rubric_2_j3, score_1, score_2, score_3 , create_skip_reason, review_skip_reason, skip_cat, review_skip_cat])

                        def clear_cat(user_task):
                            if user_task.lower() == 'review':
                                return gr.Dropdown(label = 'Skip Category', choices = ['NFSW', 'Lack of Knowledge', 'Bad Data', 'Clear Skip', 'Others'], value= None), gr.Dropdown(label = 'Skip Category', choices = ['NFSW', 'Lack of Knowledge', 'Bad Data', 'Clear Skip', 'Others'], value= None), gr.Dropdown(label = 'Skip Category', choices = ['NFSW', 'Lack of Knowledge', 'Bad Data', 'Clear Skip', 'Others'], value= None), gr.Dropdown(label = 'Skip Category', choices = ['NFSW', 'Lack of Knowledge', 'Bad Data', 'Clear Skip', 'Others'], value= None)
                            return gr.Dropdown(label = 'Skip Category', choices = ['NFSW', 'Lack of Knowledge', 'Bad Data', 'Clear Skip', 'Others'], value= curr_prompt.value['review_skip_cat'] or curr_prompt.value['create_skip_cat']), gr.Dropdown(label = 'Skip Category', choices = ['NFSW', 'Lack of Knowledge', 'Bad Data', 'Clear Skip', 'Others'], value= curr_prompt.value['review_skip_cat'] or curr_prompt.value['create_skip_cat']), gr.Dropdown(label = 'Skip Category', choices = ['NFSW', 'Lack of Knowledge', 'Bad Data', 'Clear Skip', 'Others'], value= curr_prompt.value['review_skip_cat'] or curr_prompt.value['create_skip_cat']), gr.Dropdown(label = 'Skip Category', choices = ['NFSW', 'Lack of Knowledge', 'Bad Data', 'Clear Skip', 'Others'], value= curr_prompt.value['review_skip_cat'] or curr_prompt.value['create_skip_cat'])
                        tabs.change(clear_cat, inputs=user_task, outputs=[skip_cat_j1, skip_cat_j2, skip_cat_j3, skip_cat ])
                        skip_cat.change(show_reason, inputs=[create_skip_reason, review_skip_reason, skip_cat, review_skip_cat , curr_user_task, curr_prompt], outputs=[res_skip_j1 , res_skip_j2,res_skip , res_skip_j3 ])
                        create_skip_reason.change(show_reason, inputs=[create_skip_reason, review_skip_reason, skip_cat, review_skip_cat , curr_user_task, curr_prompt], outputs=[res_skip_j1 , res_skip_j2,res_skip , res_skip_j3 ])
                        tabs.change(validate_scores, inputs=[score_1, score_2, score_3], outputs=[next_button])
                        def hide_login(curr_username):
                            if curr_username == 'admin':
                                return gr.Tab(visible=False), gr.Tab(visible=False), gr.Tab(visible=False)
                            return gr.Tab(visible=False), gr.Tab(visible=True), gr.Tab(visible=True)

                        def hide_markdown(curr_username):
                            if curr_username == 'admin':
                                return gr.Markdown(visible=False), gr.Markdown(visible=False)
                            return gr.Markdown(visible=True), gr.Markdown(visible=True)
                        tabs.change(hide_markdown, curr_username, [markdown_display, user_info_display])
                        tabs.change(hide_login, curr_username, [login_tab, selection_tab, subtask1])

gr.close_all()
app.launch(debug=True, server_name='0.0.0.0', share=True)

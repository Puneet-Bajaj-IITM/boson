
import psycopg2
from psycopg2 import sql

def get_db_connection():
    return psycopg2.connect(
        dbname="boson",
        user="puneet",
        password="Ddd@1234",  # Replace with your password
        host="localhost"
    )
    
def setup_database():
    conn = get_db_connection()
    cur = conn.cursor()

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
            response_skip_reason TEXT,
            judgements_1_skip_reason TEXT,
            judgements_2_skip_reason TEXT,
            judgements_3_skip_reason TEXT,
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

    conn.commit()
    cur.close()
    conn.close()
setup_database()
print("Database setup complete.")

import psycopg2
from psycopg2.extras import RealDictCursor

# def get_db_connection():
#     return psycopg2.connect(
#         dbname="postgres",
#         user="postgres",
#         password="your_password",  # Replace with your password
#         host="localhost"
#     )

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

# def update_prompt_status_in_db(prompt_id, user_task):

#     try:
#         # Establish a connection to the database
#         conn = get_db_connection()
#         cur = conn.cursor()

#         # Call the stored procedure
#         cur.execute("SELECT update_prompt_status(%s, %s)", (prompt_id, user_task,))
#         conn.commit()

#         # Close the cursor and connection
#         cur.close()
#         conn.close()

#         return "Prompt status updated successfully."
#     # except Exception as e:
#     #     print(f"An error occurred: {e}")
#     #     return "An error occurred while updating the prompt status."
#     finally:
#       pass

# # Example usage
# prompt_id = 2
# user_task = 'review'
# print(update_prompt_status_in_db(prompt_id, user_task))



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
        raise gr.Error(error)

    finally:
        # Close the database connection
        if cur:
            cur.close()
        if conn:
            conn.close()



def process_jsonl_files(files):
    all_file_data = []

    for file in files:
        file_data = []
        filename = str(file.name.split('/')[-1])

        with open(file.name, "r") as f:
            for line in f:
                json_data = json.loads(line)
                file_data.append(json_data)

        # Example: Insert first 3 records from each file into the database
        insert_file_data(filename, file_data)
        all_file_data.extend(file_data)

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

# # Call the function to show all tables
# show_tables()

# """Table named users with fields - id, username , password, user_role"""



# SQL command to create the stored procedure
create_procedure_sql = """
CREATE OR REPLACE FUNCTION initialize_response_scores(p_create_user VARCHAR(50), p_user_task VARCHAR(50), p_filename VARCHAR(255))
RETURNS TABLE(
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

    -- Check if any row was updated
    IF v_prompt_id IS NULL THEN
        RAISE NOTICE 'No prompt was updated. Possibly no prompt with the specified criteria.';
        RETURN;
    END IF;

    -- Fetch corresponding responses and judgements
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
"""


create_stored_procedure(create_procedure_sql)

sqlq = """
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
    -- Check if filename already exists
    PERFORM 1 FROM files WHERE files.filename = p_filename;
    IF FOUND THEN
        RETURN 'File ' || p_filename || ' already exists in the database.';
    END IF;

    -- Insert into files table
    INSERT INTO files (filename) VALUES (p_filename) RETURNING id INTO file_id;

    -- Loop through prompts in the data
    FOR prompt_data IN SELECT * FROM jsonb_array_elements(p_data)
    LOOP
        -- Insert into prompts table with truncated values
        INSERT INTO prompts (prompt_text, domain, task, meta_data, phase, status, file_id)
        VALUES (
            prompt_data->>'prompt',
            LEFT(prompt_data->'meta'->>'prompt_domain', 100),
            LEFT(prompt_data->'meta'->>'prompt_task', 100),
            prompt_data->'meta'::TEXT,
            'create',
            'yts',
            file_id
        )
        RETURNING id INTO prompt_id;

        -- Loop through responses in the prompt data
        FOR response_text IN SELECT jsonb_array_elements_text(prompt_data->'responses')
        LOOP
            -- Insert into responses table
            INSERT INTO responses (prompt_id, response_text) VALUES (prompt_id, response_text) RETURNING id INTO response_id;

            -- Loop through per_response_judgements in the prompt data
            FOR judgement_data IN SELECT * FROM jsonb_array_elements(prompt_data->'per_response_judgements')
            LOOP
                FOR judgement IN SELECT * FROM jsonb_array_elements(judgement_data)
                LOOP
                    -- Insert into judgements table with type casting for the score
                    INSERT INTO judgements (response_id, reason, rubric, score)
                    VALUES (
                        response_id,
                        judgement->>'reason',
                        judgement->>'rubric',
                        (judgement->>'score')::INTEGER
                    );
                END LOOP;
            END LOOP;
        END LOOP;
    END LOOP;

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
            -- Mark prompt phase as 'review' and status as 'hold'
            UPDATE prompts
            SET phase = 'review', status = 'hold'
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
    CREATE OR REPLACE FUNCTION update_judgements(id_1 INTEGER, id_2 INTEGER, id_3 INTEGER,
                                                score_1 INTEGER, score_2 INTEGER, score_3 INTEGER,
                                                reason_1 TEXT, reason_2 TEXT, reason_3 TEXT)
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

        INSERT INTO labelled_judgements (judgement_id, score, reason)
        VALUES (id_3, score_3, reason_3)
        ON CONFLICT (judgement_id) DO UPDATE
        SET score = EXCLUDED.score, reason = EXCLUDED.reason;
    END;
    $$ LANGUAGE plpgsql;

"""

create_stored_procedure(create_stored_procedure_sql3)

def show_table(table_name):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT id , score FROM {table_name} LIMIT 5")
    table_data = cur.fetchall()
    headers = [desc[0] for desc in cur.description]
    print(f"\nTable: {table_name}")
    print(tabulate(table_data, headers=headers, tablefmt="pretty"))
    cur.close()
    conn.close()

# show_table('labelled_judgements')

from pprint import pprint

def load_question(username, user_task, filename):
    conn = get_db_connection()
    user_task = user_task.lower()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    print('querying')

    try:
        # Call the stored procedure
        cur.execute("""
            SELECT * FROM initialize_response_scores(%s, %s, %s)
        """, (username, user_task, filename))

        row = cur.fetchone()  # Fetch only one row
        conn.commit()
        print(row)

        if row:
            return {
                "prompt_id": row['prompt_id'],
                "question": row["question"],
                "response_1_id": row["response_1_id"],
                "response_1": row["response_1"],
                "judgement_1_1_id": row["judgement_1_1_id"],
                "judgement_1_1_score": row["judgement_1_1_score"],
                "judgement_1_1_rubric": row["judgement_1_1_rubric"],
                "judgement_1_1_reason": row["judgement_1_1_reason"],
                "judgement_1_2_id": row["judgement_1_2_id"],
                "judgement_1_2_score": row["judgement_1_2_score"],
                "judgement_1_2_rubric": row["judgement_1_2_rubric"],
                "judgement_1_2_reason": row["judgement_1_2_reason"],
                "judgement_1_3_id": row["judgement_1_3_id"],
                "judgement_1_3_score": row["judgement_1_3_score"],
                "judgement_1_3_rubric": row["judgement_1_3_rubric"],
                "judgement_1_3_reason": row["judgement_1_3_reason"],
                "response_2_id": row["response_2_id"],
                "response_2": row["response_2"],
                "judgement_2_1_id": row["judgement_2_1_id"],
                "judgement_2_1_score": row["judgement_2_1_score"],
                "judgement_2_1_rubric": row["judgement_2_1_rubric"],
                "judgement_2_1_reason": row["judgement_2_1_reason"],
                "judgement_2_2_id": row["judgement_2_2_id"],
                "judgement_2_2_score": row["judgement_2_2_score"],
                "judgement_2_2_rubric": row["judgement_2_2_rubric"],
                "judgement_2_2_reason": row["judgement_2_2_reason"],
                "judgement_2_3_id": row["judgement_2_3_id"],
                "judgement_2_3_score": row["judgement_2_3_score"],
                "judgement_2_3_rubric": row["judgement_2_3_rubric"],
                "judgement_2_3_reason": row["judgement_2_3_reason"],
                "response_3_id": row["response_3_id"],
                "response_3": row["response_3"],
                "judgement_3_1_id": row["judgement_3_1_id"],
                "judgement_3_1_score": row["judgement_3_1_score"],
                "judgement_3_1_rubric": row["judgement_3_1_rubric"],
                "judgement_3_1_reason": row["judgement_3_1_reason"],
                "judgement_3_2_id": row["judgement_3_2_id"],
                "judgement_3_2_score": row["judgement_3_2_score"],
                "judgement_3_2_rubric": row["judgement_3_2_rubric"],
                "judgement_3_2_reason": row["judgement_3_2_reason"],
                "judgement_3_3_id": row["judgement_3_3_id"],
                "judgement_3_3_score": row["judgement_3_3_score"],
                "judgement_3_3_rubric": row["judgement_3_3_rubric"],
                "judgement_3_3_reason": row["judgement_3_3_reason"]
            }
        else:
            return None
    finally:
        cur.close()
        conn.close()

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

def show_table(table_name):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT * FROM {table_name} LIMIT 100")
    table_data = cur.fetchall()
    headers = [desc[0] for desc in cur.description]
    print(f"\nTable: {table_name}")
    print(tabulate(table_data, headers=headers, tablefmt="pretty"))
    cur.close()
    conn.close()

# show_table('files')



def show_table(table_name):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT id , phase, status, file_id, create_user, review_user, create_start_time, create_end_time, review_start_time, review_end_time FROM {table_name}")
    table_data = cur.fetchall()
    headers = [desc[0] for desc in cur.description]
    print(f"\nTable: {table_name}")
    print(tabulate(table_data, headers=headers, tablefmt="pretty"))
    cur.close()
    conn.close()

# show_table('prompts')

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

def save_and_next_j1(curr_prompt, username, user_task, filename, id_1_j1, id_2_j1, id_3_j1 ,id_1_j2, id_2_j2, id_3_j2 ,id_1_j3, id_2_j3, id_3_j3 , score_1_j1, score_2_j1, score_3_j1, reason_1_j1, reason_2_j1, reason_3_j1):
    try:
        # Open a cursor to perform database operations
        conn = get_db_connection()
        cur = conn.cursor()

        cur.callproc("update_judgements", (id_1_j1, id_2_j1, id_3_j1, score_1_j1, score_2_j1, score_3_j1, reason_1_j1, reason_2_j1, reason_3_j1))
        # Commit the transaction
        conn.commit()

        # Close the cursor and connection
        cur.close()
        conn.close()

        print("Judgements updated successfully")
        if get_judgement_data(id_1_j2) or get_judgement_data(id_2_j2) or get_judgement_data(id_3_j2) :
            return gr.Tabs(selected=4), gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=True),gr.Tabs(visible=False), curr_prompt
        if get_judgement_data(id_1_j3) or get_judgement_data(id_2_j3) or get_judgement_data(id_3_j3) :
            return gr.Tabs(selected=5), gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=True), curr_prompt
        print(curr_prompt)
        prompt_data = curr_prompt
        prompt_id = prompt_data['prompt_id']
        update_prompt_status_in_db(prompt_id, user_task)
        q = load_question(username, user_task, filename)
        if q is None:
            return gr.Tabs(selected=1), gr.Tabs(visible=False), gr.Tabs(visible=True),gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=False), ''
        return gr.Tabs(selected=2), gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=True), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=False), q

    except Exception as e:
        print(f"Error updating judgements: {e}")


def skip_and_next_j1(skip_reason, username, user_task, filename ,curr_prompt,id_1_j1, id_2_j1, id_3_j1 ,id_1_j2, id_2_j2, id_3_j2 ,id_1_j3, id_2_j3, id_3_j3, score_1_j1, score_2_j1, score_3_j1, reason_1_j1, reason_2_j1, reason_3_j1):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Call the combined stored procedure

        cur.callproc("update_judgements_and_prompt", (id_1_j1, id_2_j1, id_3_j1, score_1_j1, score_2_j1, score_3_j1, reason_1_j1, reason_2_j1, reason_3_j1, curr_prompt['prompt_id']))
        cur.execute(
            "UPDATE prompts SET judgements_1_skip_reason = %s WHERE id = %s",
            (skip_reason, curr_prompt['prompt_id'])
        )

        conn.commit()
        cur.close()
        conn.close()

        print("Judgements updated and prompt set to review and hold successfully")
        if get_judgement_data(id_1_j2) or get_judgement_data(id_2_j2) or get_judgement_data(id_3_j2) :
            return gr.Tabs(selected=4), gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=True),gr.Tabs(visible=False), curr_prompt
        if get_judgement_data(id_1_j3) or get_judgement_data(id_2_j3) or get_judgement_data(id_3_j3) :
            return gr.Tabs(selected=5), gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=True), curr_prompt
        print(curr_prompt)
        prompt_data = curr_prompt
        prompt_id = prompt_data['prompt_id']
        update_prompt_status_in_db(prompt_id, user_task)
        q = load_question(username, user_task, filename)
        if q['prompt_id'] is None:
            return gr.Tabs(selected=1), gr.Tabs(visible=False), gr.Tabs(visible=True), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), q
        return gr.Tabs(selected=2), gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=True), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=False), q

    except Exception as e:
        print(f"Error in skip_and_next_j1: {e}")

def save_and_next_j2(curr_prompt, username, user_task, filename, id_1_j2, id_2_j2, id_3_j2 ,id_1_j3, id_2_j3, id_3_j3 ,score_1_j2, score_2_j2, score_3_j2, reason_1_j2, reason_2_j2, reason_3_j2):
    try:
        # Open a cursor to perform database operations
        conn = get_db_connection()
        cur = conn.cursor()

        cur.callproc("update_judgements", (id_1_j2, id_2_j2, id_3_j2, score_1_j2, score_2_j2, score_3_j2, reason_1_j2, reason_2_j2, reason_3_j2))


        # Commit the transaction
        conn.commit()

        # Close the cursor and connection
        cur.close()
        conn.close()

        print("Judgements updated successfully")
        if get_judgement_data(id_1_j3) or get_judgement_data(id_2_j3) or get_judgement_data(id_3_j3) :
            return gr.Tabs(selected=5), gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=True), curr_prompt
        print(curr_prompt)
        prompt_data = curr_prompt
        prompt_id = prompt_data['prompt_id']
        update_prompt_status_in_db(prompt_id, user_task)
        q = load_question(username, user_task, filename)
        if q['prompt_id'] is None:
            return gr.Tabs(selected=1), gr.Tabs(visible=False), gr.Tabs(visible=True), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), q
        return gr.Tabs(selected=2), gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=True), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=False), q

    except Exception as e:
        print(f"Error updating judgements: {e}")



def skip_and_next_j2(skip_reason , username, user_task, filename, curr_prompt,id_1_j2, id_2_j2, id_3_j2 ,id_1_j3, id_2_j3, id_3_j3, score_1_j2, score_2_j2, score_3_j2, reason_1_j2, reason_2_j2, reason_3_j2):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Call the combined stored procedure

        cur.callproc("update_judgements_and_prompt", (id_1_j2, id_2_j2, id_3_j2, score_1_j2, score_2_j2, score_3_j2, reason_1_j2, reason_2_j2, reason_3_j2, curr_prompt['prompt_id']))
        cur.execute(
            "UPDATE prompts SET judgements_2_skip_reason = %s WHERE id = %s",
            (skip_reason, curr_prompt['prompt_id'])
        )
        conn.commit()
        cur.close()
        conn.close()
        if get_judgement_data(id_1_j3) or get_judgement_data(id_2_j3) or get_judgement_data(id_3_j3) :
            return  gr.Tabs(selected=5), gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=True), curr_prompt
        print(curr_prompt)
        prompt_data = curr_prompt
        prompt_id = prompt_data['prompt_id']
        update_prompt_status_in_db(prompt_id, user_task)
        q = load_question(username, user_task, filename)
        if q['prompt_id'] is None:
            return gr.Tabs(selected=1), gr.Tabs(visible=False), gr.Tabs(visible=True), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), q
        return  gr.Tabs(selected=2), gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=True), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=False), q
        print("Judgements updated and prompt set to review and hold successfully")

    except Exception as e:
        print(f"Error in skip_and_next_j1: {e}")

def save_and_next_j3(username, user_task, filename, curr_prompt, id_1_j3, id_2_j3, id_3_j3 ,score_1_j3, score_2_j3, score_3_j3, reason_1_j3, reason_2_j3, reason_3_j3):
    try:
        # Open a cursor to perform database operations
        conn = get_db_connection()
        cur = conn.cursor()

        cur.callproc("update_judgements", (id_1_j3, id_2_j3, id_3_j3, score_1_j3, score_2_j3, score_3_j3, reason_1_j3, reason_2_j3, reason_3_j3))
        # Commit the transaction
        conn.commit()

        # Close the cursor and connection
        cur.close()
        conn.close()

        print(curr_prompt)
        prompt_data = curr_prompt
        prompt_id = prompt_data['prompt_id']
        update_prompt_status_in_db(prompt_id, user_task)
        q = load_question(username, user_task, filename)
        if q['prompt_id'] is None:
            return gr.Tabs(selected=1), gr.Tabs(visible=False), gr.Tabs(visible=True), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), q
        return  gr.Tabs(selected=2), gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=True), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=False), q

    except Exception as e:
        print(f"Error updating judgements: {e}")



def skip_and_next_j3(skip_reason, username, user_task, filename, curr_prompt, id_1_j3, id_2_j3, id_3_j3, score_1_j3, score_2_j3, score_3_j3, reason_1_j3, reason_2_j3, reason_3_j3):
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Call the combined stored procedure

        cur.callproc("update_judgements_and_prompt", (id_1_j3, id_2_j3, id_3_j3, score_1_j3, score_2_j3, score_3_j3, reason_1_j3, reason_2_j3, reason_3_j3, curr_prompt['prompt_id']))
        cur.execute(
            "UPDATE prompts SET judgements_3_skip_reason = %s WHERE id = %s",
            (skip_reason, curr_prompt['prompt_id'])
        )
        conn.commit()
        cur.close()
        conn.close()
        print(curr_prompt)
        prompt_data = curr_prompt
        prompt_id = prompt_data['prompt_id']
        update_prompt_status_in_db(prompt_id, user_task)
        q = load_question(username, user_task, filename)
        if q['prompt_id'] is None:
            return gr.Tabs(selected=1), gr.Tabs(visible=False), gr.Tabs(visible=True), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), q

        return gr.Tabs(selected=2), gr.Tabs(visible=False), gr.Tabs(visible=False),gr.Tabs(visible=True), gr.Tabs(visible=False),gr.Tabs(visible=False), gr.Tabs(visible=False), q

        print("Judgements updated and prompt set to review and hold successfully")

    except Exception as e:
        print(f"Error in skip_and_next_j1: {e}")

create_stored_procedure_sql4 = """
CREATE OR REPLACE FUNCTION update_judgements_and_prompt(
    id_1 INTEGER, id_2 INTEGER, id_3 INTEGER,
    score_1 INTEGER, score_2 INTEGER, score_3 INTEGER,
    reason_1 TEXT, reason_2 TEXT, reason_3 TEXT,
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

    INSERT INTO labelled_judgements (judgement_id, score, reason)
    VALUES (id_3, score_3, reason_3)
    ON CONFLICT (judgement_id) DO UPDATE
    SET score = EXCLUDED.score, reason = EXCLUDED.reason;

    UPDATE prompts
    SET phase = 'review', status = 'hold'
    WHERE id = prompt_id;
END;
$$ LANGUAGE plpgsql;
"""

create_stored_procedure(create_stored_procedure_sql4)

def load_scoring_quest(username, row):
    if row is None:
        gr.Info("There are no more Prompts for Labelling, Please select another file")
        return (gr.Tabs(selected=1), username) + (None,) * 47
    return (
        gr.Tabs(), username, row['prompt_id'], row["question"],  row["response_1"], row["response_2"], row["response_3"],
        row["response_1_id"], row["response_2_id"], row["response_3_id"], 0, 0, 0,
        row["judgement_1_1_id"], row["judgement_1_2_id"], row["judgement_1_3_id"], row["judgement_1_1_score"], row["judgement_1_2_score"],
        row["judgement_1_3_score"], row["judgement_1_1_reason"], row["judgement_1_2_reason"], row["judgement_1_3_reason"], row["judgement_1_1_rubric"],
        row["judgement_1_2_rubric"], row["judgement_1_3_rubric"], row["judgement_2_1_id"], row["judgement_2_2_id"], row["judgement_2_3_id"],
        row["judgement_2_1_score"], row["judgement_2_2_score"], row["judgement_2_3_score"], row["judgement_2_1_reason"], row["judgement_2_2_reason"],
        row["judgement_2_3_reason"], row["judgement_2_1_rubric"], row["judgement_2_2_rubric"], row["judgement_2_3_rubric"], row["judgement_3_1_id"],
        row["judgement_3_2_id"], row["judgement_3_3_id"], row["judgement_3_1_score"], row["judgement_3_2_score"], row["judgement_3_3_score"],
        row["judgement_3_1_reason"], row["judgement_3_2_reason"], row["judgement_3_3_reason"], row["judgement_3_1_rubric"], row["judgement_3_2_rubric"],
        row["judgement_3_3_rubric"]
    )



# load_question("admin", "create", 'New Text Document.jsonl')

def get_prompt_counts(filename):
    conn = get_db_connection()
    cur = conn.cursor()

    # SQL query to count the total number of prompts and the number of "Done" prompts for the given file
    cur.execute("""
      SELECT
          (SELECT COUNT(*) FROM prompts JOIN files ON prompts.file_id = files.id WHERE files.filename = %s) AS total_count,
          (SELECT COUNT(*) FROM prompts JOIN files ON prompts.file_id = files.id WHERE files.filename = %s AND prompts.status = 'done' AND prompts.phase = 'create') AS create_done_count,
          (SELECT COUNT(*) FROM prompts JOIN files ON prompts.file_id = files.id WHERE files.filename = %s AND prompts.status = 'hold' AND prompts.phase = 'review') AS skip_count,
          (SELECT COUNT(*) FROM prompts JOIN files ON prompts.file_id = files.id WHERE files.filename = %s AND prompts.status = 'done' AND prompts.phase = 'review') AS review_done_count
    """, (filename, filename, filename, filename))
    counts = cur.fetchone()

    cur.close()
    conn.close()

    return counts

# Example usage:
# filename = "New Text Document.jsonl"
# total_count, done_count, rev = get_prompt_counts(filename)
# print(f"Total prompts for '{filename}': {total_count}")
# print(f"Done prompts for '{filename}': {done_count}")
# print(rev)

import psycopg2
import json
import os

def export_to_jsonl():
    try:
        # Connect to the PostgreSQL database
        conn = get_db_connection()
        # Create a cursor to perform database operations
        cur = conn.cursor()
        cur.execute("SELECT filename FROM files;")
        filenames = cur.fetchall()

        for filename_tuple in filenames:
            filename = filename_tuple[0]

            # Query data from the database
            cur.execute("""
                SELECT
                    p.prompt_text AS prompt,
                    p.response_skip_reason AS reason_for_skip,
                    p.judgements_1_skip_reason AS judgements_1_skip_reason,
                    p.judgements_2_skip_reason AS judgements_2_skip_reason,
                    p.judgements_3_skip_reason AS judgements_3_skip_reason,
                    p.meta_data AS meta,
                    r.id AS response_id,
                    r.response_text AS response,
                    CASE
                        WHEN p.phase = 'review' THEN rr.score
                        ELSE lr.score
                    END AS response_score,
                    j.id AS judgement_id,
                    CASE
                        WHEN p.phase = 'review' THEN rj.reason
                        ELSE lj.reason
                    END AS judgement_reason,
                    j.rubric AS judgement_rubric,
                    CASE
                        WHEN p.phase = 'review' THEN rj.score
                        ELSE lj.score
                    END AS judgement_score
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
                    files f ON p.file_id = f.id
                WHERE
                    p.phase IN ('create', 'review')
                AND
                    p.status = 'done'
                AND
                    f.filename = %s
                ORDER BY
                    p.prompt_text, r.id, j.id;
            """, (filename,))

            # Fetch all rows
            rows = cur.fetchall()

            # Organize data by prompt
            prompts = {}
            for row in rows:
                prompt_text = row[0]
                if prompt_text not in prompts:
                    prompts[prompt_text] = {
                        "prompt": prompt_text,
                        "reason_for_skip": row[1],
                        "judgements_1_skip_reason": row[2],
                        "judgements_2_skip_reason": row[3],
                        "judgements_3_skip_reason": row[4],
                        "meta": row[5],
                        "responses": {}
                    }

                response_id = row[6]
                if response_id not in prompts[prompt_text]["responses"]:
                    prompts[prompt_text]["responses"][response_id] = {
                        "response_id": response_id,
                        "response": row[7],
                        "response_score": row[8],
                        "per_response_judgment": []
                    }

                judgement = {
                    "judgement_id": row[9],
                    "reason": row[10],
                    "rubric": row[11],
                    "score": row[12]
                }

                prompts[prompt_text]["responses"][response_id]["per_response_judgment"].append(judgement)

            # Write data to JSONL file
            with open(f"{filename}", "w") as f:
                for prompt in prompts.values():
                    prompt_copy = prompt.copy()
                    prompt_copy["responses"] = list(prompt_copy["responses"].values())
                    json.dump(prompt_copy, f)
                    f.write('\n')

            print(f"Data exported to {filename} successfully.")


    except Exception as e:
        print(f"Error exporting data to JSONL files: {e}")

    finally:
        # Close cursor and connection
        cur.close()
        conn.close()
        file_paths = [os.path.abspath(filename[0]) for filename in filenames]
        return file_paths

# Usage example
# export_to_jsonl()



def update_prompt_status_in_db(prompt_id, user_task):

    try:
        # Establish a connection to the database
        conn = get_db_connection()
        cur = conn.cursor()
        print('updating')
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
def save_and_next(curr_prompt, id_1_j1, id_2_j1, id_3_j1 ,id_1_j2, id_2_j2, id_3_j2 ,id_1_j3, id_2_j3, id_3_j3 , username, user_task,filename, score_1, score_2, score_3, response_1_id, response_2_id, response_3_id):
    print(type(curr_prompt))
    print(username, user_task,filename, score_1, score_2, score_3, response_1_id, response_2_id, response_3_id)
    update_response_scores(score_1, score_2, score_3, response_1_id, response_2_id, response_3_id)

    if not(score_1 and score_2 and score_3):
        raise gr.Error('Please fill scores for all fields')
    if get_judgement_data(id_1_j1) or get_judgement_data(id_2_j1) or get_judgement_data(id_3_j1) :
        return gr.Tabs(selected=3), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=True), gr.Tabs(visible=False), gr.Tabs(visible=False) ,curr_prompt
    if get_judgement_data(id_1_j2) or get_judgement_data(id_2_j2) or get_judgement_data(id_3_j2) :
        return gr.Tabs(selected=4), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=True), gr.Tabs(visible=False), curr_prompt
    if get_judgement_data(id_1_j3) or get_judgement_data(id_2_j3) or get_judgement_data(id_3_j3) :
        return gr.Tabs(selected=5), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=True),curr_prompt
    print(curr_prompt)
    prompt_data = curr_prompt
    prompt_id = prompt_data['prompt_id']
    update_prompt_status_in_db(prompt_id, user_task)
    q = load_question(username, user_task, filename)
    if q['prompt_id'] is None:
        return gr.Tabs(selected=1), gr.Tabs(visible=False), gr.Tabs(visible=True), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), q
    return gr.Tabs(selected=2), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=True), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), q



# Skip the current question and move to the next question
def skip_and_next(skip_reason, curr_prompt, id_1_j1, id_2_j1, id_3_j1 ,id_1_j2, id_2_j2, id_3_j2 ,id_1_j3, id_2_j3, id_3_j3 ,username, user_task,filename, response_1_id, response_2_id, response_3_id):
    print(username, user_task, response_1_id, response_2_id, response_3_id)
    update_response_scores(-1, -1, -1, response_1_id, response_2_id, response_3_id)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE prompts SET response_skip_reason = %s WHERE id = %s",
        (skip_reason, curr_prompt['prompt_id'])
    )
    conn.commit()
    cur.close()
    conn.close()
    if get_judgement_data(id_1_j1) or get_judgement_data(id_2_j1) or get_judgement_data(id_3_j1) :
        return gr.Tabs(selected=3), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=True), gr.Tabs(visible=False), gr.Tabs(visible=False) ,curr_prompt
    if get_judgement_data(id_1_j2) or get_judgement_data(id_2_j2) or get_judgement_data(id_3_j2) :
        return gr.Tabs(selected=4), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=True), gr.Tabs(visible=False), curr_prompt
    if get_judgement_data(id_1_j3) or get_judgement_data(id_2_j3) or get_judgement_data(id_3_j3) :
        return gr.Tabs(selected=5), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=True),curr_prompt
    print(curr_prompt)
    prompt_data = curr_prompt
    prompt_id = prompt_data['prompt_id']
    update_prompt_status_in_db(prompt_id, user_task)
    q = load_question(username, user_task, filename)
    if q['prompt_id'] is None:
        return gr.Tabs(selected=1), gr.Tabs(visible=False), gr.Tabs(visible=True), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), q
    return gr.Tabs(selected=2), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=True), gr.Tabs(visible=False), gr.Tabs(visible=False), gr.Tabs(visible=False), q


# Save scores and reasons for the current question and submit
def submit_scores(username, user_task, score_1, score_2, score_3, response_1_id, response_2_id, response_3_id, prompt_id):
    update_response_scores(score_1, score_2, score_3,  response_1_id, response_2_id, response_3_id)
    if not(score_1 and score_2 and score_3):
        return gr.Markdown("Thank You!, You can see your responses in Results Tab"), gr.Markdown("PLEASE FILL CORRECTLY"),  gr.JSON("response_scores")


import gradio as gr
import psycopg2
from psycopg2 import sql
import datetime

# Function to verify user credentials
def verify_user(username, password):
    conn = get_db_connection()
    cur = conn.cursor()
    query = sql.SQL("SELECT username FROM users WHERE username = %s AND password = %s")
    cur.execute(query, (username, password))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result is not None

def login(username, password, user_task):
    if verify_user(username, password):
        return username, user_task
    raise gr.Error("Please Enter Correct credentials!")

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
        """
        cur.execute(query, (user_task,))
        filenames = cur.fetchall()

        return [filename[0] for filename in filenames]
    finally:
        cur.close()
        conn.close()

app = gr.Blocks()

with app:
    username = gr.State(value="")
    curr_username = gr.Textbox(username, visible=False)
    prompt = gr.State(value = {})
    curr_prompt = gr.JSON(prompt, visible=False)
    prompt_id = gr.Textbox('', visible=False)
    user_task = gr.State(value="")
    curr_user_task = gr.Textbox(username, visible=False)

    def update_user_info(username, task_name, filename):
        return f"""
        **User Information:** **Username:** {username} | **Task:** {task_name} | **Filename:** {filename} | **Timestamp:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
    def update_prompt_counts(filename, user_task):
        total_count, create, skipped, reviewed = get_prompt_counts(filename)
        if user_task.lower()=='create':
            markdown_text = f"Created - {create}, Skipped - {skipped}, Total - {total_count}"
        else:
            markdown_text = f"Reviewed - {reviewed}, Total - {skipped}"
        return gr.Markdown(value=markdown_text, visible=True)

    # Initial user information (for demonstration purposes)
    initial_username = "JohnDoe"
    initial_task_name = "Review Task"
    initial_filename = "sample_file.jsonl"

    # Create Gradio components
    with gr.Row():

        with gr.Column(scale=9):
            user_info_display = gr.Markdown(update_user_info(initial_username, initial_task_name, initial_filename), visible=False)
        with gr.Column(scale=3):
            markdown_display = gr.Markdown(initial_filename, visible=False)
        with gr.Column(scale=1):
            btn_refresh = gr.Button(value="Logout")
            btn_refresh.click(None, js="window.location.reload()")

    def refresh_user_info(username, task_name, filename):
        return gr.Markdown(update_user_info(username, task_name, filename), visible=True)

    with gr.Tabs() as tabs:

        with gr.Tab('Admin', visible=False, id=10) as admin:
            with gr.Row():
                create_button = gr.Button("export Files")
            with gr.Row():
                output_files = gr.Files(label='Exported files')
                files = gr.Files(label='upload files',file_types=['.jsonl'])

            create_button.click(export_to_jsonl, inputs=None, outputs=output_files)


            files.upload(process_jsonl_files, files)

        with gr.Tab("Login", id=0) as login_tab:
            l_user = gr.Textbox(label="Username")
            l_pass = gr.Textbox(label="Password", type="password")
            l_task = gr.Dropdown(label="Choose Task", choices=['Create' , 'Review'])
            l_submit = gr.Button('Submit', interactive=False)
            def validate(s1,s2,s3):
                if s1 and s2 and s3:
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
                if curr_username == 'admin':
                    return gr.Tabs(visible=True), gr.Tabs(selected=10)
                return gr.Tabs(visible=False), gr.Tabs(selected=1)
            curr_username.change(show_admin, curr_username, outputs=[admin, tabs])
            def update_files(username, user_task):
                if username is None:
                    return gr.Dropdown( choices=['No files available'])
                files = get_files(username, user_task.lower())
                print(files)
                if (files != []) and (files is not None):
                    files = [file.split('/')[-1] for file in files]
                    return  gr.Dropdown( choices=files, interactive=True)
                return gr.Dropdown( choices=['No files available'])
        def load_question_first(username, curr_user_task, file_selection):
            print('Changing tab')
            q = load_question(username, curr_user_task, file_selection)
            print(q)
            return gr.Tabs(selected=2), q
        with gr.Tab("selection", id=1) as selection_tab:
            file_selection = gr.Dropdown(label="Choose File", choices=['No files availabale'])
            btn = gr.Button('Submit')
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
            btn.click(
                fn=update_prompt_counts,
                inputs=[file_selection, user_task],
                outputs=markdown_display
            )

            def change_tab(id):
                id = int(id)
                if id == 1:
                    return gr.Tabs(selected=id), gr.Tabs(visible=True), gr.Tabs(visible=True), gr.Tabs(visible=True)
                elif id ==2:
                    return gr.Tabs(selected=id), gr.Tabs(visible=True), gr.Tabs(visible=True), gr.Tabs(visible=True)
            curr_user_task.change(update_files, inputs=[curr_username, curr_user_task], outputs=[file_selection])
            curr_username.change(show_admin, curr_username, outputs=[admin, tabs])
            files.upload(update_files, inputs=[curr_username, curr_user_task], outputs=[file_selection])


        with gr.Tab("SubTask1", id=2, visible=False) as subtask1:
            with gr.Row(equal_height=True):
                with gr.Column(scale=0.35):
                    question = gr.Textbox(label="Question", lines=22, interactive=False)


                    with gr.Row():
                        p_list = gr.State([])
                        n_clicks = gr.State(0)
                        score_list = gr.State([])

                        def append_to_p_list(l, prompt):
                            l.append(prompt)
                            return l

                        curr_prompt.change(
                            fn=append_to_p_list,
                            inputs=[p_list, curr_prompt],
                            outputs=p_list
                        )
                        def load_p_id(p_list, n_clicks):
                            return p_list[-1 - n_clicks]


                        prev_button = gr.Button('Prev', interactive=False)
                        prev_button.click(
                            fn=load_p_id,
                            inputs=[p_list, n_clicks],
                            outputs=[curr_prompt]
                        )
                        def make_in(p_list):
                            if len(p_list) > 1:
                                return gr.Button(interactive=True)
                            return gr.Button(interactive=False)

                        tabs.change(
                            fn=make_in,
                            inputs=p_list,
                            outputs=[prev_button]
                        )
                        next_button = gr.Button("Next", interactive=False)
                        with gr.Accordion("Skip", open=False) as acc_0:
                            skip = gr.Button('Skip', interactive=False)
                            response_skip_reason = gr.Textbox(label='Reason', interactive=True)


                        def clear_n_clicks(n_clicks):
                            return 0

                        next_button.click(
                            fn=clear_n_clicks,
                            inputs=n_clicks,
                            outputs=n_clicks
                        )
                        def show(value):
                            if value is not None and value != '':
                                return gr.Button(interactive=True)
                            return gr.Button(interactive=False)
                        response_skip_reason.change(show, response_skip_reason, skip)
                        def reset_acc():
                            return gr.Accordian(open=False), gr.Accordian(open=False), gr.Accordian(open=False), gr.Accordian(open=False), gr.Button(interactive=False), gr.Button(interactive=False),gr.Button(interactive=False),gr.Button(interactive=False), gr.Textbox(value=None),  gr.Textbox(value=None),  gr.Textbox(value=None),  gr.Textbox(value=None)


                with gr.Column():
                    with gr.Row():
                        response_1_id = gr.Textbox(label="Response 1 ID", lines=11, interactive=False, visible=False)
                        response_2_id = gr.Textbox(label="Response 2 ID", lines=11, interactive=False, visible=False)
                        response_3_id = gr.Textbox(label="Response 3 ID", lines=11, interactive=False, visible=False)
                        response_1 = gr.Textbox(label="Response 1", lines=21, interactive=False)
                        response_2 = gr.Textbox(label="Response 2", lines=21, interactive=False)
                        response_3 = gr.Textbox(label="Response 3", lines=21, interactive=False)

                    with gr.Row():
                        score_1 = gr.Radio(label="Score 1", choices=[1, 2, 3, 4, 5])
                        score_2 = gr.Radio(label="Score 2", choices=[1, 2, 3, 4, 5])
                        score_3 = gr.Radio(label="Score 3", choices=[1, 2, 3, 4, 5])



                        score_1.change(validate, inputs=[score_1, score_2, score_3], outputs=[next_button])
                        score_2.change(validate, inputs=[score_1, score_2, score_3], outputs=[next_button])
                        score_3.change(validate, inputs=[score_1, score_2, score_3], outputs=[next_button])
                        def enter_in_l(score_list, a, b, c):
                            score_list.append([a, b, c])
                            return score_list

                        next_button.click(
                            fn=enter_in_l,
                            inputs=[score_list, score_1, score_2, score_3],
                            outputs=score_list
                        )
                        def load_sc(score_list, n_clicks):
                            print(load_sc)
                            return score_list[-n_clicks]
                        prev_button.click(
                            fn=load_sc,
                            inputs= [score_list, n_clicks],
                            outputs= [score_1, score_2, score_3]
                        )

            # submit_button = gr.Button("Submit Scores")
            # Thankyou_md = gr.Markdown()
            # output_md = gr.Markdown()
            # output_json = gr.JSON()
        curr_username.change(change_tab, [gr.Textbox(value=1, visible=False)], outputs=[tabs, login_tab, selection_tab, subtask1])
        # curr_prompt.change(change_tab, [gr.Textbox(value=2, visible=False)], outputs=[tabs, login_tab, selection_tab, subtask1])


    # submit_button.click(submit_scores, inputs=[score_1, score_2, score_3, history, current_question_index], outputs=[output_md, Thankyou_md, output_json, curr_hist])


        with gr.Tab("SubTask2", id=3, visible=False) as judgement_1:
            judgements_1 = gr.State(value=curr_prompt.value)
            gr.Markdown("## Subtask 2: Judgement Correction")

            with gr.Row():
                with gr.Column(scale=4):
                    question_j1 = gr.Textbox(label= 'Question', value=question.value,lines=5, interactive=False)
                    response_j1 = gr.Textbox(label="Response", value=response_1.value, lines=12, interactive=False)
                    with gr.Row():
                        clear_btn_1 = gr.Button('Prev')
                        def render_0():
                            return gr.Tabs(selected=2), gr.Tabs(visible=False), gr.Tabs(visible=True)
                        clear_btn_1.click(
                            fn=render_0,
                            inputs=None,
                            outputs=[tabs, judgement_1, subtask1]
                        )
                        clear_btn_1.click(
                            fn=load_p_id,
                            inputs=[p_list, n_clicks],
                            outputs=[curr_prompt]
                        )
                        def load_score(a, b, c):
                            return a, b, c
                        clear_btn_1.click(
                            fn=load_score,
                            inputs= [score_1, score_2, score_3],
                            outputs= [score_1, score_2, score_3]
                        )
                        with gr.Accordion("Skip", open=False) as acc_1:
                            skip_button_j1 = gr.Button('Skip', interactive=False)
                            skip_reason_j1 = gr.Textbox(label = 'Reason', interactive=True)
                            skip_reason_j1.change(show, skip_reason_j1, skip_button_j1)
                        next_button_j1 = gr.Button("Next")
                with gr.Column(scale=12):
                    with gr.Row():
                        with gr.Column():
                            id_1_j1 = gr.Textbox(label="ID 1", lines=2, visible=False)
                            rubric_1_j1 = gr.Textbox(label="Rubric 1", lines=1, interactive=False)
                            score_1_j1 = gr.Radio(label="Score 1", choices=[1, 2, 3, 4, 5])
                            reason_1_j1 = gr.Textbox(label="Reason 1", lines=14)
                        with gr.Column():
                            id_2_j1 = gr.Textbox(label="ID 2", lines=2, visible=False)
                            rubric_2_j1 = gr.Textbox(label="Rubric 2", lines=1, interactive=False)
                            score_2_j1 = gr.Radio(label="Score 2", choices=[1, 2, 3, 4, 5])
                            reason_2_j1 = gr.Textbox(label="Reason 2", lines=14)
                        with gr.Column():
                            id_3_j1 = gr.Textbox(label="ID 3", lines=2, visible=False)
                            rubric_3_j1 = gr.Textbox(label="Rubric 3", lines=1, interactive=False)
                            score_3_j1 = gr.Radio(label="Score 3", choices=[1, 2, 3, 4, 5])
                            reason_3_j1 = gr.Textbox(label="Reason 3", lines=14)

                # with gr.Row():
                #     submit_button_j1 = gr.Button("Submit")
                # Thanks_j1 = gr.Markdown()
                # output_md_j1 = gr.Markdown()
                # output_json_j1 = gr.JSON()


        with gr.Tab("SubTask2", id=4, visible=False) as judgement_2:
            judgements_2 = gr.State(value=curr_prompt.value)
            gr.Markdown("## Subtask 2: Judgement Correction")

            with gr.Row():
                with gr.Column(scale=4):
                    question_j2 = gr.Textbox(label= 'Question',lines=5,value=question.value,  interactive=False)
                    response_j2 = gr.Textbox(label="Response", lines=12, value=response_2.value, interactive=False)
                    with gr.Row():
                        clear_btn_2 = gr.Button('Prev')
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
                            skip_reason_j2 = gr.Textbox(label = 'Reason', interactive=True)
                            skip_reason_j2.change(show, skip_reason_j2, skip_button_j2)

                with gr.Column(scale=12):
                    with gr.Row():
                        with gr.Column():
                            id_1_j2 = gr.Textbox(label="ID 1", lines=2, visible=False)
                            rubric_1_j2 = gr.Textbox(label="Rubric 1", lines=1, interactive=False)
                            score_1_j2 = gr.Radio(label="Score 1", choices=[1, 2, 3, 4, 5])
                            reason_1_j2 = gr.Textbox(label="Reason 1", lines=14)
                        with gr.Column():
                            id_2_j2 = gr.Textbox(label="ID 2", lines=2, visible=False)
                            rubric_2_j2 = gr.Textbox(label="Rubric 2", lines=1, interactive=False)
                            score_2_j2 = gr.Radio(label="Score 2", choices=[1, 2, 3, 4, 5])
                            reason_2_j2 = gr.Textbox(label="Reason 2", lines=14)
                        with gr.Column():
                            id_3_j2 = gr.Textbox(label="ID 3", lines=2, visible=False)
                            rubric_3_j2 = gr.Textbox(label="Rubric 3", lines=1, interactive=False)
                            score_3_j2 = gr.Radio(label="Score 3", choices=[1, 2, 3, 4, 5])
                            reason_3_j2 = gr.Textbox(label="Reason 3", lines=14)

                # with gr.Row():
                #     submit_button_j1 = gr.Button("Submit")
            # Thanks_j2 = gr.Markdown()
            # output_md_j2 = gr.Markdown()
            # output_json_j2 = gr.JSON()


        with gr.Tab("SubTask2", id=5, visible=True) as judgement_3:
            judgements_3 = gr.State(value=curr_prompt.value)
            gr.Markdown("## Subtask 2: Judgement Correction")
            with gr.Row():
                with gr.Column(scale=4):
                    question_j3 = gr.Textbox(label='Question', lines=5,value=question.value,  interactive=False)
                    response_j3 = gr.Textbox(label="Response", lines=12,value=response_3.value,  interactive=False)
                    with gr.Row():
                        clear_btn_3 = gr.Button('Prev')
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
                            skip_reason_j3 = gr.Textbox(label = 'Reason', interactive=True)
                            skip_reason_j3.change(show, skip_reason_j3, skip_button_j3)

                with gr.Column(scale=12):
                    with gr.Row():
                        with gr.Column():
                            id_1_j3 = gr.Textbox(label="ID 1", lines=2, visible=False)
                            rubric_1_j3 = gr.Textbox(label="Rubric 1", lines=1, interactive=False)
                            score_1_j3 = gr.Radio(label="Score 1", choices=[1, 2, 3, 4, 5])
                            reason_1_j3 = gr.Textbox(label="Reason 1", lines=14)
                        with gr.Column():
                            id_2_j3 = gr.Textbox(label="ID 2", lines=2, visible=False)
                            rubric_2_j3 = gr.Textbox(label="Rubric 2", lines=1, interactive=False)
                            score_2_j3 = gr.Radio(label="Score 2", choices=[1, 2, 3, 4, 5])
                            reason_2_j3 = gr.Textbox(label="Reason 2", lines=14)
                        with gr.Column():
                            id_3_j3 = gr.Textbox(label="ID 3", lines=2, visible=False)
                            rubric_3_j3 = gr.Textbox(label="Rubric 3", lines=1, interactive=False)
                            score_3_j3 = gr.Radio(label="Score 3", choices=[1, 2, 3, 4, 5])
                            reason_3_j3 = gr.Textbox(label="Reason 3", lines=14)
                        curr_prompt.change(load_scoring_quest, inputs=[curr_username, curr_prompt], outputs=[tabs, curr_username, prompt_id, question, response_1, response_2, response_3, response_1_id, response_2_id, response_3_id, score_1, score_2, score_3, id_1_j1, id_2_j1, id_3_j1 ,score_1_j1, score_2_j1, score_3_j1, reason_1_j1, reason_2_j1, reason_3_j1, rubric_1_j1, rubric_2_j1, rubric_3_j1, id_1_j2, id_2_j2, id_3_j2 ,score_1_j2, score_2_j2, score_3_j2, reason_1_j2, reason_2_j2, reason_3_j2,rubric_1_j2, rubric_2_j2, rubric_3_j2, id_1_j3, id_2_j3, id_3_j3 ,score_1_j3, score_2_j3, score_3_j3, reason_1_j3, reason_2_j3, reason_3_j3, rubric_1_j3, rubric_2_j3, rubric_3_j3 ])


                # with gr.Row():
                #     submit_button_j1 = gr.Button("Submit")
            # Thanks_j3 = gr.Markdown()
            # output_md_j3 = gr.Markdown()
            # output_json_j3 = gr.JSON()

            def sync_values(question, response_1, response_2, response_3):
                return question, question, question, response_1, response_2, response_3

            question.change(sync_values , inputs=[question, response_1, response_2, response_3], outputs=[question_j1, question_j2, question_j3, response_j1, response_j2, response_j3])
            next_button.click(save_and_next, inputs=[curr_prompt, id_1_j1, id_2_j1, id_3_j1 ,id_1_j2, id_2_j2, id_3_j2 ,id_1_j3, id_2_j3, id_3_j3 ,curr_username, curr_user_task, file_selection ,score_1, score_2, score_3, response_1_id, response_2_id, response_3_id], outputs=[tabs, login_tab, selection_tab, subtask1, judgement_1, judgement_2, judgement_3, curr_prompt])
            skip.click(skip_and_next, inputs=[response_skip_reason, curr_prompt, id_1_j1, id_2_j1, id_3_j1 ,id_1_j2, id_2_j2, id_3_j2 ,id_1_j3, id_2_j3, id_3_j3 , curr_username, curr_user_task,file_selection, response_1_id, response_2_id, response_3_id], outputs=[tabs, login_tab, selection_tab, subtask1, judgement_1, judgement_2, judgement_3, curr_prompt])
            curr_prompt.change(
                fn=update_prompt_counts,
                inputs=[file_selection, user_task],
                outputs=markdown_display
            )

            # Do same for judgement 2 and 3 and then submit
            next_button_j1.click(
                save_and_next_j1,
                inputs=[curr_prompt, curr_username, curr_user_task,file_selection,id_1_j1, id_2_j1, id_3_j1 ,id_1_j2, id_2_j2, id_3_j2 ,id_1_j3, id_2_j3, id_3_j3,score_1_j1, score_2_j1, score_3_j1, reason_1_j1, reason_2_j1, reason_3_j1],
                outputs=[tabs, login_tab, selection_tab, subtask1, judgement_1, judgement_2, judgement_3,curr_prompt]
            )

            skip_button_j1.click(
                skip_and_next_j1,
                inputs=[skip_reason_j1, curr_username, curr_user_task,file_selection,curr_prompt, id_1_j1, id_2_j1, id_3_j1 ,id_1_j2, id_2_j2, id_3_j2 ,id_1_j3, id_2_j3, id_3_j3 , score_1_j1, score_2_j1, score_3_j1, reason_1_j1, reason_2_j1, reason_3_j1],
                outputs=[tabs,login_tab, selection_tab, subtask1, judgement_1, judgement_2, judgement_3, curr_prompt]
            )



            # Do same for judgement 2 and 3 and then submit
            next_button_j2.click(
                save_and_next_j2,
                inputs=[curr_prompt, curr_username, curr_user_task,file_selection,id_1_j2, id_2_j2, id_3_j2 ,id_1_j3, id_2_j3, id_3_j3 ,score_1_j2, score_2_j2, score_3_j2, reason_1_j2, reason_2_j2, reason_3_j2],
                outputs=[tabs, login_tab, selection_tab, subtask1, judgement_1, judgement_2, judgement_3, curr_prompt]
            )

            skip_button_j2.click(
                skip_and_next_j2,
                inputs=[skip_reason_j2,curr_username, curr_user_task,file_selection,curr_prompt, id_1_j2, id_2_j2, id_3_j2 ,id_1_j3, id_2_j3, id_3_j3 ,score_1_j2, score_2_j2, score_3_j2, reason_1_j2, reason_2_j2, reason_3_j2],
                outputs=[tabs, login_tab, selection_tab, subtask1, judgement_1, judgement_2, judgement_3, curr_prompt]
            )


            next_button_j3.click(
                save_and_next_j3,
                inputs=[curr_username, curr_user_task,file_selection,curr_prompt,id_1_j3, id_2_j3, id_3_j3 ,score_1_j3, score_2_j3, score_3_j3, reason_1_j3, reason_2_j3, reason_3_j3],
                outputs=[tabs, login_tab, selection_tab, subtask1, judgement_1, judgement_2, judgement_3, curr_prompt]
            )

            skip_button_j3.click(
                skip_and_next_j3,
                inputs=[skip_reason_j3,curr_username, curr_user_task,file_selection,curr_prompt, id_1_j3, id_2_j3, id_3_j3 ,score_1_j3, score_2_j3, score_3_j3, reason_1_j3, reason_2_j3, reason_3_j3],
                outputs=[tabs, login_tab, selection_tab, subtask1, judgement_1, judgement_2, judgement_3, curr_prompt]
            )

            def reset_acc():
                return gr.Accordion(open=False), gr.Accordion(open=False), gr.Accordion(open=False), gr.Accordion(open=False), gr.Button(interactive=False), gr.Button(interactive=False),gr.Button(interactive=False),gr.Button(interactive=False), gr.Textbox(value=None),  gr.Textbox(value=None),  gr.Textbox(value=None),  gr.Textbox(value=None)


            curr_prompt.change(
                fn = reset_acc,
                inputs=None,
                outputs = [acc_0, acc_1, acc_2, acc_3, skip, skip_button_j1, skip_button_j2, skip_button_j3, response_skip_reason,skip_reason_j1, skip_reason_j2, skip_reason_j3]
              )

            # submit_button.click(
            #     save_and_submit,
            #     inputs=[question, response, rubric, score_1, score_2, reason_1, reason_2, judgements, current_question_index],
            #     outputs=[Thanks, output_md, output_json, curr_hist]
            # )


app.launch(debug=True, server_name='0.0.0.0')



def show_table(table_name):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT id , phase, status, file_id, create_user, review_user, create_start_time, create_end_time, review_start_time, review_end_time FROM {table_name}")
    table_data = cur.fetchall()
    headers = [desc[0] for desc in cur.description]
    print(f"\nTable: {table_name}")
    print(tabulate(table_data, headers=headers, tablefmt="pretty"))
    cur.close()
    conn.close()


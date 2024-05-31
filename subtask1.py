import gradio as gr
import json

# Load data from a JSONL file
def load_data(data_file_path):
    questions = []
    with open(data_file_path, "r") as f:
        for line in f:
            data = json.loads(line)
            questions.append(data)
    return questions

# Initialize response scores based on loaded questions
def initialize_response_scores(questions):
    return [{"question": q["prompt"], "response_1": q["responses"][0], "response_2": q["responses"][1], "response_3": q["responses"][2], "score_1": None, "score_2": None, "score_3": None, "reason_1": None, "reason_2": None, "reason_3": None} for q in questions]

# Load question data at a given index
def load_question(index, history):
    if index < 0:
        index = len(history) - 1
    elif index >= len(history):
        index = 0
    question_data = history[index]
    return (question_data["question"], question_data["response_1"], question_data["response_2"], question_data["response_3"], question_data["score_1"] or 0, question_data["score_2"] or 0, question_data["score_3"] or 0, question_data['reason_1'], question_data['reason_2'], question_data['reason_3'], history, index)

# Preprocess data to update response scores in questions
def preprocess_data(history):
    data = questions.copy()
    for i in range(len(history)):
        data[i]['scores'] = [history[i]['score_1'], history[i]['score_2'], history[i]['score_3']]
        data[i]['reasons'] = [history[i]['reason_1'], history[i]['reason_2'], history[i]['reason_3']]
    return data

# Save preprocessed data to a JSONL file
def save_data(history):
    preprocessed_data = preprocess_data(history)
    with open("subtask1_data.jsonl", "a") as f:
        for sample in preprocessed_data:
            json.dump(sample, f)
            f.write("\n")

# Save scores and reasons for the current question and move to the next question
def save_and_next(score_1, score_2, score_3, reason_1, reason_2, reason_3, history, current_question_index):
    history = update_response_scores(score_1, score_2, score_3, reason_1, reason_2, reason_3, history, current_question_index)
    if not(score_1 and score_2 and score_3 and reason_1 and reason_2 and reason_3):
        return load_question(current_question_index, history)
    return load_question(current_question_index + 1, history)

# Save scores and reasons for the current question and move to the previous question
def save_and_prev(score_1, score_2, score_3, reason_1, reason_2, reason_3, history, current_question_index):
    history = update_response_scores(score_1, score_2, score_3, reason_1, reason_2, reason_3, history, current_question_index)
    return load_question(current_question_index - 1, history)

# Skip the current question and move to the next question
def skip_and_next(history, current_question_index):
    history = update_response_scores(0, 0, 0, "", "", "", history, current_question_index)
    return load_question(current_question_index + 1, history)

# Save scores and reasons for the current question and submit
def submit_scores(score_1, score_2, score_3, reason_1, reason_2, reason_3, history, current_question_index):
    history = update_response_scores(score_1, score_2, score_3, reason_1, reason_2, reason_3, history, current_question_index)
    if not(score_1 and score_2 and score_3 and reason_1 and reason_2 and reason_3):
        return gr.Markdown("Thank You!, You can see your responses in Results Tab"), gr.Markdown("PLEASE FILL CORRECTLY"),  gr.JSON(response_scores), history
    save_data(history)
    return gr.Markdown("Thank you! Here is the labeled data:"), gr.Markdown('Thank you!, you can see your responses in Results Tab'), gr.JSON(history), history

# Update response scores and reasons
def update_response_scores(score_1, score_2, score_3, reason_1, reason_2, reason_3, history, current_question_index):
    history[current_question_index]["score_1"] = score_1
    history[current_question_index]["score_2"] = score_2
    history[current_question_index]["score_3"] = score_3
    history[current_question_index]["reason_1"] = reason_1
    history[current_question_index]["reason_2"] = reason_2
    history[current_question_index]["reason_3"] = reason_3
    return history

# Load initial data
questions = load_data('data.jsonl')
response_scores = initialize_response_scores(questions)

# Launch the Gradio interface
with gr.Blocks() as subtask1_demo:
    gr.Markdown("## Subtask 1: Response Scoring")
    history = gr.State(value=response_scores)
    current_question_index = gr.State(value=0)
    
    with gr.Tab("Scoring"):
        with gr.Row(equal_height=True):
            with gr.Column(scale=0.35):
                question = gr.Textbox(label="Question", lines=4, interactive=False)

                scoring_rubric = gr.Markdown("""
                ### Scoring Rubric
                - **Score 1**: The response fails to understand or address the reasoning problem.
                - **Score 2**: The response exhibits major flaws in reasoning.
                - **Score 3**: The response partially addresses the reasoning problem but contains significant errors.
                - **Score 4**: The response offers a nearly complete and accurate solution with minor flaws.
                - **Score 5**: The response delivers a perfect solution with clear understanding.
                """)

                with gr.Row():
                    prev_button = gr.Button("Prev")
                    next_button = gr.Button("Next")
                    skip = gr.Button('Skip')

            with gr.Column():
                with gr.Row():
                    response_1 = gr.Textbox(label="Response 1", lines=12, interactive=False)
                    response_2 = gr.Textbox(label="Response 2", lines=12, interactive=False)
                    response_3 = gr.Textbox(label="Response 3", lines=12, interactive=False)

                with gr.Row():
                    score_1 = gr.Radio(label="Score 1", choices=[1, 2, 3, 4, 5])
                    score_2 = gr.Radio(label="Score 2", choices=[1, 2, 3, 4, 5])
                    score_3 = gr.Radio(label="Score 3", choices=[1, 2, 3, 4, 5])

                with gr.Row():
                    reason_1 = gr.Textbox(label="Reason for Score 1")
                    reason_2 = gr.Textbox(label="Reason for Score 2")
                    reason_3 = gr.Textbox(label="Reason for Score 3")

        submit_button = gr.Button("Submit Scores")
        Thankyou_md = gr.Markdown()
        curr_hist = gr.JSON(history, visible=False)

    with gr.Tab("Results"):
        output_md = gr.Markdown()
        output_json = gr.JSON()

    prev_button.click(save_and_prev, inputs=[score_1, score_2, score_3, reason_1, reason_2, reason_3, history, current_question_index], outputs=[question, response_1, response_2, response_3, score_1, score_2, score_3, reason_1, reason_2, reason_3, curr_hist, current_question_index])
    next_button.click(save_and_next, inputs=[score_1, score_2, score_3, reason_1, reason_2, reason_3, history, current_question_index], outputs=[question, response_1, response_2, response_3, score_1, score_2, score_3, reason_1, reason_2, reason_3, curr_hist, current_question_index])
    skip.click(skip_and_next, inputs=[history, current_question_index], outputs=[question, response_1, response_2, response_3, score_1, score_2, score_3, reason_1, reason_2, reason_3, curr_hist, current_question_index])

    submit_button.click(submit_scores, inputs=[score_1, score_2, score_3, reason_1, reason_2, reason_3, history, current_question_index], outputs=[output_md, Thankyou_md, output_json, curr_hist])

    subtask1_demo.load(lambda: load_question(0, history.value), outputs=[question, response_1, response_2, response_3, score_1, score_2, score_3, reason_1, reason_2, reason_3, curr_hist, current_question_index])

    subtask1_demo.launch()

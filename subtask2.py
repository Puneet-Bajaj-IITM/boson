import gradio as gr
import json

def load_data(data_file_path):
    questions = []
    with open(data_file_path, "r") as f:
        for line in f:
            data = json.loads(line)
            questions.append(data)
    return questions

def filter_data(questions):
    filtered_data = []
    for item in questions:
        prompt = item['prompt']
        for i, response in enumerate(item['responses']):
            judgments = item['per_response_judgements'][i]
            rubrics = {}
            for judgment in judgments:
                rubric_type = judgment[0]
                if rubric_type not in rubrics:
                    rubrics[rubric_type] = {
                        "scores": [judgment[1]],
                        "reasons": [judgment[2]]
                    }
                else:
                    rubrics[rubric_type]["scores"].append(judgment[1])
                    rubrics[rubric_type]["reasons"].append(judgment[2])
            for rubric_type, data in rubrics.items():
                filtered_data.append({
                    "prompt": prompt,
                    "response": response,
                    "rubric": rubric_type,
                    "scores": data["scores"],
                    "reasons": data["reasons"]
                })
    return filtered_data

questions = load_data('data.jsonl')
filtered_data = filter_data(questions)

def load_question(index, judgements):
    if index < 0:
        index = len(judgements) - 1
    elif index >= len(judgements):
        index = 0
    question_data = judgements[index]
    return question_data["prompt"],question_data["response"],question_data["rubric"],question_data["scores"][0],question_data["scores"][1],question_data["reasons"][0],question_data["reasons"][1] ,current_question_index, index

def preprocess_data(judgements):
    questions = []
    grouped_data = {}
    for item in judgements:
        prompt = item['prompt']
        response = item['response']
        rubric = item['rubric']
        scores = item['scores']
        reasons = item['reasons']
        if (prompt, response) not in grouped_data:
            grouped_data[(prompt, response)] = []
        for score, reason in zip(scores, reasons):
            grouped_data[(prompt, response)].append([rubric, score, reason])
    for (prompt, response), judgments in grouped_data.items():
        question_entry = next((q for q in questions if q['prompt'] == prompt), None)
        if not question_entry:
            question_entry = {'prompt': prompt, 'responses': [], 'per_response_judgements': [], 'meta': {}}
            questions.append(question_entry)
        question_entry['responses'].append(response)
        question_entry['per_response_judgements'].append(judgments)
    return questions

def save_data(judgements):
    preprocessed_data = preprocess_data(judgements)
    with open("task2.jsonl", "a") as f:
        for sample in preprocessed_data:
            json.dump(sample, f)
            f.write("\n")

def save_and_submit(question, response, rubric, score_1, score_2, reason_1, reason_2, judgements, current_question_index):
    judgements[current_question_index] = {
        "prompt": question,
        "response": response,
        "rubric": rubric,
        "scores": [score_1, score_2],
        "reasons": [reason_1, reason_2]
    }
    save_data(judgements)
    return gr.Markdown("Thank you for submitting! See your response in the Results tab"), gr.Markdown("Thank you for submitting!"), gr.JSON(judgements), judgements

def save_and_next(question, response, rubric, score_1, score_2, reason_1, reason_2, judgements, current_question_index):
    judgements[current_question_index] = {
        "prompt": question,
        "response": response,
        "rubric": rubric,
        "scores": [score_1, score_2],
        "reasons": [reason_1, reason_2]
    }
    return load_question(current_question_index + 1, judgements)

def save_and_prev(question, response, rubric, score_1, score_2, reason_1, reason_2, judgements, current_question_index):
    judgements[current_question_index] = {
        "prompt": question,
        "response": response,
        "rubric": rubric,
        "scores": [score_1, score_2],
        "reasons": [reason_1, reason_2]
    }
    return load_question(current_question_index - 1, judgements)

def skip_and_next(judgements, current_question_index):
    return load_question(current_question_index + 1, judgements)

with gr.Blocks() as subtask2_demo:
    judgements = gr.State(value=filtered_data)
    current_question_index = gr.State(value=0)
    gr.Markdown("## Subtask 2: Judgement Correction")

    with gr.Tab('Judgements'):
        with gr.Row():
            with gr.Column(scale=0.4):
                question = gr.Textbox(label="Prompt", lines=2, interactive=False)
                response = gr.Textbox(label="Response", lines=12, interactive=False)
                with gr.Row():
                    prev_button = gr.Button("Prev")
                    next_button = gr.Button("Next")
                    skip_button = gr.Button("Skip")
            with gr.Column(scale=0.6):
                rubric = gr.Textbox(label="Rubric", lines=2, interactive=False)
                with gr.Row():
                    with gr.Column():
                        score_1 = gr.Radio(label="Score 1", choices=[1, 2, 3, 4, 5])
                        reason_1 = gr.Textbox(label="Reason 1", lines=10)
                    with gr.Column():
                        score_2 = gr.Radio(label="Score 2", choices=[1, 2, 3, 4, 5])
                        reason_2 = gr.Textbox(label="Reason 2", lines=10)
        with gr.Row():
            submit_button = gr.Button("Submit")
        Thanks = gr.Markdown()
        curr_hist = gr.JSON(judgements, visible=False)

    with gr.Tab('Results'):
        output_md = gr.Markdown()
        output_json = gr.JSON()

    prev_button.click(
        save_and_prev, 
        inputs=[question, response, rubric, score_1, score_2, reason_1, reason_2, judgements, current_question_index], 
        outputs=[question, response, rubric, score_1, score_2, reason_1, reason_2, curr_hist,current_question_index]
    )
    next_button.click(
        save_and_next, 
        inputs=[question, response, rubric, score_1, score_2, reason_1, reason_2, judgements, current_question_index], 
        outputs=[question, response, rubric, score_1, score_2, reason_1, reason_2, curr_hist, current_question_index]
    )
    skip_button.click(
        skip_and_next, 
        inputs=[judgements, gr.State(value=0)], 
        outputs=[question, response, rubric, score_1, score_2, reason_1, reason_2,curr_hist, current_question_index]
    )
    submit_button.click(
        save_and_submit, 
        inputs=[question, response, rubric, score_1, score_2, reason_1, reason_2, judgements, current_question_index], 
        outputs=[Thanks, output_md, output_json, curr_hist]
    )

    subtask2_demo.load(
        lambda: load_question(0, judgements.value), 
        outputs=[question, response, rubric, score_1, score_2, reason_1, reason_2, curr_hist, current_question_index]
    )

subtask2_demo.launch()

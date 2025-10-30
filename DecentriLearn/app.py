import openai
import os
import gradio as gr
openai.api_key=os.getenv('openai_appkey')
# doc is here https://platform.openai.com/docs/guides/chat/chat-vs-completions?utm_medium=email&_hsmi=248334739&utm_content=248334739&utm_source=hs_email
def get_chatgpt(input_text):
    chat_completion = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",
    messages=[
        # system message first, it helps set the behavior of the assistant
        {"role": "system", "content": "You are a helpful assistant."},
        # I am the user, and this is my prompt
        {"role": "user", "content": input_text},
        # we can also add the previous conversation
        # {"role": "assistant", "content": "Episode III."},
        ],
     )
# let's see the reply
    #print(chat_completion.choices[0].message.content)
    return chat_completion.choices[0].message.content
with gr.Blocks(
    css="""
    .message.svelte-w6rprc.svelte-w6rprc.svelte-w6rprc {font-size: 20px; margin-top: 20px}
    #component-21 > div.wrap.svelte-w6rprc {height: 600px;}
    """
) as iface:
    state = gr.State([])
    #caption_output = None
    #gr.Markdown(title)
    #gr.Markdown(description)
    #gr.Markdown(article)

    with gr.Row():
        with gr.Column(scale=1):
            with gr.Row():
                with gr.Column(scale=1):
                    chat_input = gr.Textbox(lines=1, label="Quesiton Input")
                    with gr.Row():
                        clear_button = gr.Button(value="Clear", interactive=True)
                        submit_button = gr.Button(
                            value="提问", interactive=True, variant="primary"
                        )
                    
        with gr.Column():
            caption_output_v1 = gr.Textbox(lines=0, label="答案")
            
            
        
       
        submit_button.click(
                        get_chatgpt,
                        [
                            chat_input,
                        ],
                        [caption_output_v1],
                    )
       
    examples=[["毛主席是什么时候出生的?"]]
    examples = gr.Examples(
       examples=examples,
       inputs=[ chat_input],
    )

iface.queue(concurrency_count=1, api_open=False, max_size=10)
iface.launch(enable_queue=True)
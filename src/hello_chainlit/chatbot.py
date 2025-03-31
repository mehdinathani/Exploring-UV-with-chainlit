import chainlit as cl
import os
from agents import Agent, RunConfig, AsyncOpenAI, OpenAIChatCompletionsModel, Runner
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

gemini_api_key = os.getenv("GEMINI_API_KEY")
# Step 1: Provider

provider =  AsyncOpenAI(
    api_key=gemini_api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

# Step 2: Model

model = OpenAIChatCompletionsModel(
    model="gemini-2.0-flash",
   openai_client=provider
)

# Step 3: Config defined the run level
run_config = RunConfig(
    model=model, 
    model_provider=provider,
    tracing_disabled=True
)

# Step 4 : Agent
agent  = Agent(
    instructions="You are helpful assistant that can answer questions and support",
    name="SwiftSolvesStudios Agent"
)



@cl.on_chat_start
async def start():
    cl.user_session.set("history", [])
    await cl.Message(
        content="SwiftSolvesStudios: Hello, I am a SwiftSolvesStudios Support Agent. How can I help you?",
    ).send()
        
@cl.on_message
async def main(message: cl.Message):
    history = cl.user_session.get("history")

    # standard interface [{}]
    history.append({"role": "user", "content": message.content})
    # Step 5 : Run
    result = await Runner.run(
        input= history, #message.content,
        starting_agent=agent,
        run_config=run_config
    )
    history.append({"role": "assistant", "content": result.final_output})
    cl.user_session.set("history", history)
    await cl.Message(
        content=f"SwiftSolvesStudios: {result.final_output}",
    ).send()

    
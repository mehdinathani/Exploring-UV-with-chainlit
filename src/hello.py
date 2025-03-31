import chainlit as cl

@cl.on_message
async def handle_message(message: cl.Message):
    await cl.Message(
        content=f"Chainlit: {message.content}",
    ).send()
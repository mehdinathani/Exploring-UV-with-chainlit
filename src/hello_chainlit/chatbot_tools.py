import os
from dotenv import load_dotenv
from typing import cast, List
import chainlit as cl
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel
from agents.run import RunConfig
from agents.tool import function_tool

# Load the environment variable
load_dotenv()

gemini_api_key = os.getenv("GEMINI_API_KEY")

# check if the API key is present, if not raised the error
if not gemini_api_key:
    raise ValueError("GEMINI_API_KEY is not set. Please define it in your .env file.")

STUDENT_DATA = {
    "101": {"name": "Alice Johnson", "class": "5A", "age": 10, "parent": "Mr. Johnson"},
    "102": {"name": "Bob Smith", "class": "6B", "age": 11, "parent": "Mrs. Smith"},
    "103": {"name": "Charlie Brown", "class": "4C", "age": 9, "parent": "Mr. Brown"},
    "104": {"name": "Diana Davis", "class": "7D", "age": 12, "parent": "Mrs. Davis"},
    "105": {"name": "Eva White", "class": "3E", "age": 8, "parent": "Mr. White"},
    "106": {"name": "Frank Miller", "class": "8F", "age": 13, "parent": "Mrs. Miller"},
    "107": {"name": "Grace Taylor", "class": "2G", "age": 7, "parent": "Mr. Taylor"},
    "108": {"name": "Henry Clark", "class": "9H", "age": 14, "parent": "Mrs. Clark"},
    "109": {"name": "Ivy Lee", "class": "1I", "age": 6, "parent": "Mr. Lee"},
    "110": {"name": "Jack Wilson", "class": "10J", "age": 15, "parent": "Mrs. Wilson"},}

STUDENT_RESULTS = {
    "101": {"Math": "A", "Science": "B+", "English": "A-"},
    "102": {"Math": "B", "Science": "A", "English": "B+"},
    "103":{"Math": "C+", "Science": "A-", "English": "C"},

}
STUDENT_ATTENDANCE = {
    "101": "Present: 90%, Absent: 10%",
    "102": "Present: 85%, Absent: 15%",
    "103": "Present: 80%, Absent: 20%",

}

CLASS_SCHEDULE = {
    "5A": "Math - 9 AM, Science - 11 AM, English - 1 PM",
    "6B": "English - 10 AM, Math - 12 PM, Science - 2 PM"
}

@function_tool
@cl.step(type="student data tool")
def get_student_data(student_id: str) -> str:
    """
    Get the student data by student ID
    """
    print(f"Getting student data for {student_id}")
    return str(STUDENT_DATA.get(student_id, "Student not found"))

@function_tool
@cl.step(type="student result tool")
def get_student_result(student_id: str) -> str:
    """
    Get the student result by student ID
    """
    print(f"Getting student result for {student_id}")
    return str(STUDENT_RESULTS.get(student_id, "Result not found"))

@function_tool
@cl.step(type="student attendance tool")
def get_student_attendance(student_id: str) -> str:
    """
    Get the student attendance by student ID
    """
    print(f"Getting student attendance for {student_id}")
    return str(STUDENT_ATTENDANCE.get(student_id, "Attendance not found")
)

@function_tool
@cl.step(type="class schedule tool")
def get_class_schedule(class_name: str) -> str:
    """
    Get the class schedule by class name
    """
    print(f"Getting class schedule for {class_name}")
    return str(CLASS_SCHEDULE.get(class_name, "Schedule not found"))






@cl.set_starters
async def set_starts() -> List[cl.Starter]:
    return [
        cl.Starter(
            label="Greetings",
            message = "Hello! What can you help me with today?"

        ),
        # cl.Starter("Find the weather in Karachi.")
    ]

@function_tool
@cl.step(type="weather tool")
def get_weather(location: str, unit:str = "C") -> str:
    """
    Get the weather in a given location
    """
    print(f"Getting weather for {location}")
    return "It's 30 degrees in {location}"

@cl.on_chat_start
async def start():
    #Reference 
    external_client = AsyncOpenAI(
        api_key=gemini_api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta/",
        )
    
    model = OpenAIChatCompletionsModel(
        model="gemini-2.0-flash",
        openai_client=external_client
    )

    config = RunConfig(
        model=model,
        model_provider=external_client,
        tracing_disabled=True
    )

    """
    set up chat session when a user connect
    """

    # Initialized an empty chat history in the session
    cl.user_session.set("chat_history", [])
    cl.user_session.set("config", config)
    agent : Agent = Agent(
        name="Assistant",
        instructions="You are a helpful assistant",
        model=model,
        tools=[
            get_class_schedule,
            get_student_attendance,
            get_student_data,
            get_student_result,
            get_weather
        ],
        
    )
    # agent.tools.append([get_class_schedule, get_student_attendance, get_student_data, get_student_result, get_weather])
    cl.user_session.set("agent", agent)

    await cl.Message(content="Welcome to the Swift Solves Studios, how may i help you today?").send()

@cl.on_message
async def main(message: cl.Message):
    """ Process the incoming messages and generate responses"""
    #    Send thinking message
    msg = cl.Message(content="")
    await msg.send()

    agent: Agent = cast(Agent, cl.user_session.get("agent"))
    config : RunConfig = cast(RunConfig, cl.user_session.get("config"))

    # Retrive the chat history from the session
    history = cl.user_session.get("chat_history") or []

    # append the users message history 
    history.append({"role": "user", "content": message.content})

    try:
        print("\n[CALLING_AGENT_WITH_CONTEXT]\n", history, "\n")
        # result =  Runner.run_sync(agent, history, run_config=config) 

        # response_content = result.final_output

        # # uppdate the thinking message with the actual message
        # msg.content = response_content
        # await msg.update()
        result =  Runner.run_streamed(agent, history, run_config=config)

        async for event in result.stream_events():
            if event.type == "raw_response_event" and hasattr(event.data, 'delta'):
                token = event.data.delta
                await msg.stream_token(token)

        # apend the assistant message to the history
        history.append({"role": "assistant", "content": token})


        # update the session with the new history
        cl.user_session.set("chat_history", history)

        # optional : log the interactions 
        print(f'User: {message.content}')
        print(f'Assistant : {token}')

    except Exception as e:
        msg.content = f"Error: {str(e)}"    
        await msg.send()
        print(f'Error: {str(e)}')

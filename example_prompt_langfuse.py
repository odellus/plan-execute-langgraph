from langchain_core.prompts import ChatPromptTemplate
from langfuse import get_client
from langfuse.langchain import CallbackHandler
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()
# Loads in client with env vars from load_dotenv
langfuse = get_client() 
langfuse_callback_handler = CallbackHandler() 

langfuse.create_prompt(
    name="event-planner",
    prompt=
    "Plan an event titled {{Event_Name}}. The event will be about: {{Event_Description}}. "
    "The event will be held in {{Location}} on {{Date}}. "
    "Consider the following factors: audience, budget, venue, catering options, and entertainment. "
    "Provide a detailed plan including potential vendors and logistics.",
    config={
        "model":"claude4_sonnet",
        "temperature": 0,
    },
    labels=["production"]
)

langfuse_prompt = langfuse.get_prompt("event-planner")

model_name = langfuse_prompt.config["model"]
temperature = str(langfuse_prompt.config["temperature"])

langchain_prompt = ChatPromptTemplate.from_template(
    langfuse_prompt.get_langchain_prompt(),
    metadata={"langfuse_prompt": langfuse_prompt},
)
 
model = ChatOpenAI(model=model_name, temperature=temperature)
 
chain = langchain_prompt | model

example_input = {
    "Event_Name": "Wedding",
    "Event_Description": "The wedding of Julia and Alex, a charming couple who share a love for art and nature. This special day will celebrate their journey together with a blend of traditional and contemporary elements, reflecting their unique personalities.",
    "Location": "Central Park, New York City",
    "Date": "June 5, 2024"
}

# we pass the callback handler to the chain to trace the run in Langfuse
response = chain.invoke(input=example_input,config={"callbacks":[langfuse_callback_handler]})
 
print(response.content)
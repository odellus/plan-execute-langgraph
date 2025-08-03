from pydantic import BaseModel, Field
import operator
from typing import Annotated, List, Tuple, Union, Literal
from typing_extensions import TypedDict
import asyncio

from langchain_community.tools.searx_search.tool import SearxSearchResults
from langchain_community.utilities import SearxSearchWrapper
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, START, END

from dotenv import load_dotenv
from phoenix.otel import register


# DO THIS BEFORE TRYING TO SET UP TRACER_PROVIDER
load_dotenv()

# configure the Phoenix tracer AFTER CALLING load_dotenv()
tracer_provider = register(
  project_name="plan-execute", # Default is 'default'
  auto_instrument=True # Auto-instrument your app based on installed OI dependencies
)

def get_planner(llm):
    planner_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """For the given objective, come up with a simple step by step plan. \
    This plan should involve individual tasks, that if executed correctly will yield the correct answer. Do not add any superfluous steps. \
    The result of the final step should be the final answer. Make sure that each step has all the information needed - do not skip steps.""",
            ),
            ("placeholder", "{messages}"),
        ]
    )
    planner = planner_prompt | llm.with_structured_output(Plan)
    return planner


class PlanExecute(TypedDict):
    input: str
    plan: List[str]
    past_steps: Annotated[List[Tuple], operator.add]
    response: str

class Plan(BaseModel):
    """Plan to follow in future"""

    steps: List[str] = Field(
        description="different steps to follow, should be in sorted order"
    )

class Response(BaseModel):
    """Response to user."""
    response: str


class Act(BaseModel):
    """Action to perform."""
    action: Union[Response, Plan] = Field(
        description="Action to perform. If you want to respond to user because you have the answer, use Response. "
        "If you need to further use tools to get the answer, use Plan."
    )


def get_replanner(llm):

    replanner_prompt = ChatPromptTemplate.from_template(
    """For the given objective, come up with a simple step by step plan. \
This plan should involve individual tasks, that if executed correctly will yield the correct answer. Do not add any superfluous steps. \
The result of the final step should be the final answer. Make sure that each step has all the information needed - do not skip steps.

Your objective was this:
{input}

Your original plan was this:
{plan}

You have currently done the follow steps:
{past_steps}

Update your plan accordingly. If no more steps are needed and you can return to the user, then respond with that. Otherwise, fill out the plan. Only add steps to the plan that still NEED to be done. Do not return previously done steps as part of the plan."""
    )

    replanner = replanner_prompt | llm.with_structured_output(Act)
    return replanner

def get_searxng_tool(num_results=3):
    wrapper = SearxSearchWrapper(searx_host="http://localhost:8082")
    return SearxSearchResults(wrapper=wrapper, num_results=num_results)
    

def get_llm(model):
    return ChatOpenAI(
        model=model,
        base_url='http://localhost:11434/v1', 
        api_key='ollama',
    )

def create_execute_agent(model='qwen3:latest', num_results=5):
    llm = get_llm(model=model)
    tools = [get_searxng_tool(num_results=num_results)]
    prompt = "You are a helpful assistant."
    return create_react_agent(llm, tools, prompt=prompt)




llm = get_llm("qwen3:latest")
planner = get_planner(llm)
replanner = get_replanner(llm)
agent_executor = create_execute_agent(model='qwen3:latest', num_results=3)

async def execute_step(state: PlanExecute):
    plan = state["plan"]
    plan_str = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(plan))
    if len(plan) < 1:
        task = "Answer the user with Response action."
    task = plan[0]
    task_formatted = f"""For the following plan:
{plan_str}\n\nYou are tasked with executing step {1}, {task}."""
    agent_response = await agent_executor.ainvoke(
        {"messages": [("user", task_formatted)]}
    )
    return {
        "past_steps": [(task, agent_response["messages"][-1].content)],
    }


async def plan_step(state: PlanExecute):
    plan = await planner.ainvoke({"messages": [("user", state["input"])]})
    return {"plan": plan.steps}


async def replan_step(state: PlanExecute):
    output = await replanner.ainvoke(state)
    if isinstance(output.action, Response):
        return {"response": output.action.response}
    else:
        return {"plan": output.action.steps}


def should_end(state: PlanExecute):
    if "response" in state and state["response"]:
        return END
    else:
        return "agent"

def get_graph():

    workflow = StateGraph(PlanExecute)

    # Add the plan node
    workflow.add_node("planner", plan_step)

    # Add the execution step
    workflow.add_node("agent", execute_step)

    # Add a replan node
    workflow.add_node("replan", replan_step)

    workflow.add_edge(START, "planner")

    # From plan we go to agent
    workflow.add_edge("planner", "agent")

    # From agent, we replan
    workflow.add_edge("agent", "replan")

    workflow.add_conditional_edges(
        "replan",
        # Next, we pass in the function that will determine which node is called next.
        should_end,
        ["agent", END],
    )

    # Finally, we compile it!
    # This compiles it into a LangChain Runnable,
    # meaning you can use it as you would any other runnable
    app = workflow.compile()
    return app

async def main():
    app = get_graph()
    config = {"recursion_limit": 50}
    inputs = {"input": "what is the hometown of the mens 2024 Australia open winner?"}
    async for event in app.astream(inputs, config=config):
        for k, v in event.items():
            if k != "__end__":
                print(v)


if __name__ == "__main__":
    asyncio.run(main())

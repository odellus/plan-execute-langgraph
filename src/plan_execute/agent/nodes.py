
from langchain_community.tools.searx_search.tool import SearxSearchResults
from langchain_community.utilities import SearxSearchWrapper
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph import END
from langgraph.types import Command
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from plan_execute.agent.models import Plan, PlanExecute, Response, Act

# from phoenix.otel import register
from plan_execute.config import settings
from langfuse.langchain import CallbackHandler
from dotenv import load_dotenv

# DO THIS BEFORE TRYING TO SET UP TRACER_PROVIDER

# configure the Phoenix tracer AFTER CALLING load_dotenv()
# tracer_provider = register(
#   project_name="plan-execute-tw", # Default is 'default'
#   auto_instrument=True, # Auto-instrument your app based on installed OI dependencies
#   protocol="http/protobuf",
# )

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

Update your plan accordingly. If no more steps are needed and you can return to the user, then respond with that. Otherwise, fill out the plan. Only add steps to the plan that still NEED to be done. Do not return previously done steps as part of the plan.
When you are done return with a Response action, not a Plan action please. If there are still plan items unaccounted for, proceed with a Plan action. 
Reason extremely briefly in reasoning. Seriously just think like 10-20 words and that's it. It's only there so you don't say Response action and then want to list a plan.
If it's a plan, use Plan aka action.steps . Unless the user is asking for a plan then you'll just have to be smart or this won't work.
"""

    )

    replanner = replanner_prompt | llm.with_structured_output(Act)
    return replanner

def get_searxng_tool(num_results=3):
    wrapper = SearxSearchWrapper(searx_host=f"{settings.searxng_host}:{settings.searxng_port}", unsecure=True)
    return SearxSearchResults(wrapper=wrapper, num_results=num_results)
    

def get_llm(model):
    return ChatOpenAI(
        model=model,
        base_url=settings.openai_base_url, 
        api_key=settings.openai_api_key.get_secret_value(),
    )

def create_execute_agent(model='claude4_sonnet', num_results=5):
    llm = get_llm(model=model)
    tools = [get_searxng_tool(num_results=num_results)]
    prompt = "You are a helpful assistant."
    return create_react_agent(llm, tools, prompt=prompt)


llm = get_llm("claude4_sonnet")
planner = get_planner(llm)
replanner = get_replanner(llm)
agent_executor = create_execute_agent(model='claude4_sonnet', num_results=3)

async def execute_step(state: PlanExecute):
    plan = state["plan"]
    plan_str = "\n".join(f"{i + 1}. {step}" for i, step in enumerate(plan))
    if len(plan) < 1:
        task = "Answer the user with Response action."
    else:
        task = plan[0]
    task_formatted = f"""For the following plan:
{plan_str}\n\nYou are tasked with executing step {1}, {task}."""
    agent_response = await agent_executor.ainvoke(
        {"messages": [("user", task_formatted)]}
    )
    return Command(
        update={"past_steps": [(task, agent_response["messages"][-1].content)]},
        goto="replan_step",
    )


async def plan_step(state: PlanExecute):
    plan = await planner.ainvoke({"messages": [("user", state["input"])]})
    return Command(update={"plan": plan.steps}, goto="execute_step")


async def replan_step(state: PlanExecute):
    output = await replanner.ainvoke(state)
    if isinstance(output.action, Response):
        return Command(update={"response": output.action.response}, goto=END)
    else:
        return Command(update={"plan": output.action.steps}, goto="execute_step")

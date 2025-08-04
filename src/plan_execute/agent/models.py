from pydantic import BaseModel, Field
import operator
from typing import Annotated, List, Tuple, Union, Literal
from typing_extensions import TypedDict



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
    response: str = Field(
        description="The final response to the user's query."
        "Only use when you have the answer.",
    )


class Act(BaseModel):
    """Action to perform."""
    action: Union[Response, Plan] = Field(
        description="Action to perform. If you want to respond to user because you have the answer, use Response. "
        "If you need to further use tools to get the answer, use Plan."
    )

class ChatRequest(BaseModel):
    message: str
    thread_id: str = Field(default="default")

class ChatResponse(BaseModel):
    response: str


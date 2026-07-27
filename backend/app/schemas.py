from pydantic import BaseModel


class ActionDescriptor(BaseModel):
    tool: str  # gmail | calendar | tasks
    operation: str
    params: dict
    agent_name: str | None = None


class Authorization(BaseModel):
    type: str  # policy | instruction | approval
    ref: str | None = None

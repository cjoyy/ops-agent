from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


class GraphState(TypedDict):
    messages: Annotated[list, add_messages]


load_dotenv()

model = init_chat_model(
    "llama-3.3-70b-versatile",
    model_provider="groq",
)


def call_llm(state: GraphState) -> dict:
    response = model.invoke(state["messages"])
    return {"messages": [response]}


graph = StateGraph(GraphState)
graph.add_node("call_llm", call_llm)
graph.add_edge(START, "call_llm")
graph.add_edge("call_llm", END)

app = graph.compile()

first_result = app.invoke({"messages": ["Halo, ini test graph pertama saya"]})
print("Messages length after first invoke:", len(first_result["messages"]))

second_input = {
    "messages": first_result["messages"] + ["Ini pesan kedua, masih ingat konteks sebelumnya?"]
}
second_result = app.invoke(second_input)
print("Messages length after second invoke:", len(second_result["messages"]))

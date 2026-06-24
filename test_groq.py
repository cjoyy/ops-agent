from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool


load_dotenv()

model = init_chat_model(
    "llama-3.3-70b-versatile",
    model_provider="groq",
)

response = model.invoke("Halo, kamu model apa dan siapa yang membuatmu?")
print(response.content)


@tool
def get_weather(city: str) -> str:
    """Return dummy weather information for a city."""
    return f"Cuaca di {city}: cerah, 30 derajat"


model_with_tools = model.bind_tools([get_weather])
tool_response = model_with_tools.invoke("Cuaca di Jakarta gimana?")
print(tool_response.tool_calls)

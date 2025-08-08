from langchain.agents import initialize_agent, Tool
from langchain_google_genai import ChatGoogleGenerativeAI
from tool_wrapper import youtube_search_tool
from dotenv import load_dotenv  # ✅ import from python-dotenv
import os

# Load all variables from the .env file into environment variables
load_dotenv()

# Get API key
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    raise ValueError("GOOGLE_API_KEY not found in environment variables.")

# Gemini 2.0 Flash LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)

# Define tools for the agent
tools = [
    Tool(
        name="YouTubeSearch",
        func=youtube_search_tool,
        description="Search YouTube and return the first matching video link"
    )
]

# Initialize the agent
agent = initialize_agent(
    tools,
    llm,
    agent="zero-shot-react-description",
    verbose=True
)

if __name__ == "__main__":
    query = "General farming tips which is around 30 minutes"
    result = agent.run(f"Find me a YouTube link for '{query}'")
    print("Agent Result:", result)

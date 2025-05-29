from setuptools import setup, find_packages

setup(
    name="ai-coach",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "langgraph>=0.0.15",
        "langchain>=0.1.0",
        "langchain-community>=0.0.20",
        "langchain-openai>=0.0.2",
        "pydantic>=2.0.0",
        "python-dotenv>=1.0.0",
        "openai>=1.0.0"
    ],
    python_requires=">=3.9",
) 
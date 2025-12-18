"""
NODO x402 Python SDK Setup
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="nodo-x402",
    version="1.0.0",
    author="NODO Team",
    author_email="dev@nodo.ai",
    description="Python SDK for NODO x402 API - AI prediction market analysis with Solana payments",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nodo-ai/nodo-x402",
    project_urls={
        "Documentation": "https://docs.nodo.ai",
        "Bug Tracker": "https://github.com/nodo-ai/nodo-x402/issues",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Office/Business :: Financial",
    ],
    python_requires=">=3.10",
    install_requires=[
        "httpx>=0.26.0",
    ],
    extras_require={
        "solana": [
            "solana>=0.32.0",
            "solders>=0.20.0",
            "spl-token>=0.3.0",
        ],
        "dev": [
            "pytest>=8.0.0",
            "pytest-asyncio>=0.23.0",
            "black>=24.0.0",
            "ruff>=0.1.0",
            "mypy>=1.8.0",
        ],
    },
)



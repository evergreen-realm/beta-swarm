from setuptools import setup, find_packages

setup(
    name="beta_swarm",
    version="3.1.0",
    description="Beta Swarm v3.1 zero-cost autonomous agent swarm",
    author="Antigravity",
    packages=find_packages(),
    install_requires=[
        # Dependencies are managed in requirements.txt
    ],
    entry_points={
        "console_scripts": [
            "beta-swarm=beta_swarm.orchestrator:main",
        ],
    },
    python_requires=">=3.10",
)
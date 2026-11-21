from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="open-humanizer",
    version="1.0.0",
    packages=find_packages(exclude=["tests", "tests.*", "examples", "examples.*"]),
    install_requires=[
        "openai>=1.0.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    python_requires=">=3.9",
    author="Open Source Community",
    author_email="",
    description=(
        "Drop-in open-source adversarial loop to rewrite AI text into human prose. "
        "Free alternative to paid ZeroGPT humanizers — no per-word SaaS fees."
    ),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/pandeyvishwas51-oss/open-humanizer",
    project_urls={
        "Bug Tracker": "https://github.com/pandeyvishwas51-oss/open-humanizer/issues",
        "Documentation": "https://github.com/pandeyvishwas51-oss/open-humanizer#readme",
        "Source": "https://github.com/pandeyvishwas51-oss/open-humanizer",
    },
    license="MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "Topic :: Text Processing :: Linguistic",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Typing :: Typed",
    ],
    keywords=[
        "ai humanizer",
        "ai detector bypass",
        "zerogpt",
        "undetectable ai",
        "humanize ai text",
        "ai text rewriter",
        "burstiness",
        "perplexity",
        "adversarial llm",
        "open source humanizer",
        "gptzero",
        "winston ai",
        "turnitin",
    ],
    entry_points={
        "console_scripts": [
            "open-humanizer=open_humanizer.cli:main",
        ],
    },
    include_package_data=True,
)

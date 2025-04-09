from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = f.read().splitlines()

setup(
    name="mistral-ocr-tool",
    version="0.1.0",
    author="CHUNLIN",
    author_email="alone@swufe8.orh",
    description="使用 Mistral AI 进行 OCR 处理的工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/alonegg/mistral-ocr-tool",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "mistral-ocr=mistral:main",
        ],
    },
)
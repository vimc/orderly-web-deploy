import setuptools

with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name="orderly-web-vimc",
    version="0.0.1",
    author="Rich FitzJohn",
    author_email="r.fitzjohn@imperial.ac.uk",
    description="Deploy scripts for OrderlyWeb",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/vimc/orderly-web-deploy",
    packages=setuptools.find_packages(),
    requires=[
        "docker",
        "yaml"
    ],
    test_suite="nose.collector",
    tests_require=["nose"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)

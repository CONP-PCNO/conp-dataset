# Simple dats validator

**Set up:**

- clone the repo, **important:** use `--recursive` to fetch the latest version of dats submodule:
<pre>git clone https://github.com/zxenia/dats_validator.git --recursive</pre>
- create and activate virtual environment
- install required packages:
<pre>pip install -r requirements.txt</pre>

**Usage:**
<pre>python validator.py --file=doc.json</pre>

**Test valid and invalid examples:**
<pre>python tests.py</pre>

**To validate against custom DATS schemas:**

- add  directory (e.g. submodule) containing all custom DATS schemas
- in validator.py set SCHEMA_PATH to the top-level (main) schema file

# Simple dats validator

Validation workflow:

1. Validates against CONP DATS schema
2. Validates required extra properties and their values where applicable

**Usage:**
<pre>python validator.py --file=DATS.json</pre>

**Test valid and invalid examples:**

- valid and invalid DATS files are in examples directory
- tests located in tests/

### Scripts for creating report about distinct values and generating jsonld files for them


- Create report about distinct values in each of the following properties: `privacy`, `types`, `licenses`, `isAbout`, `formats`, `keywords`.
By default generates report for all properties.

<pre>python report_generator.py [--privacy=False --types=False --licenses=False --is_about= --formats=False --keywords=False --help]</pre>

- Generate JSON-LD file for each distinct value and annotate value with an Interlex term match (using NIF API).

Obtain NIF API key in order to retrieve Interlex URI [here](https://neuinfo.org/about/webservices) and add it to the `api_key.json` file.
Otherwise, set `--use_api` to `False`, in that case the JSON-LD files will be created without matching term.

By default, it creates a directory for each of the above properties and saves JSON-LD files in the respective directory.

<pre>python jsonld_generator.py [--privacy=False --types=False --licenses=False --is_about= --formats=False --keywords=False --use_api=False --help]</pre>

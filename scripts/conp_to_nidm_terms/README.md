### Scripts for creating report about distinct values and generating jsonld files for them


- Create report about distinct values in each of the following properties: privacy, types, licenses, isAbout, formats, keywords. 
By default generates report for all properties.

<pre>python report_generator.py [--privacy=False --types=False --licenses=False --is_about= --formats=False --keywords=False]</pre>

- Generate jsonld file for each distinct value and annotate value with an Interlex term match (using NIF API).
By default creates directory for each of the above properties and saves jsonld files in a respective directory.

<pre>python jsonld_generator.py [--privacy=False --types=False --licenses=False --is_about= --formats=False --keywords=False]</pre>

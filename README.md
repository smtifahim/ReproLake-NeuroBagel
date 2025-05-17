# ReproLake-NeuroBagel Converter

The Python script `rpl-np-converter.py` connects to the Stardog database, runs a  SPARQL construct query  against a given reprolake dataset stored in Stardog cloud, and converts the resulting graph into a NeuroBagel-compatible JSON-LD format.

## Dependencies

```
stardog-client
rdflib
pyld
```

## Installation

Install the required packages:

```bash
pip install stardog-client rdflib pyld
```

## Usage

1. Make sure your Stardog server is running
2. Configure your Stardog connection details in `rpl-nb-converter.py`:

   - endpoint URL
   - username
   - password
   - database name
3. Run the script:

```bash
python rpl-nb-converter.py
```

The script will:

- Connect to the Stardog database
- Execute the SPARQL query from `sparql/rpl-nb-construct.rq`
- Convert the results to JSON-LD format
- Save the output to `data/rpl-nbl.jsonld`

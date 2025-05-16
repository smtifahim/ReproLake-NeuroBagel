# This script connects to a Stardog database, runs a SPARQL CONSTRUCT query to extract data,
# converts the result to JSON-LD using a custom NeuroBagel context, and saves the output in a
# nested, compacted JSON-LD format suitable for NeuroBagel query interface. 
# It uses rdflib for RDF parsing and pyld for JSON-LD compaction.
# Version: 1.0; @Author: Fahim Imam

import stardog
from rdflib import Graph
import json
from pyld import jsonld
from collections import OrderedDict
from dotenv import load_dotenv
import os

def load_graph_and_compact(result_bytes, context):
    g = Graph()
    g.parse(data=result_bytes.decode('utf-8'), format='turtle')
    jsonld_data = g.serialize(format='json-ld', indent=2)
    jsonld_obj = json.loads(jsonld_data)
    # Always wrap as @graph for compaction
    if isinstance(jsonld_obj, list):
        jsonld_obj = {"@graph": jsonld_obj}
    # Compact using pyld and neurobagel custom context
    compacted = jsonld.compact(jsonld_obj, context)
    return compacted

# Function to recursively rename @id to identifier and @type to schemaKey, except inside @context.
def rename_keys(obj, in_context=False):
    if isinstance(obj, dict):
        # If this is the @context, do not rename inside it
        if in_context or "@context" in obj:
            new_obj = {}
            for k, v in obj.items():
                if k == "@context":
                    # Mark that we're inside @context for the recursive call
                    new_obj[k] = rename_keys(v, in_context=True)
                else:
                    new_obj[k] = rename_keys(v, in_context=in_context)
            return new_obj
        else:
            new_obj = {}
            for k, v in obj.items():
                if k == "@id":
                    k = "identifier"
                elif k == "@type":
                    k = "schemaKey"
                new_obj[k] = rename_keys(v, in_context=False)
            return new_obj
    elif isinstance(obj, list):
        return [rename_keys(i, in_context=in_context) for i in obj]
    else:
        return obj

# Recursively nest the compacted JSON-LD graph to match the NeuroBagel structure.
# This function assumes the graph is flat and uses identifier references to nest.
def nest_graph(compacted):
    # Build a lookup table for all objects by their identifier
    if "@graph" in compacted:
        nodes = compacted["@graph"]
    else:
        nodes = [compacted]
    lookup = {n.get("identifier"): n for n in nodes if "identifier" in n}

    # A helper function to resolve references recursively
    def resolve(obj):
        if isinstance(obj, dict):
            # If this is a reference (only identifier), resolve it
            if set(obj.keys()) == {"identifier"}:
                ref = lookup.get(obj["identifier"])
                if ref:
                    return resolve(ref)
                else:
                    return obj
            # Otherwise, resolve all dict values
            return {k: resolve(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [resolve(i) for i in obj]
        else:
            return obj

    # Find the root of the Dataset node
    dataset = None
    for node in nodes:
        if node.get("schemaKey") == "Dataset":
            dataset = node
            break
    if not dataset:
        raise ValueError("No Dataset node found in graph.")

    # Recursively resolve all references in the dataset
    nested = resolve(dataset)
    # Add @context at the top
    nested["@context"] = compacted.get("@context", {})
    return nested

def checkServerStatus(admin):
    if (admin.healthcheck()):
        print ("        Server Status: Stardog server is running and able to accept traffic.")
    else:
        print ("        Server Status: Stardog server is NOT running. Please start the server and try again.")
        exit()

def main():
    # Load environment variables from .env file
    load_dotenv()
    
    # Load context from nb-context.json
    with open('nb-context.json', 'r') as ctxfile:
        custom_context = json.load(ctxfile)

    conn_details = {
                    'endpoint': 'https://sd-c1e74c63.stardog.cloud:5820',
                    'username': 'FDILab',
                    'password': os.getenv('STARDOG_PASSWORD')  # Password loaded from .env file
                    }

    # Database name to connect to
    # Note: The database must be created and populated with data before running this script. 
    db_name = 'ds002424_ADHD_bids'

    query_files = [
        './sparql/rpl-nb-construct.rq'
    ]

    generated_files = [
        './data/rpl-nbl.jsonld'
    ]

    print ("\nProgram execution started...")
    with stardog.Admin(**conn_details) as admin:  
        print ("\nStep 0: Checking Stardog server status..")
        checkServerStatus(admin)
        print ("Step 0: Done!")

    with stardog.Connection(db_name, **conn_details) as conn: 
        for i, query_file in enumerate(query_files):
            print("\nStep " + str(i+1) + ": Executing query from: " + query_file)
            with open(query_file, 'r') as file:
                query = file.read()
                result = conn.graph(query)  # Turtle as bytes

            print("        Converting to JSON-LD and compacting...")
            compacted = load_graph_and_compact(result, custom_context)
            print("        Renaming keys...")
            compacted = rename_keys(compacted)
            print("        Nesting graph...")
            nested = nest_graph(compacted)
            print("        Saving query results...")

            # Move @context to the beginning
            if "@context" in nested:
                ordered = OrderedDict()
                ordered["@context"] = nested["@context"]
                for k, v in nested.items():
                    if k != "@context":
                        ordered[k] = v
            else:
                ordered = nested

            with open(generated_files[i], 'w', encoding='utf-8') as file:
                json.dump(ordered, file, indent=2)
            print("        Query results saved to: " + generated_files[i])
            print("Step " + str(i+1) + ": Done!")
        conn.close()
    print("\nAll queries executed and results are saved successfully!\n")

if __name__ == "__main__":
    main()
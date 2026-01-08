# Tasks

1. Valiate demo folder structure and contents are aligned with C:\Users\ansyeo\OneDrive - Microsoft\01 Azure\Ontology\Ontology Demo generator\Fabric-Ontology-demoAgent\.agentic\fabric-ontology-demo-v2.yaml
2. Create Lakehouse and validate Lakehouse is created
3. Upload all data\lakehouse files into Lakehouse and validate it is uploaded
4. Load all files in lakehouse into tables and validate that all tables are created
5. Create Eventhouse and validate eventhouse is created.
6. Upload data\eventhouse data and validate that all files are in eventhouse. 
7. Create ontology and all its entities, properties, key etc. (refer to code https://github.com/falloutxAY/rdf-dtdl-fabric-ontology-converter/tree/main). 
8. Bind lakehouse properties (static) for all entities as per bindings.yaml and validate all bindings are successful. Ensure that the key is defined (keyColumn in bindings.yaml). 
9.  Bind eventhouse properties (timeseries) as per bindings.yaml and validate all bindings are successful  
10. Bind all relationships as per bindings.yaml and validate all bindings are succuessful 
11. Verify steps 2 to 10 by checking fabric to see that the steps are successfully completed with the artefacts/steps/bindings etc created. 


## Need to adhere to this
- Each task step should be able to execute on it's own if required. Provide cli to achieve this.

- At each task step:
  - Check if step is already done, if done, skip to next task
  - If successful, create a mark to know that we can resume from that step later
  - IF fail, stop processing and output error message 

- Ensure code adheres to all limitations of fabric graph, FAbric ontology

- Resume should resume from the last known successful step
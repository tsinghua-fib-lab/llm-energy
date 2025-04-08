# Energy-LLM

Since the entire pipeline involves numerous LLM API operations, and we allow users to configure different API services for each operation, please pay attention to several configurable API-related constants in the script for operations that require API calls.

- `BASE_URL ` specifies the base URL of your API service platform.
- `API_KEY ` specifies your API key.
- `MODEL_NAME ` specifies the model you wish to use with your API service, and it should follow the format required by the API service provider.



## Tuning Data Generation

### Part-1: Energy-Bonito

#### Training Energy-Bonito Model

Please first navigate to the `train_energy_bonito` directory by using the cd command: `cd train_energy_bonito`

##### Stage-1: Sample data from the structured JSON

By modifying variables `RATIO` and `dir` which represent the sample ratio and input JSON file directory respectively, you can sample the content chunk from the JSON file and generate a list which will be stored as an output JSON file with your defined `SAVE_FILE_NAME` by running:

```
python sample.py
```

##### Stage-2: Generate training data for Energy-Bonito with LLM API

By defining all the required constants including API settings and input/output file in `generate_bonito_tuning_with_api.py`, you can run the script to generate a structured JSON file with API generated QA pairs:

```
python generate_bonito_tuning_with_api.py
```

##### Stage-3: Convert the JSON file into a training dataset

Defining input and output file directory then run:

```
python transfer.py
```

to transfer the JSON file into a QA pairs dataset with structures suitable for Bonito training. You can change the `RATIO` representing the dropping ratio of the negative cases. We preserve a small ratio of the negative cases to ensure robustness of our Energy-Bonito.

#### Generating Data with Energy-Bonito

Please first navigate to the `energy_bonito_inference` directory by using the cd command: `cd energy_bonito_inference`

##### Stage-1: Setup Bonito inference service

First, you need to define a YAML file for the trained Bonito model to configure your Energy-Bonito settings, using the checkpoint obtained in the previous step. You can specify the number of parallel processes, with each GPU assigned to one process by default. To set up the service, run the following command:

```
python bonito_service_setup.py
```

##### Stage-2: Generate multiple-choice (MC) and question-answer (QA) data through model inference.

After setting up the model service, we can use the two scripts located at this path to generate MC and QA data based on the corpus, respectively.

- For MC data

```
python bonito_inferece_distributed_MC.py
```

- For QA data

```
python bonito_inference_distributed_QA.py
```



### Part-2: Knowledge Network

Please first navigate to the `knowledge_network` directory by using the cd command: `cd knowledge_network`

In this section, we break down the entire process sequentially, from the expert-derived knowledge network to the final knowledge network tuning data.

#### Stage-1: Read the knowledge network and convert it into a structured JSON file

By default, we use XMind. You can provide the path to an XMind file and convert it into JSON by running the following command:

```
python read_xmind.py
```

#### Stage-2: Generating syllabus and class sessions based on the network

```
python generate_syllubus_and_class_sessions.py
```

#### Stage-3: Generating questions based on the syllabus and class sessions

```
python generate_questions.py
```

#### Stage-4: Deduplicate potential duplicate questions

```
python deduplication_questions.py
```

#### Stage-5: Generating questions with RAG API

We build an RAGFlow system and expose an API to generate answers. However, you can use any RAG system and its API, as long as it is compatible with the OpenAI API style. To run the generation process, identify the RAG API and execute the following command:

```
python ragflow_api_generate_answer.py
```

#### Stage-5: Compose questions and answers as the final tuning data

```
python gather_knowledge_network_tuning.py
```



### Part-3: GraphRAG

Please first navigate to the `generate_based_on_graphrag` directory by using the cd command: `cd generate_based_on_graphrag`

- `append_meta_data.py`: Append metadata, including release time, district, or outline etc, to the data frame in the GraphRAG system.
- `generate_qa_pairs.py`: Request the GraphRAG system to generate QA pair data.



## Bench Energy-LLM

Please first navigate to the `bench_energy_llm` directory by using the cd command: `cd bench_energy_llm`

After using the data generated from the previous processes to train your Energy-LLM, we provide a benchmark to evaluate the model's performance on knowledge in the new energy sector.

- `bench_multi_choice`: This folder contains two scripts for testing API-based and local models on benchmark MC questions. For API-based models, you need to define the API settings. For local models, you can deploy the models in a llama-factory compatible style and expose a port to the script. Additionally, you can switch between Easy or Hard MC in the script.

- `bench_short_questions`: In this folder, we provide a script for your models, either local or API-based, to answer benchmark subjective questions. You can then grade the answers using BERTScore by running:

  ```
  python grade_short_answer.py
  ```

  


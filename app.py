# Importa as bibliotecas necessárias
from flask import Flask, request
from flask_cors import CORS
import google.generativeai as genai
import pandas as pd
import numpy as np

# Cria uma instância do flask que será nosso servidor
app = Flask(__name__)
CORS(app)

# Busca a chave guardada no Render que será o host do nosso servidor e atualiza as configs do genai para utilizar a chave
with open('api_key.txt', "r") as f:
    api_key = f.read().strip()

genai.configure(api_key=api_key)

# Definimos as configurações que serão utilizadas no modelo
configsList = [
    {
        "temperature": 0.5,
        "top_p": 0.95,
        "top_k": 0,
        "max_output_tokens": 4096,
    },
    {
        "temperature": 0.75,
        "top_p": 0.95,
        "top_k": 0,
        "max_output_tokens": 4096,
    },
    {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 0,
        "max_output_tokens": 4096,
    },
]

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
    },
]

# Função que será responsável por realizar o embed das respostas
def embedFunction(temperatura, resposta):
    return genai.embed_content(
        model="models/embedding-001",
        content=resposta,
        title=temperatura,
        task_type="RETRIEVAL_DOCUMENT",
    )["embedding"]

# Função que será responsável por realizar o embed da consulta e definir qual a resposta com o produto escalar mais próxima
def consultarMelhorResposta(consulta, base):
    embeddingConsulta = genai.embed_content(
        model="models/embedding-001", content=consulta, task_type="RETRIEVAL_QUERY"
    )["embedding"]

    produtosEscalares = np.dot(np.stack(base["Embeddings"]), embeddingConsulta)

    indice = np.argmax(produtosEscalares)

    return base.iloc[indice]["resposta"]

# Define a lógica que ocorrerá quando o servidor receber a consulta
@app.route("/", methods=["POST"])
def post():
    if request.method == "POST":
        # Acessa o prompt recebido na consulta
        prompt = request.get_json()["prompt"]
        print("Prompt:", f"{prompt}")

        # Tenta realizar a lógica de buscar 3 respostas, embeddar as 3 e definir qual a melhor delas com base no prompt recebido. Se der erro, retorna o erro.
        try:

            responses = []

            for config in configsList:
                model = genai.GenerativeModel(
                    model_name="gemini-1.5-pro-latest",
                    generation_config=config,
                    safety_settings=safety_settings,
                )

                response = model.generate_content(prompt)
                responses.append(
                    {
                        "temperatura": str(config["temperature"]),
                        "resposta": response.text,
                    }
                )

            df = pd.DataFrame(responses)

            print(df)

            df["Embeddings"] = df.apply(
                lambda row: embedFunction(row["temperatura"], row["resposta"]), axis=1
            )

            melhorResposta = consultarMelhorResposta(prompt, df)

            print(melhorResposta)

            return melhorResposta

        except Exception as e:
            print("Deu ruim!", e)
            return e.with_traceback


if __name__ == "__main__":
    app.run(debug=False)

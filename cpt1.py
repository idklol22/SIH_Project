import streamlit as st
import json
import duckdb
import sqlparse
import pandas as pd
from groq import Groq
import os


def chat_with_groq(client, prompt, model, response_format):
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format=response_format
    )
    return completion.choices[0].message.content

def execute_duckdb_query(query):
  original_cwd = os.getcwd()
  os.chdir('data')

  try:
      conn = duckdb.connect(database=':memory:', read_only=False)
      query_result = conn.execute(query).fetchdf().reset_index(drop=True)
  finally:
      os.chdir(original_cwd)

  return query_result

def get_summarization(client, user_question, df, model):
    prompt = '''
      A user asked the following question pertaining to local database tables:
    
      {user_question}
    
      To answer the question, a dataframe was returned:
    
      Dataframe:
      {df}

    In a few sentences, summarize the data in the table as it pertains to the original user question. Avoid qualifiers like "based on the data" and do not comment on the structure or metadata of the table itself
  '''.format(user_question=user_question, df=df)

    return chat_with_groq(client, prompt, model, None)

# Streamlit UI
def main():
    st.title("Streamlining Events for Freshers")


    groq_api_key = "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"
    client = Groq(api_key=groq_api_key)

    model = "llama3-70b-8192"

    user_question = st.text_input("Ask a question about the data:")
    if st.button("Submit"):
        if user_question:

            with open('prompts/base_prompt.txt', 'r') as file:
                base_prompt = file.read()

            full_prompt = base_prompt.format(user_question=user_question)
            llm_response = chat_with_groq(client, full_prompt, model, {"type": "json_object"})
            result_json = json.loads(llm_response)

            if 'sql' in result_json:
                sql_query = result_json['sql']
                results_df = execute_duckdb_query(sql_query)

                formatted_sql_query = sqlparse.format(sql_query, reindent=True, keyword_case='upper')

                st.code(formatted_sql_query, language='sql')
                st.write("Query Results:")
                st.dataframe(results_df)

                summarization = get_summarization(client, user_question, results_df, model)
                st.write("Summarization:")
                st.write(summarization)
            elif 'error' in result_json:
                st.error("ERROR: Could not generate valid SQL for this question")
                st.write(result_json['error'])


if __name__ == "__main__":
    main()

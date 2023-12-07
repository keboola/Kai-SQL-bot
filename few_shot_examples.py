from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.schema import Document
from langchain.agents.agent_toolkits import create_retriever_tool
#from langchain.agents.tools import human_approval_tool


few_shots = {'List all customers.': 'SELECT * FROM "customer";',
 'How many orders are there?': 'SELECT COUNT(*) FROM \"order\";',
 'Help me write a query to find the number of orders placed by each customer.': 'SELECT customer_id, COUNT(*) AS order_count FROM \"order\" GROUP BY customer_id;',
 'Help me write a query to calculate the RFM value of my customers based on their orders': "'Here is the SQL code to calculate the RFM (Recency, Frequency, Monetary value) of customers based on their orders:\nSELECT \n  \"customer_id\", \n  COUNT(*) AS \"frequency\", \n  MAX(\"processed_at\") AS \"last_order_date\", \n  SUM(\"total_price\") AS \"monetary_value\"\nFROM \"order\"\nGROUP BY \"customer_id\"\nLIMIT 10;\n\nAnd here are the results for the first 10 customers:\n\ncustomer_id\tfrequency\tlast_order_date\tmonetary_value\n6932238172411\t1\t2023-08-22T11:48:33-04:00\t229.00\n6752102711547\t1\t2023-04-05T04:49:00-04:00\t17.99\n6563541876987\t1\t2022-11-30T11:49:44-05:00\t28.99\n6854378815739\t1\t2023-06-24T04:48:23-04:00\t29.99\n6926350614779\t1\t2023-08-17T09:48:29-04:00\t25.00\n6957347078395\t1\t2023-09-13T16:48:31-04:00\t29.99\n6348377882875\t1\t2022-08-11T12:20:24-04:00\t10.00\n6503894057211\t1\t2022-10-30T17:49:19-04:00\t100.00\n6615296835835\t1\t2022-12-28T13:49:25-05:00\t9.99\n6966435152123\t1\t2023-09-20T09:48:53-04:00\t99.95\nThis query provides the frequency of orders, the date of the last order, and the total monetary value of orders for each customer. The results are limited to 10 customers for brevity.'",
 "How many vendors are there?": "53 vendors were found. Here is the SQL query to get the count of vendors: ```sql SELECT COUNT(DISTINCT \"vendor\") FROM \"product\";",
 'Help me write a query to calculate the number of orders placed by month': "Here is the SQL code to calculate the number of orders placed by month:\n\nSELECT TO_CHAR(TO_DATE(\"processed_at\"), 'YYYY-MM') AS order_month, COUNT(*) AS total_orders \nFROM \"order\" \nGROUP BY TO_CHAR(TO_DATE(\"processed_at\"), 'YYYY-MM') \nORDER BY order_month;\n\nAnd here are the results:\n\norder_month\ttotal_orders\n2022-02\t120\n2022-04\t251\n2022-05\t48\n2022-06\t38\n2022-07\t57\n2022-08\t84\n2022-09\t68\n2022-10\t211\n2022-11\t211\n2022-12\t217\n2023-01\t52\n2023-03\t115\n2023-04\t210\n2023-05\t217\n2023-06\t210\n2023-07\t217\n2023-08\t217\n2023-09\t203\n(Note: The results are limited to the first 18 rows for brevity.)",
 
}

embeddings = OpenAIEmbeddings()

few_shot_docs = [Document(page_content=question, metadata={'sql_query': few_shots[question]}) for question in few_shots.keys()]
vector_db = FAISS.from_documents(few_shot_docs, embeddings)
retriever = vector_db.as_retriever()

tool_description = """
This tool will help you understand similar examples to adapt them to the user question.
Input to this tool should be the user question.
"""

retriever_tool = create_retriever_tool(
        retriever,
        name='sql_get_similar_examples',
        description=tool_description
    )
custom_tool_list = [retriever_tool]


custom_suffix = """
I should first get the similar examples I know.
If the examples are enough to construct the query, I can build it.
Otherwise, I can then look at the tables in the database to see what I can query.
Then I should query the schema of the most relevant tables
"""
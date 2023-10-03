# Kai SQL Bot Guide 

The Kai SQL Bot is an interactive Streamlit application designed to assist users with SQL queries. Whether you are setting it up or are a user aiming to derive insights from SQL databases, this comprehensive guide offers insights on the technical setup and user interactions.

---

#### Application Structure:

1. **Import Libraries**: Essential Python libraries and custom modules are imported.
    
2. **Configurations & Setups**: Everything within this data app is customizable. From the logos, prompts, and language support, you have control over exactly how you want your app to look and behave.
    
    - Page title and icon setup.
        
    - Initialization of the OpenAI key.
        
    - Translation function for multi-language support.
        
    - Functions to establish Snowflake database connections.
        
    - AI model configurations.
        
3. **Chat Interface**: User's interactions with the AI (Kai) through a chat interface.
    
4. **Feedback & Logging**: Allows users to provide feedback on the AI's responses, and this feedback can be logged to a specified URL.
    

Get started with your own customizations by forking this repository:

[https://github.com/keboola/Kai-SQL-bot](https://github.com/keboola/Kai-SQL-bot)

---

#### Best Practices:

1. **Security**:
    
    - Store sensitive information like API keys, database credentials, etc., in st.secrets to avoid exposing them.
        
    - Ensure database connections are closed after executing SQL queries to prevent unauthorized access.
        
2. **User Interface**:
    
    - Clearly label all user inputs and options for better usability.
        
    - Regularly clear the chat history for better performance and to avoid overloading the session.
        
3. **Performance**:
    
    - Limit the amount of data fetched from the database to avoid delays or crashes.
        
    - Ensure the language model used (GPT-4, GPT-3.5, etc.) matches your application's needs in terms of complexity and speed. The default model is gpt-4-0613 but there is no limitation to which foundation model is chosen. To review the different model options, you can follow this link:
        
        - [https://platform.openai.com/docs/models/overview](https://platform.openai.com/docs/models/overview)
            
4. **Feedback**:
    
    - Always log feedback to analyze and improve the model's performance and accuracy over time.

    - You can make use of Keboola Data Streams for this. [https://developers.keboola.com/integrate/data-streams/tutorial/](https://developers.keboola.com/integrate/data-streams/tutorial/)
        
    - Prompt users to provide feedback on the AI's response to continuously improve the model.
        
5. **Multilanguage Support**:
    
    - Update the JSON files in the languages folder to add more translations if needed.
        
    - Ensure translations are accurate to provide a seamless experience for users.
        
6. **Error Handling**:
    
    - Handle all potential errors, especially around database connections and AI model calls, to prevent application crashes.
        
    - Inform users when errors occur and possibly provide guidance on the next steps.
        

---

#### User Interaction with Kai:

**How to Begin**:

- Upon launching the application, users are greeted by Kai, the AI bot, who introduces itself.
    
- Users can select their preferred language from the sidebar (currently supports English and Czech).
    
- Users can also choose the Open AI model to be used.
    

**What Questions to Ask**:

Kai is designed to assist with SQL related questions. Examples include:

1. "Show me the first ten rows from the users table."
    
2. "Find users from the customers table where their name matches 'John'."
    
3. "Count the number of orders in the orders table for the last month."
    

**Recommendations**:

1. **Tables & Columns**: For optimal performance and readability:
    
    - It's recommended to limit databases to **not more than 500 tables**.
        
    - Each table should ideally have **no more than 50 columns**.
        
2. **Question Clarity**: Be specific in your questions. For better clarity, specify the table name and what you're seeking, e.g., "Show me the first ten rows from the sales table."
    
3. **Errors & Troubleshooting**:
            
    - If connecting to Snowflake, ensure correct credentials are provided. If repeated connection errors occur, check with your database administrator or the service provider.
        
    - If a generated SQL query seems overly complex or doesn't produce the expected result when executed, consider consulting with a SQL expert.
        
4. **Using Kai's Assistance**: Kai provides more than just SQL generation. Users can inquire about SQL best practices, receive explanations of specific SQL functions, and more.
         

---

#### Deployment:

For deploying this app, ensure:

- All necessary libraries are available.
    
- The required modules (e.g., langchain, src.workspace_connection) are accessible and correctly referenced.
    
- The st.secrets are correctly set up with all essential credentials and API keys.
    

---

#### Future Enhancements:

1. Extend language support.
    
2. Introduce features like saving queries and exporting results.
    
3. Enhance the chat UI for a superior user experience.
    

---

By understanding both the technical aspects and user interaction guidelines of the Kai SQL Bot, users and developers can ensure efficient, secure, and meaningful engagements with the tool.

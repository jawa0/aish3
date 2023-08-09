# (C) 2023 by Jabavu Adams. All Rights Reserved.

import openai
import os
from dotenv import load_dotenv


# Load the .env file
load_dotenv()


def makeGPTRequest():
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_ORGANIZATION = os.getenv("OPENAI_ORGANIZATION")
    
    openai.api_key = OPENAI_API_KEY
    openai.organization = OPENAI_ORGANIZATION

    response = openai.Completion.create(
    model="gpt-4",
    # model="gpt-3.5-turbo",
    messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Define ADAR"},
        ]
    )
    print(response['choices'][0]['message']['content'])

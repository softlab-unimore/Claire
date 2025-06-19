from pydantic import BaseModel, Field
from typing import Optional, Any, Union, List
from dotenv import load_dotenv
from openai import OpenAI
import timeout_decorator
import os
from .prompts.prompt_check import prompt_stage1, prompt_stage2, prompt_stage3, prompt_stage4


load_dotenv()

class OpenAIModel(BaseModel):
    model_name: str = Field(..., strict=True, description="Name of the openai model as per their official website")
    temperature: float = Field(0.00001, strict=True, description="The temperature of the model in between 0 and 1")
    client: Any = OpenAI()
    max_retries: int = Field(50, strict=True, description="Number of retries in case of failed OpenAI API call")

    # @timeout_decorator.timeout(60, timeout_exception=StopIteration)
    def call_gpt(self, prompt: str) -> (str, dict):
        completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": f"{prompt}"
                    }
                ],
                temperature=self.temperature
        )

        metadata = {
            "input_tokens": completion.usage.prompt_tokens,
            "output_tokens": completion.usage.completion_tokens,
        }

        return completion.choices[0].message.content.lower() #, metadata

    def extract_result(self, text: str) -> bool:
        response = text.lower().split("risposta finale:")[-1].strip()
        return True if response == "vai alla fase successiva" else False

    def query(self, prompt: str) -> str:
        for _ in range(self.max_retries):
            try:
                return self.call_gpt(prompt)
            except StopIteration:
                print("Failed to get a response. Retrying...")

        raise RuntimeError(f"Failed to query OpenAI after {self.max_retries} retries.")

    def check_next_stage(self, messages: str, stage: int) -> bool:
        if stage == 1:
            prompt = prompt_stage1.format(messages=messages, stage=str(stage))
        elif stage == 2:
            prompt = prompt_stage2.format(messages=messages, stage=str(stage))
        elif stage == 3:
            prompt = prompt_stage3.format(messages=messages, stage=str(stage))
        elif stage == 4:
            prompt = prompt_stage4.format(messages=messages, stage=str(stage))
        else:
            raise RuntimeError("Unknown stage level")

        result = self.query(prompt)
        print(result)
        return self.extract_result(result)

attr = {
    "model_name": os.environ["OPENAI_MODEL_NAME"],
    "temperature": float(os.environ["OPENAI_TEMPERATURE"]),
}
openaimodel = OpenAIModel(**attr)
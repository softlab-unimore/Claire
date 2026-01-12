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
                temperature=self.temperature if "5" not in self.model_name else 1.0,
        )

        metadata = {
            "input_tokens": completion.usage.prompt_tokens,
            "output_tokens": completion.usage.completion_tokens,
        }

        return completion.choices[0].message.content #, metadata

    """def extract_result(self, text: str, pattern: str) -> str:
        response = text.lower().split(pattern)[-1].strip()
        return response"""

    def extract_result(self, text: str, pattern: str) -> str:
        lower_text = text.lower()
        lower_pattern = pattern.lower()

        idx = lower_text.find(lower_pattern)
        if idx == -1:
            return ""  # pattern not found

        start = idx + len(pattern)
        response = text[start:].strip()
        return response

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
        return self.extract_result(result, "risposta finale: ") == "vai alla fase successiva"

    def call_gpt_stream(self, prompt: str):
        stream = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature if "5" not in self.model_name else 1.0,
            stream=True,
            # stream_options={"include_usage": True},  # optional; see note below
        )

        for chunk in stream:
            # If you ever use include_usage=True, the last chunk may have choices=[]
            if not getattr(chunk, "choices", None):
                continue

            delta = chunk.choices[0].delta  # ChoiceDelta
            text_piece = getattr(delta, "content", None)
            if text_piece:
                yield text_piece

attr = {
    "model_name": os.environ["OPENAI_MODEL_NAME"],
    "temperature": float(os.environ["OPENAI_TEMPERATURE"]),
}
openaimodel = OpenAIModel(**attr)
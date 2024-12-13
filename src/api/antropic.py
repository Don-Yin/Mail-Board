#!/Users/donyin/miniconda3/envs/common/bin/python

"""
https://docs.anthropic.com/en/docs/about-claude/models#model-comparison-table for other models
"""

import os
from anthropic import Anthropic
from anthropic.types import Message
from ast import literal_eval
from typing import List, Tuple, Dict, Any
from rich.console import Console
from rich.table import Table
from rich import print as rprint

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
client = Anthropic(api_key=ANTHROPIC_API_KEY)
console = Console()

# Pricing per million tokens for different Claude models and operations
PRICING = {
    "claude-3-5-sonnet-latest": {
        "input": 3.0,  # $3/MTok
        "output": 15.0,  # $15/MTok
        "cache_write": 3.75,  # $3.75/MTok
        "cache_read": 0.30,  # $0.30/MTok
        "context_window": 200000,
        "batch_discount": 0.5,  # 50% discount with Batches API
    },
    "claude-3-5-haiku-latest": {
        "input": 0.80,  # $0.80/MTok
        "output": 4.0,  # $4/MTok
        "cache_write": 1.0,  # $1/MTok
        "cache_read": 0.08,  # $0.08/MTok
        "context_window": 200000,
        "batch_discount": 0.5,  # 50% discount with Batches API
    },
}


class AntropicResponse:
    def __init__(self, prompt: str, requested_keys: List[str] = None):
        self.prompt = prompt
        self.requested_keys = requested_keys if requested_keys is not None else []
        self.previous_responses = []

    def _create_response_table(self, title: str, content: str) -> None:
        """Create and display a formatted table for responses"""
        table = Table(title=title, show_header=True, header_style="bold magenta")
        table.add_column("Content", style="cyan", no_wrap=False)
        table.add_row(str(content))
        console.print(table)

    def _calculate_cost(self, model: str, response: Message, prompt_length: int) -> float:
        """
        Calculate the cost of the API call based on input and output tokens.
        Uses pricing from the PRICING dictionary based on the model.
        Estimates tokens by dividing character count by 3.5 (average chars per token).
        """
        if model not in PRICING:
            raise ValueError(f"Unknown model: {model}")

        model_pricing = PRICING[model]
        input_cost_per_million = model_pricing["input"]
        output_cost_per_million = model_pricing["output"]

        # convert character lengths to estimated token counts
        input_tokens = prompt_length / 3.5
        output_tokens = len(response.content[0].text) / 3.5

        input_cost = (input_tokens * input_cost_per_million) / 1_000_000
        output_cost = (output_tokens * output_cost_per_million) / 1_000_000
        total_cost = input_cost + output_cost

        return total_cost

    def get_completion(self, model: str = "claude-3-5-haiku-latest") -> Tuple[Dict[str, Any], float, str]:
        """
        Get a completion from Anthropic's Claude model using the Messages API.

        Args:
            model: The model to use (defaults to 'claude-3-5-haiku-latest')

        Returns:
            tuple: (response_dict, total_cost, model)
        """
        return_content = {}
        total_cost = 0

        while True:
            try:
                messages = []

                # Add system message if there are previous responses
                if self.previous_responses:
                    messages.append(
                        {
                            "role": "assistant",
                            "content": (
                                "Previous attempts that were invalid:\n"
                                + "\n".join(self.previous_responses)
                                + f"\n\nPlease provide a valid Python dictionary containing these keys: {self.requested_keys} with no other keys."
                            ),
                        }
                    )

                # Add user message
                messages.append({"role": "user", "content": self.prompt.strip()})

                response = client.messages.create(model=model, max_tokens=1024, messages=messages)

                # Calculate cost for this attempt
                attempt_cost = self._calculate_cost(model, response, len(self.prompt))
                total_cost += attempt_cost
                self._create_response_table("API Cost", f"${attempt_cost:.6f}")

                response_text = response.content[0].text.strip()
                self.previous_responses.append(response_text)
                self._create_response_table("Received Response", response_text)

                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                if start != -1 and end != -1 and start < end:
                    response_dict_str = response_text[start:end]
                else:
                    response_dict_str = response_text

                self._create_response_table("Processed Response", response_dict_str)

                response_dict = literal_eval(response_dict_str)
                if all(key in response_dict for key in self.requested_keys):
                    return_content = response_dict
                    break
                else:
                    missing_keys = [key for key in self.requested_keys if key not in response_dict]
                    self._create_response_table("Missing Keys", missing_keys)
            except (ValueError, SyntaxError) as e:
                self._create_response_table("Parse Error", f"Failed to parse response as dictionary: {e}")
            except Exception as e:
                self._create_response_table("Error", f"Error getting completion from Claude: {e}")
                break

        self._create_response_table("Total API Cost", f"${total_cost:.6f}")
        return return_content, total_cost, model


if __name__ == "__main__":
    prompt = "What is the capital of France?"
    requested_keys = ["capital"]
    response = AntropicResponse(prompt, requested_keys)
    result, cost = response.get_completion()
    console.print("\n[bold green]Final Result:[/bold green]")
    console.print(result)
    console.print(f"\n[bold blue]Total Cost: ${cost:.6f}[/bold blue]")

    print(result)
    print(cost)

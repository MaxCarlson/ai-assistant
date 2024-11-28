from transformers import AutoModelForCausalLM, AutoTokenizer
import torch


class LLMManager:
    def __init__(self, model_name="EleutherAI/gpt-neo-1.3B", device="cuda"):
        """
        Initialize the LLM and tokenizer.
        
        :param model_name: Hugging Face model name or path.
        :param device: Device for inference ('cuda' or 'cpu').
        """
        self.model_name = model_name
        self.device = device
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(model_name).to(device)

        # Check and set padding token
        if self.tokenizer.pad_token is None:
            if self.tokenizer.eos_token is not None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            else:
                self.tokenizer.add_special_tokens({'pad_token': '[PAD]'})
                self.model.resize_token_embeddings(len(self.tokenizer))  # Resize model embeddings

    def generate(self, prompt, max_new_tokens=200, temperature=0.8, top_p=0.9, do_sample=True):
        """
        Generate a response from the LLM based on the given prompt.

        :param prompt: Input text prompt.
        :param max_new_tokens: Maximum number of new tokens to generate.
        :param temperature: Sampling temperature.
        :param top_p: Top-p sampling.
        :param do_sample: Whether to use sampling.
        :return: Generated text.
        """
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,  # Truncate input if necessary
        ).to(self.device)

        output_ids = self.model.generate(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            max_new_tokens=max_new_tokens,  # Limit the length of the generated tokens
            temperature=temperature,
            top_p=top_p,
            do_sample=do_sample,
            pad_token_id=self.tokenizer.pad_token_id,
        )
        response = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)
        return response




